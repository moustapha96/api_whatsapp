# whatsapp_business_api/models/res_partner_whatsapp.py
from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    

    # waiting_password_whatsapp = fields.Boolean(
    #     string="En attente de mot de passe via WhatsApp",
    #     default=False,
    #     help="Indique si le partenaire est en attente de mot de passe via WhatsApp"
    # )
    
    @api.depends()
    def _compute_show_whatsapp_button(self):
        """Calcule si le bouton WhatsApp doit être affiché selon la configuration"""
        config = self.env['whatsapp.config'].get_active_config()
        show_button = config.show_button_in_partner if config else True
        for record in self:
            record.x_show_whatsapp_button = show_button
    
    x_show_whatsapp_button = fields.Boolean(
        string="Afficher bouton WhatsApp",
        compute="_compute_show_whatsapp_button",
        store=False,
        help="Indique si le bouton WhatsApp doit être affiché selon la configuration"
    )

