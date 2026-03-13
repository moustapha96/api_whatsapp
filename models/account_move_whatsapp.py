# whatsapp_business_api/models/account_move_whatsapp.py
# Ce fichier nécessite le module 'account' pour fonctionner
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import config
import logging
import base64
import time

_logger = logging.getLogger(__name__)

# Hérite directement de account.move (le module account est dans les dépendances)
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.depends()
    def _compute_show_whatsapp_button(self):
        """Calcule si le bouton WhatsApp doit être affiché selon la configuration"""
        config = self.env['whatsapp.config'].get_active_config()
        show_button = config.show_button_in_invoice if config else True
        for record in self:
            record.x_show_whatsapp_button = show_button
    
    x_show_whatsapp_button = fields.Boolean(
        string="Afficher bouton WhatsApp",
        compute="_compute_show_whatsapp_button",
        store=False,
        help="Indique si le bouton WhatsApp doit être affiché selon la configuration"
    )

    x_whatsapp_residual_sent = fields.Boolean(
        string="Message montant résiduel WhatsApp envoyé",
        default=False,
        help="Indique si un message de montant résiduel a été envoyé via WhatsApp"
    )
    
    x_whatsapp_residual_sent_date = fields.Datetime(
        string="Date envoi message résiduel WhatsApp"
    )
    
    x_whatsapp_validation_sent = fields.Boolean(
        string="Validation facture WhatsApp envoyée",
        default=False,
        help="Indique si un message de validation de facture a été envoyé via WhatsApp"
    )
    
    x_whatsapp_validation_sent_date = fields.Datetime(
        string="Date envoi validation facture WhatsApp"
    )
    
    x_whatsapp_invoice_sent = fields.Boolean(
        string="Facture WhatsApp envoyée",
        default=False,
        help="Indique si la facture a été envoyée par WhatsApp"
    )
    
    x_whatsapp_invoice_sent_date = fields.Datetime(
        string="Date envoi facture WhatsApp"
    )

    x_whatsapp_auto_send_attempted = fields.Boolean(
        string="Envoi auto WhatsApp déjà tenté",
        default=False,
        help="Indique qu'une tentative d'envoi automatique a déjà été faite (succès ou non), pour éviter les doublons lors de multiples write()."
    )
    
    x_whatsapp_unpaid_reminder_sent = fields.Boolean(
        string="Rappel facture impayée WhatsApp envoyé",
        default=False,
        help="Indique si un rappel pour facture impayée a été envoyé via WhatsApp"
    )
    
    x_whatsapp_unpaid_reminder_sent_date = fields.Datetime(
        string="Date envoi rappel facture impayée WhatsApp"
    )

    def write(self, vals):
        """Surcharge write pour détecter les changements de amount_residual et envoyer un message"""
        # Sauvegarde l'ancien état et montant résiduel avant la modification
        old_state = {}
        old_residual = {}
        
        # Détecte les changements qui peuvent affecter le montant résiduel ou l'état
        if any(field in vals for field in ['line_ids', 'invoice_payment_state', 'payment_state', 'state']):
            for record in self:
                if record.move_type in ['out_invoice', 'out_refund']:
                    old_state[record.id] = record.state
                    old_residual[record.id] = record.amount_residual
        
        # Effectue la modification
        result = super().write(vals)
        
        # Traite chaque facture
        for record in self:
            if record.move_type in ['out_invoice', 'out_refund']:
                # Vérifie si la facture vient d'être validée (postée)
                old_state_value = old_state.get(record.id)
                new_state_value = record.state
                
                # Si la facture passe à l'état "posted" (validée), envoie la facture (une seule tentative par facture)
                if (old_state_value != new_state_value and 
                    new_state_value == 'posted' and 
                    not record.x_whatsapp_invoice_sent and 
                    not record.x_whatsapp_auto_send_attempted):
                    _logger.debug("Tentative d'envoi automatique de la facture %s (état: %s -> %s)", 
                                  record.name, old_state_value, new_state_value)
                    try:
                        record._send_whatsapp_invoice()
                    except ValidationError:
                        raise
                    except Exception as e:
                        _logger.warning("Erreur lors de l'envoi de la facture WhatsApp pour %s: %s", record.name, str(e))
                elif old_state_value != new_state_value and new_state_value == 'posted':
                    if record.x_whatsapp_auto_send_attempted:
                        _logger.debug("Facture %s: envoi auto WhatsApp déjà tenté, ignoré", record.name)
                    else:
                        _logger.debug("Facture %s déjà envoyée (x_whatsapp_invoice_sent=True), envoi ignoré", record.name)
                
                # Si le montant résiduel a changé, envoie un message
                old_residual_value = old_residual.get(record.id)
                new_residual_value = record.amount_residual
                
                # Envoie un message si le montant résiduel a changé et qu'il reste à payer
                if (old_residual_value is not None and 
                    abs(old_residual_value - new_residual_value) > 0.01 and 
                    new_residual_value > 0):
                    try:
                        record._send_whatsapp_residual_notification(old_residual_value, new_residual_value)
                    except Exception as e:
                        _logger.warning("Erreur lors de l'envoi du message WhatsApp de montant résiduel pour la facture %s: %s", record.name, str(e))
        
        return result

    def _send_whatsapp_residual_notification(self, old_residual, new_residual):
        """Envoie un template payment_reminder quand le montant résiduel d'une facture change."""
        self.ensure_one()

        if not self.partner_id:
            return
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour %s, rappel WhatsApp non envoyé", self.partner_id.name)
            return
        if self.x_whatsapp_residual_sent and abs(old_residual - new_residual) < 0.01:
            return

        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active pour le rappel résiduel")
            return

        try:
            phone = whatsapp_config._validate_phone_number(phone, partner=self.partner_id)
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": self.partner_id.name},
                        {"type": "text", "text": self.name},
                        {"type": "text", "text": f"{new_residual:.0f}"},
                    ],
                }
            ]
            fallback_text = (
                f"Bonjour {self.partner_id.name}, un paiement a ete enregistre sur votre facture {self.name}. "
                f"Montant restant a regler : {new_residual:.0f} F CFA. Equipe CCTS."
            )
            result = self._send_template_or_fallback(
                whatsapp_config, phone, "payment_reminder", components, fallback_text
            )
            if not isinstance(result, dict) or result.get('success') is not False:
                self.write({
                    'x_whatsapp_residual_sent': True,
                    'x_whatsapp_residual_sent_date': fields.Datetime.now(),
                })
                _logger.info("Template payment_reminder envoyé pour la facture %s (restant: %s)", self.name, new_residual)
            else:
                _logger.warning("Échec envoi payment_reminder pour facture %s: %s", self.name, result.get('error'))

        except Exception as e:
            _logger.warning("Message WhatsApp montant résiduel facture %s non envoyé (non bloquant): %s", self.name, str(e))
    
    def action_send_invoice_details_whatsapp(self):
        """Envoie le template invoice_notification avec les détails de la facture."""
        self.ensure_one()

        if not self.partner_id:
            raise ValidationError(_("La facture n'a pas de partenaire associé."))

        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)

        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))

        try:
            phone = whatsapp_config._validate_phone_number(phone, partner=self.partner_id)
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": self.partner_id.name},
                        {"type": "text", "text": self.name},
                        {"type": "text", "text": f"{self.amount_total:.0f}"},
                        {"type": "text", "text": f"{self.amount_residual:.0f}"},
                    ],
                }
            ]
            fallback_text = (
                f"Bonjour {self.partner_id.name}, votre facture {self.name} "
                f"d'un montant de {self.amount_total:.0f} F CFA est disponible. "
                f"Montant restant : {self.amount_residual:.0f} F CFA. Equipe CCTS."
            )
            result = self._send_template_or_fallback(
                whatsapp_config, phone, "invoice_notification", components, fallback_text
            )

            conversation = self.env['whatsapp.conversation'].search([
                ('phone', '=', phone),
                ('contact_id', '=', self.partner_id.id)
            ], limit=1)
            if not conversation:
                conversation = self.env['whatsapp.conversation'].create({
                    'name': f"{self.partner_id.name} - {phone}",
                    'phone': phone,
                    'contact_id': self.partner_id.id,
                    'contact_name': self.partner_id.name,
                })
            if isinstance(result, dict) and result.get('message_record'):
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = self.partner_id.id

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Détails de la facture envoyés par WhatsApp à %s') % self.partner_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except ValidationError:
            raise
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi des détails de la facture")
            raise ValidationError(_("Erreur lors de l'envoi des détails : %s") % str(e))
    
    def action_send_whatsapp_invoice(self):
        """Action pour envoyer la facture par WhatsApp (appelée depuis le bouton)"""
        self.ensure_one()
        
        # Vérifie que c'est une facture client
        if self.move_type not in ['out_invoice', 'out_refund']:
            raise ValidationError(_("Cette fonctionnalité est uniquement disponible pour les factures clients."))
        
        # Vérifie que la facture est validée
        if self.state != 'posted':
            raise ValidationError(_("La facture doit être validée avant de pouvoir l'envoyer par WhatsApp."))
        
        # Vérifie qu'il y a un partenaire
        if not self.partner_id:
            raise ValidationError(_("Aucun partenaire associé à cette facture."))
        
        # Vérifie qu'il y a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)
        
        # Vérifie si la facture a déjà été envoyée
        if self.x_whatsapp_invoice_sent:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Cette facture a déjà été envoyée par WhatsApp le %s.') % (
                        self.x_whatsapp_invoice_sent_date.strftime('%d/%m/%Y %H:%M') if self.x_whatsapp_invoice_sent_date else _('date inconnue')
                    ),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Envoie la facture
        try:
            self._send_whatsapp_invoice()
            
            # Retourne une notification de succès
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Facture envoyée par WhatsApp à %s') % self.partner_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors de l'envoi de la facture : %s") % str(e))
    
    def _mark_invoice_sent(self):
        """Marque la facture comme envoyée par WhatsApp (utilisé pour éviter les doublons)"""
        self.ensure_one()
        if not self.x_whatsapp_invoice_sent:
            self.sudo().write({
                'x_whatsapp_invoice_sent': True,
                'x_whatsapp_invoice_sent_date': fields.Datetime.now()
            })
            _logger.info("Facture %s marquée comme envoyée par WhatsApp", self.name)

    def _send_template_or_fallback(self, whatsapp_config, phone, template_name, components, fallback_text):
        """Envoie un template WhatsApp.
        - Si 132001 (template inexistant sur Meta) : bascule vers invoice_message (approuvé).
        - Si 131049 (Meta bloque pour qualité d'écosystème) : logue sans retry, lève l'erreur.
        - Autre erreur : relance.
        """
        if not whatsapp_config or not whatsapp_config.is_active:
            raise ValidationError(_("Aucune configuration WhatsApp active."))
        try:
            return whatsapp_config.send_template_message(
                to_phone=phone,
                template_name=template_name,
                language_code="fr",
                components=components,
            )
        except ValidationError as e:
            err_str = str(e)
            if "132001" in err_str:
                _logger.warning(
                    "Template '%s' introuvable sur Meta (#132001) — fallback vers invoice_message. "
                    "Créez le template via 'Envoyer les templates vers WhatsApp'.",
                    template_name,
                )
                return whatsapp_config.send_template_message(
                    to_phone=phone,
                    template_name="invoice_message",
                    language_code="fr",
                    components=[{
                        "type": "body",
                        "parameters": [{"type": "text", "text": fallback_text}],
                    }],
                )
            if "131049" in err_str:
                _logger.warning(
                    "Message non livré pour %s — Meta a bloqué (131049 : qualité écosystème). "
                    "Le destinataire n'est peut-être pas abonné ou n'engage pas avec les messages.",
                    phone,
                )
                raise
            raise
    
    def _send_whatsapp_invoice(self):
        """Envoie le template invoice_notification lorsque la facture est validée. Non bloquant."""
        self.ensure_one()

        if not self.x_whatsapp_auto_send_attempted:
            self.sudo().write({'x_whatsapp_auto_send_attempted': True})

        if self.sudo().x_whatsapp_invoice_sent:
            _logger.debug("Facture %s déjà envoyée par WhatsApp, envoi ignoré", self.name)
            return

        if not self.partner_id:
            _logger.info("Facture %s: pas de partenaire associé, envoi WhatsApp non effectué", self.name)
            return

        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Facture %s: partenaire %s sans numéro, envoi WhatsApp non effectué", self.name, self.partner_id.name)
            return

        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.info("Facture %s: aucune configuration WhatsApp active, envoi non effectué", self.name)
            return

        # N'envoyer que pour les factures liées à un contrat de location toujours en cours
        if hasattr(self, 'rental_contract_id'):
            if not self.rental_contract_id:
                _logger.info("Facture %s: pas de contrat de location lié, envoi WhatsApp non effectué", self.name)
                return
            if self.rental_contract_id.state != 'active':
                _logger.info("Facture %s: contrat %s non actif, envoi WhatsApp non effectué",
                             self.name, self.rental_contract_id.name)
                return

        try:
            phone = whatsapp_config._validate_phone_number(phone, partner=self.partner_id)
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": self.partner_id.name},
                        {"type": "text", "text": self.name},
                        {"type": "text", "text": f"{self.amount_total:.0f}"},
                        {"type": "text", "text": f"{self.amount_residual:.0f}"},
                    ],
                }
            ]
            fallback_text = (
                f"Bonjour {self.partner_id.name}, votre facture {self.name} "
                f"d'un montant de {self.amount_total:.0f} F CFA est disponible. "
                f"Montant restant : {self.amount_residual:.0f} F CFA. Equipe CCTS."
            )
            result = self._send_template_or_fallback(
                whatsapp_config, phone, "invoice_notification", components, fallback_text
            )

            conversation = self.env['whatsapp.conversation'].search([
                ('phone', '=', phone),
                ('contact_id', '=', self.partner_id.id)
            ], limit=1)
            if not conversation:
                conversation = self.env['whatsapp.conversation'].create({
                    'name': f"{self.partner_id.name} - {phone}",
                    'phone': phone,
                    'contact_id': self.partner_id.id,
                    'contact_name': self.partner_id.name,
                })
            if isinstance(result, dict) and result.get('message_record'):
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = self.partner_id.id

            if not self.sudo().x_whatsapp_invoice_sent:
                self._mark_invoice_sent()
            _logger.info("Template invoice_notification envoyé pour la facture %s", self.name)

        except ValidationError as e:
            _logger.warning("Envoi WhatsApp facture %s non effectué (validation): %s", self.name, str(e))
        except Exception as e:
            _logger.warning("Envoi WhatsApp facture %s non effectué (non bloquant): %s", self.name, str(e))
    
    def _send_unpaid_invoice_reminder(self):
        """Envoie un rappel pour une facture impayée avec un message interactif et un bouton pour télécharger le PDF"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour le partenaire %s, rappel facture impayée non envoyé", self.partner_id.name)
            return
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer le rappel de facture impayée")
            return
        
        # Vérifie si le rappel a déjà été envoyé
        if self.x_whatsapp_unpaid_reminder_sent:
            _logger.info("Rappel facture impayée %s déjà envoyé, envoi ignoré", self.name)
            return
        
        try:
            # Nettoie le numéro de téléphone (prise en charge Sénégal +221 via pays du partenaire)
            phone = whatsapp_config._validate_phone_number(phone, partner=self.partner_id)
            
            # Génère le PDF de la facture et crée un lien public
            pdf_url = None
            try:
                # Essaie plusieurs méthodes pour trouver le rapport
                report = None
                report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
                
                Report = self.env['ir.actions.report'].sudo()
                for report_name in report_names:
                    try:
                        report = Report._get_report_from_name(report_name)
                        if report and report.exists() and report.id:
                            break
                        else:
                            report = None
                    except Exception:
                        report = None
                        continue
                
                if not report or not report.exists():
                    report = Report.search([
                        ('report_name', 'in', report_names),
                        ('model', '=', 'account.move')
                    ], limit=1)
                
                if report and report.exists():
                    # Génère le PDF (sudo pour éviter "Enregistrement inexistant" si règles d'accès)
                    pdf_content, _unused = report.sudo()._render_qweb_pdf(self.id)
                    
                    if pdf_content:
                        # Crée un attachment public pour le PDF
                        attachment = self.env['ir.attachment'].create({
                            'name': f"{self.name}.pdf",
                            'type': 'binary',
                            'datas': base64.b64encode(pdf_content),
                            'res_model': 'account.move',
                            'res_id': self.id,
                            'public': True,  # Important : rend le fichier accessible publiquement
                        })
                        
                        # Génère l'URL publique de téléchargement
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        _logger.info("URL PDF générée pour la facture %s: %s", self.name, pdf_url)
                else:
                    _logger.warning("Aucun rapport trouvé pour générer le PDF de la facture %s", self.name)
            except Exception as e:
                _logger.warning("Erreur lors de la génération du PDF pour la facture %s: %s", self.name, str(e))
            
            # Prépare le message avec les détails de la facture
            days_overdue = 0
            if self.invoice_date_due:
                today = fields.Date.today()
                days_overdue = (today - self.invoice_date_due).days
            
            message = f"Bonjour {self.partner_id.name},\n\n"
            message += f"📋 Rappel : Votre facture {self.name} n'est pas encore payée.\n\n"
            message += f"Montant dû : {self.amount_residual:.0f} F CFA\n"
            message += f"Montant total : {self.amount_total:.0f} F CFA\n"
            if self.invoice_date:
                message += f"Date facture : {self.invoice_date.strftime('%d/%m/%Y')}\n"
            if self.invoice_date_due:
                message += f"Date d'échéance : {self.invoice_date_due.strftime('%d/%m/%Y')}\n"
            if days_overdue > 0:
                message += f"Jours de retard : {days_overdue}\n"
            message += "\nVeuillez régler cette facture dans les plus brefs délais."
            
            # Crée un bouton pour télécharger le PDF
            buttons = []
            if pdf_url:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_download_invoice_{self.id}",
                        "title": "Télécharger PDF"
                    }
                })
            
            # Envoie le message : interactif si boutons, texte sinon
            if buttons:
                # Message interactif avec bouton(s) - WhatsApp exige entre 1 et 3 boutons
                result = whatsapp_config.send_interactive_message(
                    to_phone=phone,
                    body_text=message,
                    buttons=buttons
                )
            else:
                # Message texte simple si pas de boutons (PDF non disponible)
                result = whatsapp_config.send_invoice_message(
                    partner_id=self.partner_id.id,
                    message_text=message
                )
            
            # Crée ou met à jour la conversation
            conversation = self.env['whatsapp.conversation'].search([
                ('phone', '=', phone),
                ('contact_id', '=', self.partner_id.id)
            ], limit=1)
            
            if not conversation:
                conversation = self.env['whatsapp.conversation'].create({
                    'name': f"{self.partner_id.name} - {phone}",
                    'phone': phone,
                    'contact_id': self.partner_id.id,
                    'contact_name': self.partner_id.name,
                })
            
            # Lie le message à la conversation
            if result.get('message_record') and conversation:
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = self.partner_id.id
            
            # Marque le rappel comme envoyé si l'envoi a réussi
            if result.get('success'):
                self.sudo().write({
                    'x_whatsapp_unpaid_reminder_sent': True,
                    'x_whatsapp_unpaid_reminder_sent_date': fields.Datetime.now()
                })
                _logger.info("Rappel facture impayée WhatsApp envoyé avec succès pour la facture %s", self.name)
            else:
                _logger.warning("Échec de l'envoi du rappel facture impayée pour %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                
        except Exception as e:
            _logger.warning("Rappel facture impayée %s non envoyé (non bloquant): %s", self.name, str(e))
    
    @api.model
    def send_all_invoices_to_partner_whatsapp(self, partner_id, phone=None, include_links=False):
        """Envoie la facture impayée la plus ancienne d'un partenaire par WhatsApp,
        avec un bouton pour demander la facture impayée suivante.
        
        Args:
            partner_id: ID du partenaire ou objet partenaire
            phone: Numéro de téléphone (optionnel, récupéré depuis le partenaire si non fourni)
            include_links: Si True, inclut les liens de téléchargement directement dans le message texte
        
        Returns:
            dict: Résultat avec 'success', 'count', 'invoices_sent', 'errors'
        """
        # Récupère le partenaire
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        if not partner.exists():
            _logger.warning("Partenaire introuvable pour l'envoi des factures")
            return {'success': False, 'error': 'Partenaire introuvable', 'count': 0}
        
        # Récupère le numéro de téléphone
        if not phone:
            phone = partner.phone or partner.mobile
        
        if not phone:
            _logger.warning("Partenaire %s n'a pas de numéro de téléphone", partner.name)
            return {'success': False, 'error': 'Pas de numéro de téléphone', 'count': 0}
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            _logger.warning("Aucune configuration WhatsApp active trouvée")
            return {'success': False, 'error': 'Configuration WhatsApp non trouvée', 'count': 0}
        
        # Nettoie le numéro de téléphone (prise en charge Sénégal +221 via pays du partenaire)
        phone = whatsapp_config._validate_phone_number(phone, partner=partner)
        
        # Recherche toutes les factures du partenaire (validées) qui ne sont pas totalement payées
        # On les trie de la plus ancienne à la plus récente
        invoices = self.search([
            ('partner_id', '=', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('amount_residual', '>', 0)
        ], order='invoice_date asc, create_date asc')
        
        if not invoices:
            _logger.info("Aucune facture impayée trouvée pour le partenaire %s", partner.name)
            # Envoie un message indiquant qu'il n'y a pas de facture
            no_invoice_message = f"Bonjour {partner.name},\n\n"
            no_invoice_message += "Vous n'avez actuellement aucune facture impayée.\n\n"
            no_invoice_message += "Équipe CCTS"

            try:
                result = whatsapp_config.send_invoice_message(
                    partner_id=partner.id,
                    message_text=no_invoice_message
                )
                _logger.info("Message 'aucune facture impayée' envoyé pour le partenaire %s", partner.name)
            except Exception as e:
                _logger.warning(
                    "Erreur lors de l'envoi du message 'aucune facture impayée' pour le partenaire %s: %s",
                    partner.name, str(e)
                )

            return {
                'success': True,
                'count': 0,
                'invoices_sent': [],
                'message': 'Aucune facture impayée trouvée'
            }
        
        # On ne renvoie que la facture impayée la plus ancienne
        first_invoice = invoices[0]
        _logger.info(
            "Envoi de la facture impayée la plus ancienne %s au partenaire %s (téléphone: %s)",
            first_invoice.name, partner.name, phone
        )

        # S'il y a d'autres factures impayées après celle-ci, on prépare un bouton "Facture suivante"
        next_button_id = None
        if len(invoices) > 1:
            # Index de la prochaine facture dans la liste (0 = première, donc 1 = suivante)
            next_index = 1
            next_button_id = f"btn_next_invoice_{partner.id}_{next_index}"

        # Envoie la facture avec éventuellement le bouton "Facture suivante"
        try:
            result = first_invoice._send_invoice_details_whatsapp_direct(
                whatsapp_config,
                phone,
                include_links=include_links,
                next_button_id=next_button_id,
            )
            _logger.info("Facture %s envoyée avec succès", first_invoice.name)
        except Exception as e:
            _logger.warning(
                "Envoi facture impayée %s non effectué (non bloquant): %s",
                first_invoice.name, str(e)
            )
            return {
                'success': False,
                'count': 0,
                'invoices_sent': [],
                'errors': [str(e)],
                'total': len(invoices),
            }

        return {
            'success': True,
            'count': 1,
            'invoices_sent': [first_invoice.name],
            'errors': [],
            'total': len(invoices),
        }
    
    def _send_invoice_details_whatsapp_direct(self, whatsapp_config, phone, include_links=False, next_button_id=None):
        """Envoie les détails d'une facture directement (méthode interne, sans retour d'action)
        
        Args:
            whatsapp_config: Configuration WhatsApp à utiliser
            phone: Numéro de téléphone
            include_links: Si True, inclut le lien de téléchargement directement dans le message texte
            next_button_id: Si fourni, ajoute un bouton "Facture suivante" avec cet ID
        """
        self.ensure_one()
        
        # Vérifie si les attributs de paiement existent
        has_payment_links = hasattr(self, 'payment_link_wave') and hasattr(self, 'payment_link_orange_money')
        
        # S'assure que les liens de paiement existent si les attributs sont disponibles
        if has_payment_links:
            if hasattr(self, '_ensure_payment_links'):
                self._ensure_payment_links()
            elif not getattr(self, 'payment_link_wave', None) or not getattr(self, 'payment_link_orange_money', None):
                if hasattr(self, 'transaction_id') and self.transaction_id:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                    if not getattr(self, 'payment_link_wave', None):
                        self.payment_link_wave = f"{base_url}/paiement?type=wave&transaction={self.transaction_id}"
                    if not getattr(self, 'payment_link_orange_money', None):
                        self.payment_link_orange_money = f"{base_url}/paiement?type=orange&transaction={self.transaction_id}"
        
        # Construit le message avec les détails de la facture
        details_message = f"📋 Facture {self.name}\n\n"
        
        # Informations générales
        if self.invoice_date:
            details_message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
        if self.invoice_date_due:
            details_message += f"Échéance : {self.invoice_date_due.strftime('%d/%m/%Y')}\n"
        details_message += f"Montant total : {self.amount_total:.0f} {self.currency_id.symbol}\n"
        details_message += f"Montant restant : {self.amount_residual:.0f} {self.currency_id.symbol}\n\n"
        
        # Liste des produits/lignes (limité à 3 pour ne pas surcharger)
        if self.invoice_line_ids:
            details_message += "📦 Articles :\n"
            for line in self.invoice_line_ids[:3]:  # Limite à 3 articles
                product_name = line.product_id.name if line.product_id else line.name
                if len(product_name) > 30:
                    product_name = product_name[:27] + "..."
                details_message += f"• {product_name} - {line.quantity:.0f} × {line.price_unit:.0f} {self.currency_id.symbol}\n"
            
            if len(self.invoice_line_ids) > 3:
                details_message += f"... et {len(self.invoice_line_ids) - 3} autre(s) article(s)\n"
            details_message += "\n"
        
        # Totaux
        details_message += "─" * 30 + "\n"
        details_message += f"Total : {self.amount_total:.0f} {self.currency_id.symbol}\n\n"
        
        # Génère le PDF pour le bouton de téléchargement et prépare les liens à renvoyer
        pdf_url = None
        pdf_link_text = ""
        try:
            report = None
            report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
            Report = self.env['ir.actions.report'].sudo()
            for report_name in report_names:
                try:
                    report = Report._get_report_from_name(report_name)
                    if report and report.exists() and report.id:
                        break
                    else:
                        report = None
                except Exception:
                    report = None
                    continue
            
            if not report or not report.exists():
                report = Report.search([
                    ('report_name', 'in', report_names),
                    ('model', '=', 'account.move')
                ], limit=1)
            
            if report and report.exists():
                pdf_content, _unused = report.sudo()._render_qweb_pdf(self.id)
                
                if pdf_content:
                    attachment = self.env['ir.attachment'].create({
                        'name': f"{self.name}.pdf",
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'account.move',
                        'res_id': self.id,
                        'public': True,
                    })
                    
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    if base_url:
                        # Lien de téléchargement de la facture (PDF)
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        # Lien du formulaire (vue formulaire de la facture dans Odoo)
                        form_url = f"{base_url}/web#id={self.id}&model=account.move&view_type=form"
                        pdf_link_text = ""
                        if pdf_url:
                            pdf_link_text += f"\n📄 Télécharger la facture : {pdf_url}\n"
                        if form_url:
                            pdf_link_text += f"📝 Ouvrir le formulaire de la facture : {form_url}\n"
        except Exception as e:
            _logger.warning("Erreur lors de la génération du PDF pour la facture %s: %s", self.name, str(e))
        
        # Si include_links est True, ajoute les liens directement dans le message
        if include_links and pdf_link_text:
            details_message += pdf_link_text
        
        # Crée les boutons pour le message interactif
        buttons = []

        # Si on veut gérer une navigation "Facture suivante", on réserve de la place
        # pour ce bouton afin de ne jamais dépasser la limite de 3 boutons WhatsApp.
        reserve_for_next = bool(next_button_id)
        max_other_buttons = 2 if reserve_for_next else 3
        
        # Boutons de paiement (type reply) si montant résiduel > 0 ET si les attributs de paiement existent
        # Les boutons reply déclencheront une action qui enverra le lien de paiement
        if self.amount_residual > 0 and has_payment_links:
            payment_link_wave = getattr(self, 'payment_link_wave', None)
            payment_link_orange = getattr(self, 'payment_link_orange_money', None)
            
            # Bouton Wave (type reply qui enverra le lien)
            if payment_link_wave and len(buttons) < max_other_buttons:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_pay_wave_{self.id}",
                        "title": "Payer Wave"
                    }
                })
            
            # Bouton Orange Money (type reply qui enverra le lien)
            if payment_link_orange and len(buttons) < max_other_buttons:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_pay_orange_{self.id}",
                        "title": "Payer Orange"
                    }
                })
        
        # Bouton "Télécharger PDF" (type reply pour déclencher l'action de téléchargement)
        if pdf_url and len(buttons) < max_other_buttons:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"btn_download_invoice_{self.id}",
                    "title": "Télécharger PDF"
                }
            })

        # Bouton "Facture suivante" si demandé et si on a encore de la place
        if next_button_id and len(buttons) < 3:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": next_button_id,
                    "title": "Facture suivante",
                },
            })
        
        # Envoie le message : interactif si boutons disponibles, texte sinon
        # Si include_links est True et qu'on a des liens, on les ajoute dans le texte
        if include_links and pdf_link_text:
            details_message += pdf_link_text
        
        # Envoie le message interactif si on a des boutons
        if buttons:
            result = whatsapp_config.send_interactive_message(
                to_phone=phone,
                body_text=details_message,
                buttons=buttons
            )
        else:
            # Message texte simple si pas de boutons
            result = whatsapp_config.send_invoice_message(
                partner_id=self.partner_id.id,
                message_text=details_message
            )
        
        # Crée ou met à jour la conversation
        conversation = self.env['whatsapp.conversation'].search([
            ('phone', '=', phone),
            ('contact_id', '=', self.partner_id.id)
        ], limit=1)
        
        if not conversation:
            conversation = self.env['whatsapp.conversation'].create({
                'name': f"{self.partner_id.name} - {phone}",
                'phone': phone,
                'contact_id': self.partner_id.id,
                'contact_name': self.partner_id.name,
            })
        
        # Lie le message à la conversation
        if result.get('message_record') and conversation:
            result['message_record'].conversation_id = conversation.id
            result['message_record'].contact_id = self.partner_id.id
        
        return result
