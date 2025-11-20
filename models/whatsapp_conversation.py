# whatsapp_business_api/models/whatsapp_conversation.py
from odoo import models, fields, api


class WhatsappConversation(models.Model):
    _name = "whatsapp.conversation"
    _description = "Conversation WhatsApp"
    _order = "create_date desc"

    name = fields.Char(
        string="Identifiant",
        required=True,
    )
    
    phone = fields.Char("Numéro de téléphone")
    
    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        ondelete="set null",
    )
    contact_name = fields.Char("Nom contact (si disponible)")
    
    message_ids = fields.One2many(
        "whatsapp.message",
        "conversation_id",
        string="Messages",
    )
    
    message_count = fields.Integer(
        string="Nombre de messages",
        compute="_compute_message_count",
    )
    
    @api.depends('message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

