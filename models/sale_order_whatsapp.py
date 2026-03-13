# whatsapp_business_api/models/sale_order_whatsapp.py
# Ce fichier nécessite le module 'sale' pour fonctionner
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import config
from datetime import datetime
import logging
import json
import base64

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.depends()
    def _compute_show_whatsapp_button(self):
        """Calcule si le bouton WhatsApp doit être affiché selon la configuration"""
        config = self.env['whatsapp.config'].get_active_config()
        show_button = config.show_button_in_order if config else True
        for record in self:
            record.x_show_whatsapp_button = show_button
    
    x_show_whatsapp_button = fields.Boolean(
        string="Afficher bouton WhatsApp",
        compute="_compute_show_whatsapp_button",
        store=False,
        help="Indique si le bouton WhatsApp doit être affiché selon la configuration"
    )
    
    @api.depends('partner_id', 'partner_id.phone', 'partner_id.mobile')
    def _compute_has_phone(self):
        """Calcule si le partenaire a un numéro de téléphone"""
        for record in self:
            record.x_has_phone = bool(record.partner_id and (record.partner_id.phone or record.partner_id.mobile))
    
    x_has_phone = fields.Boolean(
        string="A un numéro de téléphone",
        compute="_compute_has_phone",
        store=False,
        help="Indique si le partenaire a un numéro de téléphone"
    )

    x_whatsapp_validation_sent = fields.Boolean(
        string="Validation WhatsApp envoyée",
        default=False,
        help="Indique si un message de validation a été envoyé via WhatsApp"
    )
    
    x_whatsapp_validation_sent_date = fields.Datetime(
        string="Date envoi validation WhatsApp"
    )
    
    x_whatsapp_validated = fields.Boolean(
        string="Validée via WhatsApp",
        default=False,
        help="Indique si la commande a été validée via WhatsApp"
    )
    
    x_whatsapp_rejected = fields.Boolean(
        string="Rejetée via WhatsApp",
        default=False,
        help="Indique si la commande a été rejetée via WhatsApp"
    )
    
    x_whatsapp_creation_sent = fields.Boolean(
        string="Message de création WhatsApp envoyé",
        default=False,
        help="Indique si un message de confirmation de création a été envoyé via WhatsApp"
    )
    
    x_whatsapp_creation_sent_date = fields.Datetime(
        string="Date envoi message création WhatsApp"
    )
    
    x_whatsapp_state_sent = fields.Boolean(
        string="Message d'état WhatsApp envoyé",
        default=False,
        help="Indique si un message de changement d'état a été envoyé via WhatsApp"
    )
    
    x_whatsapp_state_sent_date = fields.Datetime(
        string="Date envoi message d'état WhatsApp"
    )
    
    x_whatsapp_details_sent = fields.Boolean(
        string="Détails commande WhatsApp envoyés",
        default=False,
        help="Indique si les détails de la commande ont été envoyés via WhatsApp après le clic sur le bouton"
    )
    
    x_whatsapp_details_sent_date = fields.Datetime(
        string="Date envoi détails WhatsApp"
    )

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """Surcharge la méthode create pour envoyer un message WhatsApp à la création"""
    #     # Crée les commandes
    #     orders = super().create(vals_list)
        
    #     # Envoie un message WhatsApp pour chaque commande créée
    #     # La méthode _should_send_whatsapp_notification vérifie automatiquement :
    #     # - Si c'est une commande à crédit (exclue)
    #     # - Si l'envoi automatique est activé
    #     # - Si le message n'a pas déjà été envoyé
    #     for order in orders:
    #         try:
    #             order._send_whatsapp_creation_notification()
    #         except Exception as e:
    #             _logger.warning("Erreur lors de l'envoi du message WhatsApp de création pour la commande %s: %s", order.name, str(e))
    #             # Ne bloque pas la création de la commande si l'envoi échoue
        
    #     return orders

    def _get_invoice_pdf_url(self, invoice):
        """Génère l'URL publique de téléchargement du PDF d'une facture
        
        Args:
            invoice: Objet account.move (facture)
            
        Returns:
            str: URL publique de téléchargement ou None si erreur
        """
        if not invoice or not invoice.exists():
            return None
        
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
                invoice_pdf_content = None
                try:
                    invoice_pdf_content, _unused = report._render_qweb_pdf(invoice.id)
                except (OSError, ConnectionError) as e:
                    _logger.info("Génération PDF facture %s indisponible (réseau): %s", invoice.name, str(e))
                except Exception as e:
                    _logger.debug("Génération PDF facture %s échouée: %s", invoice.name, str(e))
                if invoice_pdf_content:
                    # Crée un attachment public pour le PDF de la facture
                    invoice_attachment = self.env['ir.attachment'].create({
                        'name': f"{invoice.name}.pdf",
                        'type': 'binary',
                        'datas': base64.b64encode(invoice_pdf_content),
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'public': True,
                    })
                    
                    # Génère l'URL publique de téléchargement
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    invoice_pdf_url = f"{base_url}/web/content/{invoice_attachment.id}?download=true"
                    _logger.info("URL PDF facture générée pour la commande %s: %s", self.name, invoice_pdf_url)
                    return invoice_pdf_url
        except Exception as e:
            _logger.warning("Erreur lors de la génération du PDF de la facture %s pour la commande %s: %s", 
                          invoice.name if invoice else 'N/A', self.name, str(e))
        
        return None
    
    def _get_confirmed_invoice(self):
        """Récupère la facture confirmée (posted) la plus récente associée à la commande
        
        Returns:
            account.move ou None: La facture confirmée la plus récente ou None
        """
        invoice = self.env['account.move'].search([
            ('invoice_origin', '=', self.name),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')  # Seulement les factures confirmées
        ], order='create_date desc', limit=1)
        
        return invoice if invoice else None
    
    def _should_send_whatsapp_notification(self, notification_type='creation'):
        """
        Vérifie si un message WhatsApp doit être envoyé pour cette commande.
        
        Cette méthode centralise la logique pour éviter les doublons et les conflits
        avec le système de notifications pour les commandes à crédit.
        
        Args:
            notification_type: Type de notification ('creation', 'state_change')
            
        Returns:
            bool: True si le message doit être envoyé, False sinon
        """
        self.ensure_one()
        
        # Ne pas envoyer pour les commandes à crédit (gérées par whatsapp.admin.notification)
        if hasattr(self, 'type_sale') and self.type_sale == 'creditorder':
            _logger.debug("Commande %s est une commande à crédit, notification WhatsApp standard ignorée", self.name)
            return False
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return False
        
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            return False
        
        # Vérifie la configuration WhatsApp
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            return False
        
        # Vérifie si l'envoi automatique est activé (pour les notifications de création)
        if notification_type == 'creation':
            if not whatsapp_config.auto_send_order_creation:
                return False
            
            # Vérifie si le message a déjà été envoyé
            if self.x_whatsapp_creation_sent:
                return False
        
        # Pour les changements d'état, vérifie que l'état est 'sale' ou 'done'
        if notification_type == 'state_change':
            if self.state not in ['sale', 'done']:
                return False
            
            # Vérifie si le message a déjà été envoyé pour cet état
            if self.x_whatsapp_state_sent and self.state in ['sale', 'done']:
                return False
        
        return True
    
    def _send_template_or_fallback(self, whatsapp_config, phone, template_name, components, fallback_text):
        """Envoie un template WhatsApp. Si le template n'existe pas sur Meta (132001),
        bascule automatiquement vers invoice_message (approuvé) avec le texte complet."""
        from odoo.exceptions import ValidationError as VE
        try:
            return whatsapp_config.send_template_message(
                to_phone=phone,
                template_name=template_name,
                language_code="fr",
                components=components,
            )
        except VE as e:
            if "132001" in str(e):
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
            raise

    def _send_whatsapp_creation_notification(self):
        """Envoie un message WhatsApp (template order_created) pour confirmer la création de la commande."""
        self.ensure_one()

        if not self._should_send_whatsapp_notification(notification_type='creation'):
            return

        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            return
        phone = self.partner_id.phone or self.partner_id.mobile

        try:
            phone = whatsapp_config._validate_phone_number(phone)
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": self.partner_id.name},
                        {"type": "text", "text": self.name},
                        {"type": "text", "text": f"{self.amount_total:.0f}"},
                    ],
                }
            ]
            fallback_text = (
                f"Bonjour {self.partner_id.name}, votre commande {self.name} "
                f"a ete enregistree. Montant : {self.amount_total:.0f} F CFA. Equipe CCTS."
            )
            result = self._send_template_or_fallback(
                whatsapp_config, phone, "order_created", components, fallback_text
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

            if not isinstance(result, dict) or result.get('success') is not False:
                self.write({
                    'x_whatsapp_creation_sent': True,
                    'x_whatsapp_creation_sent_date': fields.Datetime.now(),
                })
                _logger.info("Template order_created envoyé pour la commande %s", self.name)
            else:
                _logger.warning("Échec envoi order_created pour commande %s: %s", self.name, result.get('error'))

        except Exception as e:
            _logger.warning("Envoi WhatsApp création commande %s non effectué (non bloquant): %s", self.name, str(e))

    def write(self, vals):
        """Surcharge write pour détecter les changements d'état et envoyer un message"""
        # Sauvegarde l'ancien état avant la modification
        old_state = {}
        if 'state' in vals:
            for record in self:
                old_state[record.id] = record.state
        
        # Effectue la modification
        result = super().write(vals)
        
        # Si l'état a changé, envoie un message
        if 'state' in vals:
            for record in self:
                new_state = vals.get('state')
                old_state_value = old_state.get(record.id)
                
                # IMPORTANT: Ne pas envoyer pour les commandes à crédit (gérées par whatsapp.admin.notification)
                if hasattr(record, 'type_sale') and record.type_sale == 'creditorder':
                    continue
                
                # Envoie un message si l'état change vers 'sale' (confirmé) ou 'done' (terminé)
                if old_state_value != new_state and new_state in ['sale', 'done']:
                    # Vérifie si le message doit être envoyé (méthode centralisée)
                    if record._should_send_whatsapp_notification(notification_type='state_change'):
                        try:
                            record._send_whatsapp_state_notification(new_state, old_state_value)
                        except Exception as e:
                            _logger.warning("Erreur lors de l'envoi du message WhatsApp d'état pour la commande %s: %s", record.name, str(e))
        
        return result

    def _send_whatsapp_state_notification(self, new_state, old_state):
        """Envoie un message WhatsApp (template order_confirmed) lors d'un changement d'état."""
        self.ensure_one()

        if not self._should_send_whatsapp_notification(notification_type='state_change'):
            return

        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            return
        phone = self.partner_id.phone or self.partner_id.mobile

        try:
            phone = whatsapp_config._validate_phone_number(phone)

            state_labels = {
                'draft': 'Brouillon',
                'sent': 'Envoyee',
                'sale': 'Confirmee',
                'done': 'Terminee',
                'cancel': 'Annulee',
            }
            state_label = state_labels.get(new_state, new_state)

            # Utilise le montant de la facture confirmée si disponible, sinon celui de la commande
            invoice = self._get_confirmed_invoice()
            amount = invoice.amount_total if invoice else self.amount_total

            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": self.partner_id.name},
                        {"type": "text", "text": self.name},
                        {"type": "text", "text": state_label},
                        {"type": "text", "text": f"{amount:.0f}"},
                    ],
                }
            ]
            fallback_text = (
                f"Bonjour {self.partner_id.name}, votre commande {self.name} est {state_label}. "
                f"Montant : {amount:.0f} F CFA. Merci pour votre confiance. Equipe CCTS."
            )
            result = self._send_template_or_fallback(
                whatsapp_config, phone, "order_confirmed", components, fallback_text
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

            if not isinstance(result, dict) or result.get('success') is not False:
                self.write({
                    'x_whatsapp_state_sent': True,
                    'x_whatsapp_state_sent_date': fields.Datetime.now(),
                })
                _logger.info("Template order_confirmed envoyé pour la commande %s (état: %s)", self.name, new_state)
            else:
                _logger.warning("Échec envoi order_confirmed pour commande %s: %s", self.name, result.get('error'))

        except Exception as e:
            _logger.warning("Envoi WhatsApp d'état pour la commande %s non effectué (non bloquant): %s", self.name, str(e))

    def action_send_order_validation_whatsapp(self):
        """Envoie les détails de la commande via WhatsApp pour validation"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            raise ValidationError(_("Aucun partenaire associé à cette commande."))
        
        if not self.partner_id.phone:
            raise ValidationError(_("Le partenaire n'a pas de numéro de téléphone."))
        
        # Vérifie que la commande n'est pas déjà validée ou annulée
        if self.state in ['cancel', 'done']:
            raise ValidationError(_("Impossible d'envoyer une validation pour une commande annulée ou terminée."))
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        # Nettoie le numéro de téléphone
        phone = whatsapp_config._validate_phone_number(self.partner_id.phone)
        
        # Prépare les paramètres du template
        # Paramètres : {{1}} = Numéro commande, {{2}} = Montant en F CFA
        # Format du template :
        # Bonjour ,
        # Détails de votre commande :
        # - Numéro : {{1}}
        # - Montant : {{2}} F CFA
        # Souhaitez-vous valider cette commande ?
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": self.name},  # {{1}} = Numéro de commande
                    {"type": "text", "text": f"{self.amount_total:.0f}"}  # {{2}} = Montant (sans décimales pour F CFA)
                ]
            }
        ]
        
        try:
            # Envoie le template
            result = whatsapp_config.send_template_message(
                to_phone=phone,
                template_name="order_validation",
                language_code="fr",
                components=components
            )
            
            # Met à jour la commande pour indiquer qu'un message a été envoyé
            self.write({
                'x_whatsapp_validation_sent': True,
                'x_whatsapp_validation_sent_date': fields.Datetime.now()
            })
            
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
                # Stocke le numéro de commande dans le message pour faciliter la recherche
                result['message_record'].write({
                    'content': f"Validation commande {self.name}"
                })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Message de validation envoyé à %s') % self.partner_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi du message de validation")
            raise ValidationError(_("Erreur lors de l'envoi du message : %s") % str(e))
    
    def action_send_order_details_whatsapp(self):
        """Envoie une notification WhatsApp (template invoice_notification) avec les détails de la commande."""
        self.ensure_one()

        if not self.partner_id:
            raise ValidationError(_("La commande n'a pas de partenaire associé."))

        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)

        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))

        try:
            phone = whatsapp_config._validate_phone_number(phone)

            # Utilise la facture confirmée si disponible, sinon les montants de la commande
            invoice = self._get_confirmed_invoice()
            if invoice:
                invoice_name = invoice.name
                amount_total = invoice.amount_total
                amount_residual = invoice.amount_residual
            else:
                invoice_name = self.name
                amount_total = self.amount_total
                amount_residual = self.amount_total

            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": self.partner_id.name},
                        {"type": "text", "text": invoice_name},
                        {"type": "text", "text": f"{amount_total:.0f}"},
                        {"type": "text", "text": f"{amount_residual:.0f}"},
                    ],
                }
            ]
            fallback_text = (
                f"Bonjour {self.partner_id.name}, votre facture {invoice_name} "
                f"d'un montant de {amount_total:.0f} F CFA est disponible. "
                f"Montant restant : {amount_residual:.0f} F CFA. Equipe CCTS."
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

            self.write({
                'x_whatsapp_details_sent': True,
                'x_whatsapp_details_sent_date': fields.Datetime.now(),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Détails de la commande envoyés par WhatsApp à %s') % self.partner_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except ValidationError:
            raise
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi des détails de la commande")
            raise ValidationError(_("Erreur lors de l'envoi des détails : %s") % str(e))
