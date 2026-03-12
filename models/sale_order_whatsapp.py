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
    
    def _send_whatsapp_creation_notification(self):
        """Envoie un message WhatsApp pour confirmer la création de la commande
        
        Note: 
        - La facture n'est envoyée que si la commande est en 'sale' ou 'done'
        - Les commandes à crédit sont exclues (gérées par whatsapp.admin.notification)
        """
        self.ensure_one()
        
        # Vérifie si le message doit être envoyé (méthode centralisée)
        if not self._should_send_whatsapp_notification(notification_type='creation'):
            return
        
        # Récupère la configuration WhatsApp active (déjà vérifiée dans _should_send_whatsapp_notification)
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            _logger.debug("Commande %s: pas de config WhatsApp active, notification de création non envoyée", self.name)
            return
        phone = self.partner_id.phone or self.partner_id.mobile

        try:
            # Prépare un message avec 3 boutons : Valider, Annuler, Voir détail
            message = f"Bonjour {self.partner_id.name},\n\nVotre commande {self.name} a été créée avec succès.\n\nEquipe CCBM SHOP"
            
            # Génère le PDF pour le bouton de téléchargement
            pdf_url = None
            try:
                # Essaie plusieurs méthodes pour trouver le rapport
                report = None
                report_names = ['sale.report_saleorder', 'sale.action_report_saleorder']
                
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
                        ('model', '=', 'sale.order')
                    ], limit=1)
                
                if report and report.exists():
                    try:
                        pdf_content, _unused = report._render_qweb_pdf(self.id)
                    except (OSError, ConnectionError) as e:
                        _logger.info("Génération PDF commande %s indisponible (réseau): %s", self.name, str(e))
                        pdf_content = None
                    if pdf_content:
                        # Crée un attachment public pour le PDF
                        attachment = self.env['ir.attachment'].create({
                            'name': f"{self.name}.pdf",
                            'type': 'binary',
                            'datas': base64.b64encode(pdf_content),
                            'res_model': 'sale.order',
                            'res_id': self.id,
                            'public': True,
                        })
                        
                        # Génère l'URL publique de téléchargement
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        _logger.info("URL PDF générée pour la commande %s: %s", self.name, pdf_url)
            except Exception as e:
                _logger.warning("Erreur lors de la génération du PDF pour la commande %s: %s", self.name, str(e))
            
            # Ajoute les boutons : Valider, Annuler, Voir détail, et Télécharger PDF si disponible
            # L'ID de la commande est inclus dans l'ID du bouton pour l'identifier
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": f"btn_view_order_details_{self.id}",
                        "title": "Voir détail"
                    }
                }
            ]
            
            # IMPORTANT: Cherche les factures confirmées UNIQUEMENT si la commande est en 'sale' ou 'done'
            invoice_pdf_url = None
            invoice = None
            
            if self.state in ['sale', 'done']:
                invoice = self._get_confirmed_invoice()
                if invoice:
                    invoice_pdf_url = self._get_invoice_pdf_url(invoice)
            
            # Si facture disponible, ajoute le bouton "Télécharger facture" (priorité)
            # Sinon, si PDF commande disponible, ajoute "Télécharger devis"
            if invoice_pdf_url and invoice:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_download_invoice_{invoice.id}",
                        "title": "Télécharger facture"
                    }
                })
            elif pdf_url:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_download_order_{self.id}",
                        "title": "Télécharger devis"
                    }
                })
            
            # Envoie le message interactif avec les boutons
            phone = whatsapp_config._validate_phone_number(phone)
            result = whatsapp_config.send_interactive_message(
                to_phone=phone,
                body_text=message,
                buttons=buttons
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
            
            # Lie le message à la conversation et au partenaire
            if result.get('message_record'):
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = self.partner_id.id
            
            # Met à jour la commande pour indiquer qu'un message a été envoyé (uniquement si succès)
            # Cela garantit qu'un message n'est envoyé qu'une seule fois
            if result.get('success'):
                self.write({
                    'x_whatsapp_creation_sent': True,
                    'x_whatsapp_creation_sent_date': fields.Datetime.now()
                })
                _logger.info("Message WhatsApp de création envoyé avec succès pour la commande %s", self.name)
            else:
                _logger.warning("Échec de l'envoi du message WhatsApp pour la commande %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                # Ne marque pas comme envoyé si l'envoi a échoué, pour permettre une nouvelle tentative
                
        except Exception as e:
            _logger.warning("Envoi WhatsApp création commande %s non effectué (non bloquant): %s", self.name, str(e))
            # Ne lève pas d'exception pour ne pas bloquer la création de la commande

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
        """Envoie un message WhatsApp avec l'état de la commande, la facture et le nouveau montant
        
        Note: 
        - Les commandes à crédit sont exclues (gérées par whatsapp.admin.notification)
        - La facture n'est envoyée que si elle est confirmée (state='posted')
        """
        self.ensure_one()
        
        # Vérifie si le message doit être envoyé (méthode centralisée)
        if not self._should_send_whatsapp_notification(notification_type='state_change'):
            return
        
        # Récupère la configuration WhatsApp active (déjà vérifiée dans _should_send_whatsapp_notification)
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            _logger.debug("Commande %s: pas de config WhatsApp active, notification d'état non envoyée", self.name)
            return
        phone = self.partner_id.phone or self.partner_id.mobile

        try:
            # Nettoie le numéro de téléphone (peut lever ValidationError → capturé ci-dessous)
            phone = whatsapp_config._validate_phone_number(phone)
            
            # Prépare le message avec l'état
            state_labels = {
                'draft': 'Brouillon',
                'sent': 'Envoyée',
                'sale': 'Confirmée',
                'done': 'Terminée',
                'cancel': 'Annulée'
            }
            
            state_label = state_labels.get(new_state, new_state)
            
            message = f"Bonjour {self.partner_id.name},\n\n"
            message += f"État de votre commande {self.name} : {state_label}\n\n"
            
            # IMPORTANT: Récupère UNIQUEMENT les factures confirmées (posted)
            invoice = self._get_confirmed_invoice()
            
            if invoice:
                invoice_amount = invoice.amount_total
                
                message += f"Facture : {invoice.name}\n"
                message += f"Nouveau montant : {invoice_amount:.0f} F CFA\n"
                
                # Affiche la date de la facture si disponible
                if invoice.invoice_date:
                    message += f"Date facture : {invoice.invoice_date.strftime('%d/%m/%Y')}\n"
                
                message += "\n"
                message += "Equipe CCBM SHOP"
            else:
                # Si pas de facture confirmée, utilise le montant de la commande
                message += f"Montant commande : {self.amount_total:.0f} F CFA\n\n"
            
            # Ajoute un message selon l'état
            # IMPORTANT: La facture n'est envoyée que si la commande est en 'sale' ou 'done'
            if new_state in ['sale', 'done']:
                # Génère le PDF de la facture et crée le bouton de téléchargement
                invoice_pdf_url = None
                
                # Vérifie que la facture existe et est confirmée
                if invoice and invoice.state == 'posted':
                    invoice_pdf_url = self._get_invoice_pdf_url(invoice)
                
                # Prépare le message avec la facture
                message += "\nMerci pour votre confiance."
                message += "\n\nÉquipe CCTS"
                
                # Si on a une facture confirmée avec PDF, envoie un message interactif avec bouton
                if invoice_pdf_url and invoice:
                    buttons = [{
                        "type": "reply",
                        "reply": {
                            "id": f"btn_download_invoice_{invoice.id}",
                            "title": "Télécharger facture"
                        }
                    }]
                    
                    # Envoie le message interactif avec le bouton
                    result = whatsapp_config.send_interactive_message(
                        to_phone=phone,
                        body_text=message,
                        buttons=buttons
                    )
                else:
                    # Envoie le message texte simple (pas de facture confirmée ou PDF non disponible)
                    result = whatsapp_config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
            else:
                # Autres états (draft, sent, cancel), envoie le message texte simple
                # Pas d'envoi de facture pour ces états
                result = whatsapp_config.send_text_to_partner(
                    partner_id=self.partner_id.id,
                    message_text=message
                )
            
            # Met à jour la commande pour indiquer qu'un message a été envoyé
            if result.get('success'):
                self.write({
                    'x_whatsapp_state_sent': True,
                    'x_whatsapp_state_sent_date': fields.Datetime.now()
                })
                _logger.info("Message WhatsApp d'état envoyé avec succès pour la commande %s (état: %s)", self.name, new_state)
            else:
                _logger.warning("Échec de l'envoi du message WhatsApp d'état pour la commande %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                
        except Exception as e:
            _logger.warning("Envoi WhatsApp d'état pour la commande %s non effectué (non bloquant): %s", self.name, str(e))
            # Ne lève pas d'exception pour ne pas bloquer la modification de la commande

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
        """Envoie les détails de la commande par WhatsApp"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            raise ValidationError(_("La commande n'a pas de partenaire associé."))
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        try:
            # Construit le message avec les détails de la commande
            details_message = f"Détails de la commande {self.name}\n\n"
            
            # Informations générales
            details_message += f"Client : {self.partner_id.name if self.partner_id else 'N/A'}\n"
            details_message += f"Numéro : {self.name}\n"
            details_message += f"Date : {self.date_order.strftime('%d/%m/%Y %H:%M') if self.date_order else 'N/A'}\n"
            details_message += f"Montant total : {self.amount_total:.0f} F CFA\n\n"
            
            # Calcule le montant non payé et mentionne la facture si elle existe
            unpaid_amount = self.amount_total
            # Récupère toutes les factures confirmées pour calculer les montants
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', self.name),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ], order='create_date desc')
            
            if invoices:
                total_paid = sum(invoices.mapped('amount_total')) - sum(invoices.mapped('amount_residual'))
                unpaid_amount = sum(invoices.mapped('amount_residual'))
                
                # Mentionne la facture la plus récente
                latest_invoice = invoices[0]
                details_message += f"📄 Facture : {latest_invoice.name}\n"
                if latest_invoice.invoice_date:
                    details_message += f"Date facture : {latest_invoice.invoice_date.strftime('%d/%m/%Y')}\n"
                details_message += f"Montant payé : {total_paid:.0f} F CFA\n"
                details_message += f"Montant non payé : {unpaid_amount:.0f} F CFA\n\n"
            else:
                details_message += f"Montant non payé : {unpaid_amount:.0f} F CFA\n\n"
            
            # Liste des produits
            if self.order_line:
                details_message += "Produits :\n"
                details_message += "─" * 30 + "\n"
                
                for line in self.order_line:
                    product_name = line.product_id.name if line.product_id else line.name
                    quantity = line.product_uom_qty
                    unit_price = line.price_unit
                    subtotal = line.price_subtotal
                    
                    # Formate le nom du produit (limite à 30 caractères pour WhatsApp)
                    if len(product_name) > 30:
                        product_name = product_name[:27] + "..."
                    
                    details_message += f"• {product_name}\n"
                    details_message += f"  Qté : {quantity:.0f}"
                    
                    # Affiche l'unité si disponible
                    if line.product_uom:
                        details_message += f" {line.product_uom.name}"
                    
                    details_message += f" × {unit_price:.0f} F CFA\n"
                    details_message += f"  Sous-total : {subtotal:.0f} F CFA\n\n"
            else:
                details_message += "📦 Aucun produit dans cette commande.\n\n"
            
            # Totaux
            details_message += "─" * 30 + "\n"
            details_message += f"Sous-total : {self.amount_untaxed:.0f} F CFA\n"
            
            if self.amount_tax > 0:
                details_message += f"TVA : {self.amount_tax:.0f} F CFA\n"
            
            details_message += f"Total : {self.amount_total:.0f} F CFA\n\n"
            
            # Informations supplémentaires
            if self.partner_id.street:
                details_message += f"📍 Adresse : {self.partner_id.street}\n"
                if self.partner_id.city:
                    details_message += f"   {self.partner_id.city}"
                    if self.partner_id.zip:
                        details_message += f" {self.partner_id.zip}"
                    details_message += "\n\n"
            
            # Footer
            details_message += "─" * 30 + "\n"
            details_message += "Équipe CCTS"
            
            # Génère le PDF pour le bouton de téléchargement
            pdf_url = None
            try:
                # Essaie plusieurs méthodes pour trouver le rapport
                report = None
                report_names = ['sale.report_saleorder', 'sale.action_report_saleorder']
                
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
                        ('model', '=', 'sale.order')
                    ], limit=1)
                
                if report and report.exists():
                    try:
                        pdf_content, _unused = report._render_qweb_pdf(self.id)
                    except (OSError, ConnectionError) as e:
                        _logger.info("Génération PDF commande %s indisponible (réseau): %s", self.name, str(e))
                        pdf_content = None
                    if pdf_content:
                        # Crée un attachment public pour le PDF
                        attachment = self.env['ir.attachment'].create({
                            'name': f"{self.name}.pdf",
                            'type': 'binary',
                            'datas': base64.b64encode(pdf_content),
                            'res_model': 'sale.order',
                            'res_id': self.id,
                            'public': True,
                        })
                        
                        # Génère l'URL publique de téléchargement
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        _logger.info("URL PDF générée pour la commande %s: %s", self.name, pdf_url)
            except Exception as e:
                _logger.warning("Erreur lors de la génération du PDF pour la commande %s: %s", self.name, str(e))
            
            # Cherche les factures confirmées associées à la commande
            invoice = self._get_confirmed_invoice()
            invoice_pdf_url = None
            
            if invoice:
                # Génère l'URL du PDF de la facture
                invoice_pdf_url = self._get_invoice_pdf_url(invoice)
            
            # Crée les boutons pour le message interactif
            buttons = []
            
            # Bouton "Télécharger PDF commande" si disponible
            if pdf_url:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_download_order_{self.id}",
                        "title": "Télécharger devis"
                    }
                })
            
            # Bouton "Télécharger facture" si disponible (priorité sur le devis si on a les deux)
            if invoice_pdf_url and invoice:
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_download_invoice_{invoice.id}",
                        "title": "Télécharger facture"
                    }
                })
            
            # Envoie le message : interactif si boutons, texte sinon
            if buttons:
                # Message interactif avec bouton(s)
                phone = whatsapp_config._validate_phone_number(phone)
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
