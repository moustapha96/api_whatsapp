# whatsapp_business_api/models/whatsapp_interactive_scenario.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class WhatsappInteractiveScenario(models.Model):
    _name = "whatsapp.interactive.scenario"
    _description = "Scénario de message interactif WhatsApp avec réponses automatiques"
    _order = "sequence, name"

    name = fields.Char(
        string="Nom du scénario",
        required=True,
        help="Nom descriptif du scénario (ex: Validation commande, Support client, etc.)"
    )

    active = fields.Boolean(string="Actif", default=True)

    sequence = fields.Integer(string="Séquence", default=10)

    description = fields.Text(string="Description")

    # Message initial
    initial_message = fields.Text(
        string="Message initial",
        required=True,
        help="Message à envoyer avec les boutons interactifs"
    )

    # Boutons (jusqu'à 3 boutons selon l'API WhatsApp)
    button_1_id = fields.Char(
        string="ID Bouton 1",
        help="ID unique du bouton (ex: btn_yes, btn_validate, etc.)"
    )
    button_1_title = fields.Char(
        string="Titre Bouton 1",
        help="Texte affiché sur le bouton (max 20 caractères)"
    )
    button_1_response = fields.Text(
        string="Réponse automatique Bouton 1",
        help="Message à envoyer automatiquement si ce bouton est cliqué"
    )
    button_1_send_interactive = fields.Boolean(
        string="Bouton 1 : Envoyer un message interactif",
        help="Si coché, la réponse sera un message interactif avec boutons"
    )
    button_1_next_scenario_id = fields.Many2one(
        'whatsapp.interactive.scenario',
        string="Bouton 1 : Scénario suivant",
        help="Scénario à exécuter après ce bouton (pour créer des conversations multi-étapes)"
    )

    button_2_id = fields.Char(string="ID Bouton 2")
    button_2_title = fields.Char(string="Titre Bouton 2")
    button_2_response = fields.Text(string="Réponse automatique Bouton 2")
    button_2_send_interactive = fields.Boolean(string="Bouton 2 : Envoyer un message interactif")
    button_2_next_scenario_id = fields.Many2one(
        'whatsapp.interactive.scenario',
        string="Bouton 2 : Scénario suivant"
    )

    button_3_id = fields.Char(string="ID Bouton 3")
    button_3_title = fields.Char(string="Titre Bouton 3")
    button_3_response = fields.Text(string="Réponse automatique Bouton 3")
    button_3_send_interactive = fields.Boolean(string="Bouton 3 : Envoyer un message interactif")
    button_3_next_scenario_id = fields.Many2one(
        'whatsapp.interactive.scenario',
        string="Bouton 3 : Scénario suivant"
    )

    # Configuration
    config_id = fields.Many2one(
        'whatsapp.config',
        string="Configuration WhatsApp",
        help="Configuration à utiliser pour envoyer les messages"
    )

    @api.constrains('button_1_id', 'button_2_id', 'button_3_id')
    def _check_button_ids_unique(self):
        """Vérifie que les IDs de boutons sont uniques"""
        for record in self:
            button_ids = []
            if record.button_1_id:
                if record.button_1_id in button_ids:
                    raise ValidationError(_("Les IDs de boutons doivent être uniques."))
                button_ids.append(record.button_1_id)
            if record.button_2_id:
                if record.button_2_id in button_ids:
                    raise ValidationError(_("Les IDs de boutons doivent être uniques."))
                button_ids.append(record.button_2_id)
            if record.button_3_id:
                if record.button_3_id in button_ids:
                    raise ValidationError(_("Les IDs de boutons doivent être uniques."))
                button_ids.append(record.button_3_id)

    @api.constrains('button_1_title', 'button_2_title', 'button_3_title')
    def _check_button_titles_length(self):
        """Vérifie que les titres de boutons ne dépassent pas 20 caractères"""
        for record in self:
            if record.button_1_title and len(record.button_1_title) > 20:
                raise ValidationError(_("Le titre du bouton 1 ne peut pas dépasser 20 caractères."))
            if record.button_2_title and len(record.button_2_title) > 20:
                raise ValidationError(_("Le titre du bouton 2 ne peut pas dépasser 20 caractères."))
            if record.button_3_title and len(record.button_3_title) > 20:
                raise ValidationError(_("Le titre du bouton 3 ne peut pas dépasser 20 caractères."))

    def get_buttons(self):
        """Retourne la liste des boutons configurés"""
        self.ensure_one()
        buttons = []
        
        if self.button_1_id and self.button_1_title:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": self.button_1_id,
                    "title": self.button_1_title
                }
            })
        if self.button_2_id and self.button_2_title:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": self.button_2_id,
                    "title": self.button_2_title
                }
            })
        if self.button_3_id and self.button_3_title:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": self.button_3_id,
                    "title": self.button_3_title
                }
            })
        
        return buttons

    def send_scenario(self, to_phone, contact_id=None):
        """Envoie le scénario (message initial avec boutons)"""
        self.ensure_one()
        
        if not self.config_id:
            config = self.env['whatsapp.config'].get_active_config()
            if not config:
                raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        else:
            config = self.config_id

        buttons = self.get_buttons()
        if not buttons:
            raise ValidationError(_("Aucun bouton configuré pour ce scénario."))

        result = config.send_interactive_message(
            to_phone=to_phone,
            body_text=self.initial_message,
            buttons=buttons
        )

        # Crée ou met à jour la conversation
        if contact_id:
            contact = self.env['res.partner'].browse(contact_id)
            conversation = self.env['whatsapp.conversation'].search([
                ('phone', '=', to_phone),
                ('contact_id', '=', contact_id)
            ], limit=1)
            
            if not conversation:
                conversation = self.env['whatsapp.conversation'].create({
                    'name': f"{contact.name} - {to_phone}",
                    'phone': to_phone,
                    'contact_id': contact_id,
                    'contact_name': contact.name,
                })
            
            # Lie le message à la conversation
            if result.get('message_record') and conversation:
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = contact_id

        return result

    def handle_button_click(self, button_id, message, contact=None):
        """Gère le clic sur un bouton et envoie la réponse appropriée"""
        self.ensure_one()
        
        config = self.config_id or self.env['whatsapp.config'].get_active_config()
        if not config:
            _logger.warning("Aucune configuration WhatsApp active pour gérer le clic sur le bouton %s", button_id)
            return {"success": False, "message": "Configuration WhatsApp non trouvée"}

        phone = message.phone
        if contact and contact.phone:
            phone = contact.phone

        # Détermine quel bouton a été cliqué et quelle réponse envoyer
        response_text = None
        next_scenario = None
        send_interactive = False

        if button_id == self.button_1_id:
            response_text = self.button_1_response
            send_interactive = self.button_1_send_interactive
            next_scenario = self.button_1_next_scenario_id
        elif button_id == self.button_2_id:
            response_text = self.button_2_response
            send_interactive = self.button_2_send_interactive
            next_scenario = self.button_2_next_scenario_id
        elif button_id == self.button_3_id:
            response_text = self.button_3_response
            send_interactive = self.button_3_send_interactive
            next_scenario = self.button_3_next_scenario_id

        if not response_text and not next_scenario:
            _logger.warning("Aucune réponse configurée pour le bouton %s dans le scénario %s", button_id, self.name)
            return {"success": False, "message": "Aucune réponse configurée pour ce bouton"}

        try:
            # Si un scénario suivant est défini, l'envoyer
            if next_scenario:
                return next_scenario.send_scenario(to_phone=phone, contact_id=contact.id if contact else None)
            
            # Sinon, envoyer la réponse textuelle ou interactive
            if send_interactive and response_text:
                # Pour l'instant, on envoie juste le texte
                # TODO: Permettre de définir des boutons dans la réponse
                result = config.send_text_message(to_phone=phone, body_text=response_text)
            elif response_text:
                result = config.send_text_message(to_phone=phone, body_text=response_text)
            else:
                return {"success": False, "message": "Aucune réponse configurée"}

            return {"success": True, "message": "Réponse envoyée avec succès", "result": result}
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi de la réponse pour le bouton %s : %s", button_id, e)
            return {"success": False, "message": str(e)}

    def send_test_scenario(self):
        """Ouvre un wizard pour envoyer un test du scénario"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Envoyer un test du scénario'),
            'res_model': 'whatsapp.send.scenario.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_scenario_id': self.id,
                'default_config_id': self.config_id.id if self.config_id else False,
            }
        }

