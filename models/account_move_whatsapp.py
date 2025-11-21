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
                
                # Si la facture passe à l'état "posted" (validée), envoie la facture
                if (old_state_value != new_state_value and 
                    new_state_value == 'posted' and 
                    not record.x_whatsapp_invoice_sent):
                    _logger.info("Tentative d'envoi automatique de la facture %s (état: %s -> %s)", 
                               record.name, old_state_value, new_state_value)
                    try:
                        record._send_whatsapp_invoice()
                    except Exception as e:
                        _logger.warning("Erreur lors de l'envoi de la facture WhatsApp pour %s: %s", record.name, str(e))
                elif old_state_value != new_state_value and new_state_value == 'posted':
                    _logger.info("Facture %s déjà envoyée (x_whatsapp_invoice_sent=True), envoi ignoré", record.name)
                
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
        """Envoie un message WhatsApp avec le montant résiduel (reste à payer)"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour le partenaire %s, message WhatsApp résiduel non envoyé", self.partner_id.name)
            return
        
        # Vérifie si le message a déjà été envoyé (évite les doublons si le montant n'a pas vraiment changé)
        if self.x_whatsapp_residual_sent and abs(old_residual - new_residual) < 0.01:
            return
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            # Ne log pas d'avertissement en mode test
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer le message de montant résiduel")
            return
        
        try:
            # Nettoie le numéro de téléphone
            phone = whatsapp_config._validate_phone_number(phone)
            
            # Prépare le message
            message = f"Bonjour {self.partner_id.name},\n\n"
            message += f"Facture : {self.name}\n"
            message += f"Montant total : {self.amount_total:.0f} F CFA\n"
            message += f"Montant restant à payer : {new_residual:.0f} F CFA\n\n"
            
            # Calcule le montant payé
            amount_paid = self.amount_total - new_residual
            if amount_paid > 0:
                message += f"Montant déjà payé : {amount_paid:.0f} F CFA\n\n"
            
            # Ajoute un message selon le montant restant
            if new_residual < self.amount_total:
                message += "Un paiement partiel a été enregistré. Il reste un montant à régler."
            else:
                message += "Rappel : Cette facture est en attente de paiement."
            
            # Ajoute un lien vers la facture si disponible
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
            if base_url:
                invoice_url = f"{base_url}/web#id={self.id}&model=account.move&view_type=form"
                message += f"\n\nConsulter la facture : {invoice_url}"
            
            # Envoie le message via WhatsApp
            result = whatsapp_config.send_text_to_partner(
                partner_id=self.partner_id.id,
                message_text=message
            )
            
            # Met à jour la facture pour indiquer qu'un message a été envoyé
            if result.get('success'):
                self.write({
                    'x_whatsapp_residual_sent': True,
                    'x_whatsapp_residual_sent_date': fields.Datetime.now()
                })
                _logger.info("Message WhatsApp de montant résiduel envoyé avec succès pour la facture %s (reste: %s)", self.name, new_residual)
            else:
                _logger.warning("Échec de l'envoi du message WhatsApp de montant résiduel pour la facture %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi du message WhatsApp de montant résiduel pour la facture %s", self.name)
            # Ne lève pas d'exception pour ne pas bloquer la modification de la facture
    
    def action_send_invoice_details_whatsapp(self):
        """Envoie les détails de la facture par WhatsApp avec un bouton Payer"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            raise ValidationError(_("La facture n'a pas de partenaire associé."))
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        try:
            # Vérifie si les attributs de paiement existent (module res_api_rental)
            has_payment_links = hasattr(self, 'payment_link_wave') and hasattr(self, 'payment_link_orange_money')
            
            # S'assure que les liens de paiement existent si les attributs sont disponibles
            if has_payment_links:
                if hasattr(self, '_ensure_payment_links'):
                    self._ensure_payment_links()
                elif not self.payment_link_wave or not self.payment_link_orange_money:
                    # Si la méthode n'existe pas, on génère les liens si possible
                    if hasattr(self, 'transaction_id') and self.transaction_id:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                        if not self.payment_link_wave:
                            self.payment_link_wave = f"{base_url}/paiement?type=wave&transaction={self.transaction_id}"
                        if not self.payment_link_orange_money:
                            self.payment_link_orange_money = f"{base_url}/paiement?type=orange&transaction={self.transaction_id}"
            
            # Construit le message avec les détails de la facture
            details_message = f"📋 Détails de la facture {self.name}\n\n"
            
            # Informations générales
            details_message += f"Client : {self.partner_id.name if self.partner_id else 'N/A'}\n"
            details_message += f"Numéro : {self.name}\n"
            if self.invoice_date:
                details_message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
            if self.invoice_date_due:
                details_message += f"Date d'échéance : {self.invoice_date_due.strftime('%d/%m/%Y')}\n"
            details_message += f"Montant total : {self.amount_total:.0f} {self.currency_id.symbol}\n"
            details_message += f"Montant restant à payer : {self.amount_residual:.0f} {self.currency_id.symbol}\n\n"
            
            # Liste des produits/lignes
            if self.invoice_line_ids:
                details_message += "📦 Articles :\n"
                details_message += "─" * 30 + "\n"
                
                for line in self.invoice_line_ids:
                    product_name = line.product_id.name if line.product_id else line.name
                    quantity = line.quantity
                    unit_price = line.price_unit
                    subtotal = line.price_subtotal
                    
                    # Formate le nom du produit (limite à 30 caractères pour WhatsApp)
                    if len(product_name) > 30:
                        product_name = product_name[:27] + "..."
                    
                    details_message += f"• {product_name}\n"
                    details_message += f"  Qté : {quantity:.0f}"
                    
                    # Affiche l'unité si disponible
                    if line.product_uom_id:
                        details_message += f" {line.product_uom_id.name}"
                    
                    details_message += f" × {unit_price:.0f} {self.currency_id.symbol}\n"
                    details_message += f"  Sous-total : {subtotal:.0f} {self.currency_id.symbol}\n\n"
            else:
                details_message += "📦 Aucun article dans cette facture.\n\n"
            
            # Totaux
            details_message += "─" * 30 + "\n"
            details_message += f"Sous-total : {self.amount_untaxed:.0f} {self.currency_id.symbol}\n"
            
            if self.amount_tax > 0:
                details_message += f"TVA : {self.amount_tax:.0f} {self.currency_id.symbol}\n"
            
            details_message += f"Total : {self.amount_total:.0f} {self.currency_id.symbol}\n\n"
            
            # Footer
            details_message += "─" * 30 + "\n"
            details_message += "Équipe CCBM Shop"
            
            # Génère le PDF pour le bouton de téléchargement
            pdf_url = None
            try:
                # Essaie plusieurs méthodes pour trouver le rapport
                report = None
                report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
                
                for report_name in report_names:
                    try:
                        report = self.env['ir.actions.report']._get_report_from_name(report_name)
                        if report and report.exists() and report.id:
                            break
                        else:
                            report = None
                    except:
                        report = None
                        continue
                
                if not report or not report.exists():
                    report = self.env['ir.actions.report'].search([
                        ('report_name', 'in', report_names),
                        ('model', '=', 'account.move')
                    ], limit=1)
                
                if report and report.exists():
                    # Génère le PDF
                    pdf_content, _unused = report._render_qweb_pdf(self.id)
                    
                    if pdf_content:
                        # Crée un attachment public pour le PDF
                        attachment = self.env['ir.attachment'].create({
                            'name': f"{self.name}.pdf",
                            'type': 'binary',
                            'datas': base64.b64encode(pdf_content),
                            'res_model': 'account.move',
                            'res_id': self.id,
                            'public': True,
                        })
                        
                        # Génère l'URL publique de téléchargement
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        _logger.info("URL PDF générée pour la facture %s: %s", self.name, pdf_url)
            except Exception as e:
                _logger.warning("Erreur lors de la génération du PDF pour la facture %s: %s", self.name, str(e))
            
            # Crée les boutons pour le message interactif
            # WhatsApp exige entre 1 et 3 boutons
            buttons = []
            
            # Boutons de paiement (type reply) si montant résiduel > 0 ET si les attributs de paiement existent
            # Les boutons reply déclencheront une action qui enverra le lien de paiement
            if self.amount_residual > 0 and has_payment_links:
                # Vérifie que les liens de paiement sont disponibles
                payment_link_wave = getattr(self, 'payment_link_wave', None)
                payment_link_orange = getattr(self, 'payment_link_orange_money', None)
                
                # Bouton Wave (type reply qui enverra le lien)
                if payment_link_wave:
                    buttons.append({
                        "type": "reply",
                        "reply": {
                            "id": f"btn_pay_wave_{self.id}",
                            "title": "Payer Wave"
                        }
                    })
                
                # Bouton Orange Money (type reply qui enverra le lien)
                if payment_link_orange:
                    buttons.append({
                        "type": "reply",
                        "reply": {
                            "id": f"btn_pay_orange_{self.id}",
                            "title": "Payer Orange"
                        }
                    })
            
            # Bouton "Télécharger PDF" (type reply pour déclencher l'action de téléchargement)
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
                    body_text=details_message,
                    buttons=buttons
                )
            else:
                # Message texte simple si pas de boutons disponibles
                result = whatsapp_config.send_text_to_partner(
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
            
            # Retourne une notification de succès
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
    
    def _send_whatsapp_invoice(self):
        """Envoie la facture en PDF par WhatsApp lorsqu'elle est validée"""
        self.ensure_one()
        
        _logger.info("Début de l'envoi WhatsApp pour la facture %s", self.name)
        
        # Vérifie si la facture a déjà été envoyée (évite les doublons) - VÉRIFICATION EN PREMIER
        # Utilise sudo() pour vérifier même si l'utilisateur n'a pas les droits
        if self.sudo().x_whatsapp_invoice_sent:
            _logger.info("Facture %s déjà envoyée par WhatsApp (x_whatsapp_invoice_sent=True), envoi ignoré", self.name)
            return
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            _logger.warning("Facture %s n'a pas de partenaire associé, envoi WhatsApp annulé", self.name)
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.warning("Partenaire %s (ID: %s) n'a pas de numéro de téléphone, facture %s non envoyée", 
                         self.partner_id.name, self.partner_id.id, self.name)
            return
        
        _logger.info("Numéro de téléphone trouvé pour le partenaire %s: %s", self.partner_id.name, phone)
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            # Ne log pas d'avertissement en mode test
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer la facture %s", self.name)
            else:
                _logger.info("Mode test détecté, configuration WhatsApp non requise")
            return
        
        _logger.info("Configuration WhatsApp active trouvée (ID: %s)", whatsapp_config.id)
        
        try:
            # Nettoie le numéro de téléphone
            phone = whatsapp_config._validate_phone_number(phone)
            
            # Génère le PDF de la facture
            # Essaie plusieurs méthodes pour trouver le rapport
            report = None
            report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
            
            for report_name in report_names:
                try:
                    report = self.env['ir.actions.report']._get_report_from_name(report_name)
                    if report and report.exists() and report.id:
                        break
                    else:
                        report = None
                except Exception as e:
                    _logger.debug("Erreur lors de la recherche du rapport %s: %s", report_name, str(e))
                    report = None
                    continue
            
            # Si pas trouvé, cherche directement dans la base
            if not report or not report.exists():
                try:
                    report = self.env['ir.actions.report'].search([
                        ('report_name', 'in', report_names),
                        ('model', '=', 'account.move')
                    ], limit=1)
                    # Vérifie que le rapport existe vraiment
                    if report and not report.exists():
                        report = None
                except Exception as e:
                    _logger.debug("Erreur lors de la recherche du rapport dans la base: %s", str(e))
                    report = None
            
            # Si toujours pas de rapport, essaie de générer directement ou envoie juste le message texte
            if not report or not report.exists():
                _logger.info("Rapport de facture non trouvé pour %s, envoi du message texte uniquement", self.name)
                # Envoie juste un message texte avec les détails (pas de PDF)
                message = f"Bonjour {self.partner_id.name},\n\n"
                message += f"Votre facture {self.name} a été validée.\n\n"
                message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                if self.invoice_date:
                    message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                message += "\nMerci de votre confiance !"
                
                result = whatsapp_config.send_text_to_partner(
                    partner_id=self.partner_id.id,
                    message_text=message
                )
                # Marque immédiatement comme envoyé si succès
                if isinstance(result, dict) and result.get('success'):
                    self._mark_invoice_sent()
                pdf_content = None
            else:
                # Génère le PDF avec le rapport trouvé
                try:
                    # Vérifie que le rapport existe toujours avant de l'utiliser
                    if not report.exists():
                        raise Exception("Le rapport n'existe plus")
                    
                    # _render_qweb_pdf sur un objet report attend un ID unique (int)
                    pdf_content, _unused = report._render_qweb_pdf(self.id)
                except Exception as e:
                    _logger.warning("Erreur lors de la génération du PDF avec le rapport %s pour la facture %s: %s", 
                                  report.report_name if report else 'N/A', self.name, str(e))
                    # Essaie avec la méthode de classe en passant le nom du rapport
                    try:
                        if report and report.report_name:
                            pdf_content, _unused = self.env['ir.actions.report']._render_qweb_pdf(
                                report.report_name,
                                self.id
                            )
                        else:
                            pdf_content = None
                    except Exception as e2:
                        _logger.warning("Erreur avec méthode de classe: %s", str(e2))
                        pdf_content = None
                
                if not pdf_content:
                    _logger.info("Impossible de générer le PDF pour la facture %s, envoi du message texte uniquement", self.name)
                    # Envoie juste un message texte avec les détails
                    message = f"Bonjour {self.partner_id.name},\n\n"
                    message += f"Votre facture {self.name} a été validée.\n\n"
                    message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                    if self.invoice_date:
                        message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                    message += "\nMerci de votre confiance !"
                    
                    result = whatsapp_config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
                    # Marque immédiatement comme envoyé si succès
                    if isinstance(result, dict) and result.get('success'):
                        _logger.info("Message texte envoyé avec succès pour la facture %s (sans PDF)", self.name)
                        self._mark_invoice_sent()
                    else:
                        _logger.warning("Échec de l'envoi du message texte pour la facture %s: %s", 
                                      self.name, result.get('error', 'Erreur inconnue') if isinstance(result, dict) else 'Résultat invalide')
                    pdf_content = None
            
            # Si on a un PDF, envoie directement un message interactif avec bouton "Télécharger PDF"
            if pdf_content:
                try:
                    # Crée un attachement public pour le PDF
                    attachment = self.env['ir.attachment'].create({
                        'name': f"{self.name}.pdf",
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'account.move',
                        'res_id': self.id,
                        'public': True,  # Rend l'attachement public pour que WhatsApp puisse le télécharger
                    })
                    
                    # Génère une URL publique pour le PDF
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                    if base_url:
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        
                        # Prépare le message avec les détails de la facture
                        message = f"Bonjour {self.partner_id.name},\n\n"
                        message += f"✅ Votre facture {self.name} a été validée.\n\n"
                        message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                        if self.invoice_date:
                            message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                        message += "\nCliquez sur le bouton ci-dessous pour télécharger votre facture."
                        message += "\n\nMerci de votre confiance !"
                        message += "\n\nÉquipe CCBM Shop"
                        
                        # Crée un bouton "Télécharger PDF" qui déclenchera l'action de téléchargement
                        buttons = [{
                            "type": "reply",
                            "reply": {
                                "id": f"btn_download_invoice_{self.id}",
                                "title": "Télécharger PDF"
                            }
                        }]
                        
                        # Envoie le message interactif avec le bouton
                        result = whatsapp_config.send_interactive_message(
                            to_phone=phone,
                            body_text=message,
                            buttons=buttons
                        )
                        
                        # Marque immédiatement comme envoyé si succès
                        if isinstance(result, dict) and result.get('success'):
                            self._mark_invoice_sent()
                            _logger.info("Message interactif avec bouton téléchargement envoyé avec succès pour la facture %s", self.name)
                        else:
                            _logger.warning("Échec de l'envoi du message interactif pour la facture %s: %s", 
                                          self.name, result.get('error', 'Erreur inconnue') if isinstance(result, dict) else 'Résultat invalide')
                    else:
                        # Pas d'URL de base, envoie juste le message texte
                        message = f"Bonjour {self.partner_id.name},\n\n"
                        message += f"Votre facture {self.name} a été validée.\n\n"
                        message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                        if self.invoice_date:
                            message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                        message += "\nMerci de votre confiance !"
                        
                        result = whatsapp_config.send_text_to_partner(
                            partner_id=self.partner_id.id,
                            message_text=message
                        )
                        # Marque immédiatement comme envoyé si succès
                        if isinstance(result, dict) and result.get('success'):
                            self._mark_invoice_sent()
                except Exception as e:
                    _logger.warning("Erreur lors de la création de l'attachement PDF: %s", str(e))
                    # En cas d'erreur, essaie d'envoyer un message interactif avec bouton
                    # Si le PDF n'a pas pu être généré, on ne peut pas créer de lien, donc on envoie juste un message texte
                    message = f"Bonjour {self.partner_id.name},\n\n"
                    message += f"Votre facture {self.name} a été validée.\n\n"
                    message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                    if self.invoice_date:
                        message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                    message += "\nMerci de votre confiance !"
                    
                    result = whatsapp_config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
                    # Marque immédiatement comme envoyé si succès
                    if isinstance(result, dict) and result.get('success'):
                        self._mark_invoice_sent()
            
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
            
            # Normalise result pour avoir toujours un dict avec success
            if not isinstance(result, dict):
                # Si result n'est pas un dict, on le convertit
                if result is None:
                    result = {'success': False, 'error': 'Aucun résultat retourné'}
                else:
                    # Si result contient des données (ancien format), on considère que c'est un succès
                    result = {'success': True, 'data': result}
            
            # Lie le message à la conversation
            if result.get('message_record') and conversation:
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = self.partner_id.id
            
            # Vérification finale : si le message n'a pas encore été marqué comme envoyé et que l'envoi a réussi
            # (sécurité supplémentaire au cas où _mark_invoice_sent() n'aurait pas été appelé)
            if result.get('success') and not self.sudo().x_whatsapp_invoice_sent:
                self._mark_invoice_sent()
                _logger.info("Facture WhatsApp envoyée avec succès pour %s (marquage final)", self.name)
            elif not result.get('success'):
                _logger.warning("Échec de l'envoi de la facture WhatsApp pour %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                # Ne marque pas comme envoyé si l'envoi a échoué, pour permettre une nouvelle tentative
                
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi de la facture WhatsApp pour %s", self.name)
            # Ne lève pas d'exception pour ne pas bloquer la validation de la facture
    
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
            # Nettoie le numéro de téléphone
            phone = whatsapp_config._validate_phone_number(phone)
            
            # Génère le PDF de la facture et crée un lien public
            pdf_url = None
            try:
                # Essaie plusieurs méthodes pour trouver le rapport
                report = None
                report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
                
                for report_name in report_names:
                    try:
                        report = self.env['ir.actions.report']._get_report_from_name(report_name)
                        if report and report.exists() and report.id:
                            break
                        else:
                            report = None
                    except:
                        report = None
                        continue
                
                if not report or not report.exists():
                    report = self.env['ir.actions.report'].search([
                        ('report_name', 'in', report_names),
                        ('model', '=', 'account.move')
                    ], limit=1)
                
                if report and report.exists():
                    # Génère le PDF
                    pdf_content, _unused = report._render_qweb_pdf(self.id)
                    
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
                result = whatsapp_config.send_text_to_partner(
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
            _logger.exception("Erreur lors de l'envoi du rappel facture impayée pour la facture %s: %s", self.name, str(e))
    
    @api.model
    def send_all_invoices_to_partner_whatsapp(self, partner_id, phone=None, include_links=False):
        """Envoie toutes les factures d'un partenaire par WhatsApp
        
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
        
        # Nettoie le numéro de téléphone
        phone = whatsapp_config._validate_phone_number(phone)
        
        # Recherche toutes les factures du partenaire (validées) qui ne sont pas totalement payées
        invoices = self.search([
            ('partner_id', '=', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('amount_residual', '>', 0)  # Uniquement les factures non totalement payées
        ], order='create_date desc')
        
        if not invoices:
            _logger.info("Aucune facture trouvée pour le partenaire %s", partner.name)
            # Envoie un message indiquant qu'il n'y a pas de facture
            no_invoice_message = f"Bonjour {partner.name},\n\n"
            no_invoice_message += "Vous n'avez actuellement aucune facture.\n\n"
            no_invoice_message += "Équipe CCBM Shop"
            
            result = whatsapp_config.send_text_to_partner(
                partner_id=partner.id,
                message_text=no_invoice_message
            )
            
            return {
                'success': True,
                'count': 0,
                'invoices_sent': [],
                'message': 'Aucune facture trouvée'
            }
        
        _logger.info("Envoi de %d facture(s) au partenaire %s (téléphone: %s)", len(invoices), partner.name, phone)
        
        # Envoie d'abord un message d'introduction
        intro_message = f"Bonjour {partner.name},\n\n"
        intro_message += f"Voici vos {len(invoices)} facture(s) :\n\n"
        intro_message += "─" * 30 + "\n"
        
        result_intro = whatsapp_config.send_text_to_partner(
            partner_id=partner.id,
            message_text=intro_message
        )
        
        # Envoie chaque facture avec ses détails
        invoices_sent = []
        errors = []
        
        for invoice in invoices:
            try:
                # Utilise la méthode existante pour envoyer les détails de chaque facture
                # On simule l'appel de action_send_invoice_details_whatsapp mais sans retourner l'action
                invoice._send_invoice_details_whatsapp_direct(whatsapp_config, phone, include_links=include_links)
                invoices_sent.append(invoice.name)
                _logger.info("Facture %s envoyée avec succès", invoice.name)
                
                # Petite pause entre chaque envoi pour éviter de surcharger WhatsApp
                time.sleep(1)
                
            except Exception as e:
                error_msg = f"Erreur pour {invoice.name}: {str(e)}"
                errors.append(error_msg)
                _logger.exception("Erreur lors de l'envoi de la facture %s: %s", invoice.name, str(e))
        
        # Envoie un message de clôture
        if invoices_sent:
            closing_message = f"\n─" * 30 + "\n"
            closing_message += f"Total : {len(invoices_sent)} facture(s) envoyée(s).\n\n"
            closing_message += "Équipe CCBM Shop"
            
            whatsapp_config.send_text_to_partner(
                partner_id=partner.id,
                message_text=closing_message
            )
        
        return {
            'success': len(errors) == 0,
            'count': len(invoices_sent),
            'invoices_sent': invoices_sent,
            'errors': errors,
            'total': len(invoices)
        }
    
    def _send_invoice_details_whatsapp_direct(self, whatsapp_config, phone, include_links=False):
        """Envoie les détails d'une facture directement (méthode interne, sans retour d'action)
        
        Args:
            whatsapp_config: Configuration WhatsApp à utiliser
            phone: Numéro de téléphone
            include_links: Si True, inclut le lien de téléchargement directement dans le message texte
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
        
        # Génère le PDF pour le bouton de téléchargement
        pdf_url = None
        pdf_link_text = ""
        try:
            report = None
            report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
            
            for report_name in report_names:
                try:
                    report = self.env['ir.actions.report']._get_report_from_name(report_name)
                    if report and report.exists() and report.id:
                        break
                    else:
                        report = None
                except:
                    report = None
                    continue
            
            if not report or not report.exists():
                report = self.env['ir.actions.report'].search([
                    ('report_name', 'in', report_names),
                    ('model', '=', 'account.move')
                ], limit=1)
            
            if report and report.exists():
                pdf_content, _unused = report._render_qweb_pdf(self.id)
                
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
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        pdf_link_text = f"\n📄 Télécharger : {pdf_url}\n"
        except Exception as e:
            _logger.warning("Erreur lors de la génération du PDF pour la facture %s: %s", self.name, str(e))
        
        # Si include_links est True, ajoute le lien directement dans le message
        if include_links and pdf_url:
            details_message += pdf_link_text
        
        # Crée les boutons pour le message interactif
        buttons = []
        
        # Boutons de paiement (type reply) si montant résiduel > 0 ET si les attributs de paiement existent
        # Les boutons reply déclencheront une action qui enverra le lien de paiement
        if self.amount_residual > 0 and has_payment_links:
            payment_link_wave = getattr(self, 'payment_link_wave', None)
            payment_link_orange = getattr(self, 'payment_link_orange_money', None)
            
            # Bouton Wave (type reply qui enverra le lien)
            if payment_link_wave:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_pay_wave_{self.id}",
                        "title": "Payer Wave"
                    }
                })
            
            # Bouton Orange Money (type reply qui enverra le lien)
            if payment_link_orange:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_pay_orange_{self.id}",
                        "title": "Payer Orange"
                    }
                })
        
        # Bouton "Télécharger PDF" (type reply pour déclencher l'action de téléchargement)
        if pdf_url:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"btn_download_invoice_{self.id}",
                    "title": "Télécharger PDF"
                }
            })
        
        # Envoie le message : interactif si boutons disponibles, texte sinon
        # Si include_links est True et qu'on a un PDF, on ajoute le lien dans le texte aussi
        if include_links and pdf_url:
            # Ajoute le lien PDF dans le message texte
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
            result = whatsapp_config.send_text_to_partner(
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
