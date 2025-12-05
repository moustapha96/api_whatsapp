# whatsapp_business_api/models/whatsapp_template.py
from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)


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
    
    # Structure des paramètres du template
    parameter_structure = fields.Text(
        string="Structure des paramètres (JSON)",
        help="""Structure JSON décrivant les paramètres requis par le template.
        Exemple pour un template avec 2 paramètres dans le body:
        {
            "body": [
                {"index": 1, "type": "text", "label": "Nom du client"},
                {"index": 2, "type": "text", "label": "Numéro de commande"}
            ],
            "header": [],
            "buttons": []
        }
        
        Exemple avec header image:
        {
            "header": [
                {"index": 1, "type": "image", "label": "Image (URL)"}
            ],
            "body": [
                {"index": 1, "type": "text", "label": "Nom du client"}
            ],
            "buttons": []
        }
        """,
    )
    
    has_parameters = fields.Boolean(
        string="A des paramètres",
        compute="_compute_has_parameters",
        store=False,
    )
    
    @api.depends('parameter_structure')
    def _compute_has_parameters(self):
        """Détermine si le template a des paramètres"""
        for record in self:
            try:
                if record.parameter_structure:
                    structure = json.loads(record.parameter_structure)
                    has_params = bool(
                        structure.get("body") or 
                        structure.get("header") or 
                        structure.get("buttons")
                    )
                    record.has_parameters = has_params
                else:
                    record.has_parameters = False
            except (json.JSONDecodeError, Exception) as e:
                _logger.warning("Erreur lors du parsing de la structure des paramètres pour le template %s: %s", record.name, e)
                record.has_parameters = False
    
    def get_parameter_structure(self):
        """Retourne la structure des paramètres parsée"""
        self.ensure_one()
        if not self.parameter_structure:
            return {}
        try:
            return json.loads(self.parameter_structure)
        except json.JSONDecodeError:
            return {}
