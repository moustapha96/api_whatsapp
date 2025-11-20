# whatsapp_business_api/models/whatsapp_template.py
from odoo import models, fields


class WhatsappTemplate(models.Model):
    _name = "whatsapp.template"
    _description = "Template WhatsApp (référence Odoo)"

    name = fields.Char("Nom interne Odoo", required=True)
    wa_name = fields.Char("Nom template WhatsApp (Meta)", required=True)
    language_code = fields.Char("Langue", default="fr")
    category = fields.Selection(
        [
            ("MARKETING", "Marketing"),
            ("UTILITY", "Utility"),
            ("AUTHENTICATION", "Authentication"),
            ("UNKNOWN", "Inconnu"),
        ],
        string="Catégorie",
        default="UNKNOWN",
    )
    status = fields.Selection(
        [
            ("APPROVED", "Approuvé"),
            ("PENDING", "En attente"),
            ("REJECTED", "Rejeté"),
            ("DISABLED", "Désactivé"),
        ],
        string="Statut",
        default="APPROVED",
    )
    description = fields.Text("Description / Notes")
