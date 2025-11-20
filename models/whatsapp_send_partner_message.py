# whatsapp_business_api/models/whatsapp_send_partner_message.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class WhatsappSendPartnerMessage(models.TransientModel):
    _name = "whatsapp.send.partner.message"
    _description = "Wizard pour envoyer un message WhatsApp à un partenaire"

    config_id = fields.Many2one(
        "whatsapp.config",
        string="Configuration WhatsApp",
        required=True,
        help="Configuration WhatsApp à utiliser pour l'envoi",
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Partenaire",
        required=True,
        help="Partenaire à qui envoyer le message",
    )

    phone = fields.Char(
        string="Numéro de téléphone",
        required=True,
        help="Numéro au format international (ex: +33612345678)",
    )

    message = fields.Text(
        string="Message",
        required=True,
        help="Contenu du message à envoyer",
    )

    preview_url = fields.Boolean(
        string="Aperçu des liens",
        default=False,
        help="Si activé, les liens dans le message seront prévisualisés",
    )

    @api.model
    def default_get(self, fields_list):
        """Charge la configuration active par défaut et le partenaire depuis le contexte"""
        res = super().default_get(fields_list)
        
        # Charge la configuration active
        if 'config_id' in fields_list:
            config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
            if config:
                res['config_id'] = config.id
        
        # Charge le partenaire depuis le contexte (si appelé depuis un bouton)
        if 'partner_id' in fields_list and 'default_partner_id' in self.env.context:
            partner_id = self.env.context.get('default_partner_id')
            if partner_id:
                res['partner_id'] = partner_id
        
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Remplit automatiquement le numéro de téléphone depuis le partenaire"""
        if self.partner_id:
            phone = self.partner_id.phone or self.partner_id.mobile
            if phone:
                # Nettoie le numéro
                phone = phone.replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '')
                if not phone.startswith('+'):
                    phone = '+' + phone.lstrip('+')
                self.phone = phone
            else:
                raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)

    def action_send_message(self):
        """Envoie le message WhatsApp au partenaire"""
        self.ensure_one()
        
        if not self.config_id:
            raise ValidationError(_("Veuillez sélectionner une configuration WhatsApp."))
        
        if not self.partner_id:
            raise ValidationError(_("Veuillez sélectionner un partenaire."))
        
        if not self.phone:
            raise ValidationError(_("Veuillez saisir un numéro de téléphone."))
        
        if not self.message:
            raise ValidationError(_("Veuillez saisir un message."))

        # Valide et nettoie le numéro de téléphone
        phone = self.config_id._validate_phone_number(self.phone)

        message_record = None
        try:
            # Envoie le message
            result = self.config_id.send_text_message(
                to_phone=phone,
                body_text=self.message,
                preview_url=self.preview_url
            )
            
            # Récupère le message créé depuis le résultat
            if isinstance(result, dict) and result.get('message_record'):
                message_record = result['message_record']
            else:
                message_record = self.env['whatsapp.message'].search([
                    ('config_id', '=', self.config_id.id),
                    ('phone', '=', phone),
                    ('content', '=', self.message),
                    ('direction', '=', 'out')
                ], order='create_date desc', limit=1)
            
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
            if message_record and conversation:
                message_record.conversation_id = conversation.id
                message_record.contact_id = self.partner_id.id
            
            # Retourne la vue du message pour voir le résultat
            if message_record:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Message WhatsApp'),
                    'res_model': 'whatsapp.message',
                    'res_id': message_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Succès'),
                        'message': _('Message envoyé avec succès à %s') % self.partner_id.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
                
        except ValidationError as e:
            # Affiche l'erreur
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi du message WhatsApp")
            raise ValidationError(_("Erreur lors de l'envoi du message : %s") % str(e))

