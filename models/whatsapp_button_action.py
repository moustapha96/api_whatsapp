# whatsapp_business_api/models/whatsapp_button_action.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class WhatsappButtonAction(models.Model):
    _name = "whatsapp.button.action"
    _description = "Action à exécuter lors d'un clic sur un bouton WhatsApp"
    _order = "sequence, id"

    name = fields.Char(
        string="Nom de l'action",
        required=True,
        help="Nom descriptif de l'action"
    )

    button_id = fields.Char(
        string="ID du bouton",
        required=True,
        help="ID du bouton tel que défini dans le template WhatsApp (ex: btn_1, btn_yes, etc.)"
    )

    action_type = fields.Selection(
        [
            ("send_message", "Envoyer un message"),
            ("update_contact", "Mettre à jour le contact"),
            ("create_ticket", "Créer un ticket"),
            ("update_status", "Mettre à jour le statut"),
            ("custom_python", "Code Python personnalisé"),
        ],
        string="Type d'action",
        required=True,
        default="send_message",
    )

    message_to_send = fields.Text(
        string="Message à envoyer",
        help="Message à envoyer automatiquement après le clic"
    )

    contact_field_to_update = fields.Char(
        string="Champ contact à mettre à jour",
        help="Nom du champ du contact à mettre à jour (ex: x_whatsapp_status)"
    )

    contact_field_value = fields.Char(
        string="Valeur à définir",
        help="Valeur à définir pour le champ du contact"
    )

    python_code = fields.Text(
        string="Code Python",
        help="Code Python à exécuter. Variables disponibles: env, message, contact, button_id"
    )

    active = fields.Boolean(string="Actif", default=True)

    sequence = fields.Integer(string="Séquence", default=10)

    description = fields.Text(string="Description")

    def execute_action(self, message, contact=None):
        """Exécute l'action définie"""
        self.ensure_one()
        
        _logger.info("Exécution de l'action %s pour le bouton %s", self.name, self.button_id)
        
        try:
            if self.action_type == "send_message":
                return self._action_send_message(message, contact)
            elif self.action_type == "update_contact":
                return self._action_update_contact(message, contact)
            elif self.action_type == "create_ticket":
                return self._action_create_ticket(message, contact)
            elif self.action_type == "update_status":
                return self._action_update_status(message, contact)
            elif self.action_type == "custom_python":
                return self._action_custom_python(message, contact)
        except Exception as e:
            _logger.exception("Erreur lors de l'exécution de l'action %s : %s", self.name, e)
            raise ValidationError(_("Erreur lors de l'exécution de l'action : %s") % str(e))

    def _action_send_message(self, message, contact=None):
        """Envoie un message automatique"""
        if not self.message_to_send:
            return {"success": False, "message": "Aucun message défini"}
        
        config = message.config_id
        if not config:
            config = self.env['whatsapp.config'].get_active_config()
        
        phone = message.phone
        if contact and contact.phone:
            phone = contact.phone
        
        try:
            config.send_text_message(phone, self.message_to_send)
            return {"success": True, "message": "Message envoyé avec succès"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _action_update_contact(self, message, contact=None):
        """Met à jour un champ du contact"""
        if not contact:
            # Cherche le contact par numéro de téléphone
            contact = self.env['res.partner'].search([
                ('phone', '=', message.phone)
            ], limit=1)
        
        if not contact:
            return {"success": False, "message": "Contact non trouvé"}
        
        if not self.contact_field_to_update:
            return {"success": False, "message": "Aucun champ défini"}
        
        try:
            if hasattr(contact, self.contact_field_to_update):
                contact.write({self.contact_field_to_update: self.contact_field_value})
                return {"success": True, "message": f"Champ {self.contact_field_to_update} mis à jour"}
            else:
                return {"success": False, "message": f"Champ {self.contact_field_to_update} n'existe pas"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _action_create_ticket(self, message, contact=None):
        """Crée un ticket (si le module helpdesk est installé)"""
        # Cette action nécessite le module helpdesk
        if 'helpdesk.ticket' not in self.env:
            return {"success": False, "message": "Module helpdesk non installé"}
        
        if not contact:
            contact = self.env['res.partner'].search([
                ('phone', '=', message.phone)
            ], limit=1)
        
        try:
            ticket = self.env['helpdesk.ticket'].create({
                'name': f"Demande WhatsApp - {message.phone}",
                'partner_id': contact.id if contact else False,
                'description': f"Message reçu via WhatsApp:\n{message.content}",
            })
            return {"success": True, "message": f"Ticket créé: {ticket.name}", "ticket_id": ticket.id}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _action_update_status(self, message, contact=None):
        """Met à jour le statut du contact"""
        return self._action_update_contact(message, contact)

    def _action_custom_python(self, message, contact=None):
        """Exécute du code Python personnalisé"""
        if not self.python_code:
            return {"success": False, "message": "Aucun code Python défini"}
        
        try:
            # Variables disponibles dans le contexte
            env = self.env
            button_id = self.button_id
            
            # Exécute le code
            exec(self.python_code, {
                'env': env,
                'message': message,
                'contact': contact,
                'button_id': button_id,
                'self': self,
                '_': _,
            })
            return {"success": True, "message": "Code Python exécuté avec succès"}
        except Exception as e:
            _logger.exception("Erreur dans le code Python personnalisé")
            return {"success": False, "message": str(e)}

