# whatsapp_business_api/models/sale_order_whatsapp.py
# Ce fichier nécessite le module 'sale' pour fonctionner
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import config
from datetime import datetime
import logging
import json

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    @api.model_create_multi
    def create(self, vals_list):
        """Surcharge la méthode create pour envoyer un message WhatsApp à la création"""
        # Crée les commandes
        orders = super().create(vals_list)
        
        # Envoie un message WhatsApp pour chaque commande créée
        for order in orders:
            try:
                order._send_whatsapp_creation_notification()
            except Exception as e:
                _logger.warning("Erreur lors de l'envoi du message WhatsApp de création pour la commande %s: %s", order.name, str(e))
                # Ne bloque pas la création de la commande si l'envoi échoue
        
        return orders

    def _send_whatsapp_creation_notification(self):
        """Envoie un message WhatsApp pour confirmer la création de la commande"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour le partenaire %s, message WhatsApp non envoyé", self.partner_id.name)
            return
        
        # Vérifie si le message a déjà été envoyé (évite les doublons)
        if self.x_whatsapp_creation_sent:
            return
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            # Ne log pas d'avertissement en mode test
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer le message de création")
            return
        
        try:
            # Prépare un message simple avec le bouton "Voir détail"
            message = f"Bonjour {self.partner_id.name},\n\nVotre commande {self.name} a été créée avec succès.\n\nCliquez sur le bouton ci-dessous pour voir les détails de votre commande."
            
            # Ajoute un bouton "Voir détail" pour afficher les produits
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": f"btn_view_order_details_{self.id}",
                        "title": "Voir détail"
                    }
                }
            ]
            
            # Envoie le message interactif avec le bouton
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
            _logger.exception("Erreur lors de l'envoi du message WhatsApp de création pour la commande %s", self.name)
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
                
                # Envoie un message si l'état change vers 'sale' (confirmé) ou 'done' (terminé)
                if old_state_value != new_state and new_state in ['sale', 'done']:
                    try:
                        record._send_whatsapp_state_notification(new_state, old_state_value)
                    except Exception as e:
                        _logger.warning("Erreur lors de l'envoi du message WhatsApp d'état pour la commande %s: %s", record.name, str(e))
        
        return result

    def _send_whatsapp_state_notification(self, new_state, old_state):
        """Envoie un message WhatsApp avec l'état de la commande, la facture et le nouveau montant"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour le partenaire %s, message WhatsApp d'état non envoyé", self.partner_id.name)
            return
        
        # Vérifie si le message a déjà été envoyé pour cet état (évite les doublons)
        if self.x_whatsapp_state_sent and self.state == new_state:
            return
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            # Ne log pas d'avertissement en mode test
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer le message d'état")
            return
        
        try:
            # Nettoie le numéro de téléphone
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
            
            # Récupère les factures associées (la plus récente)
            invoice = self.env['account.move'].search([
                ('invoice_origin', '=', self.name),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
            ], order='create_date desc', limit=1)
            
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
                # Si pas de facture, utilise le montant de la commande
                message += f"Montant commande : {self.amount_total:.0f} F CFA\n\n"
            
            # Ajoute un message selon l'état
            if new_state == 'sale':
                message += "Merci pour votre confiance."
                
                # Envoie le message texte simple
                result = whatsapp_config.send_text_to_partner(
                    partner_id=self.partner_id.id,
                    message_text=message
                )
            elif new_state == 'done':
                message += "Merci pour votre confiance.\n\n"
                
                # Si une facture existe, envoie un message interactif avec validation
                if invoice:
                    message += "Souhaitez-vous valider cette facture ?"
                    
                    # Prépare les boutons pour validation
                    buttons = [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"btn_validate_invoice_{invoice.id}",
                                "title": "Valider"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"btn_reject_invoice_{invoice.id}",
                                "title": "Rejeter"
                            }
                        }
                    ]
                    
                    # Envoie le message interactif
                    phone = whatsapp_config._validate_phone_number(phone)
                    result = whatsapp_config.send_interactive_message(
                        to_phone=phone,
                        body_text=message,
                        buttons=buttons
                    )
                    
                    # Met à jour la facture pour indiquer qu'un message de validation a été envoyé
                    if result.get('success'):
                        invoice.write({
                            'x_whatsapp_validation_sent': True,
                            'x_whatsapp_validation_sent_date': fields.Datetime.now()
                        })
                else:
                    # Pas de facture, envoie juste le message texte
                    message += "Merci de votre confiance !"
                    result = whatsapp_config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
            else:
                # Autres états, envoie le message texte simple
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
            _logger.exception("Erreur lors de l'envoi du message WhatsApp d'état pour la commande %s", self.name)
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
