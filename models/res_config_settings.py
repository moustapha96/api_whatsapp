# whatsapp_business_api/models/res_config_settings.py
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_config_id = fields.Many2one(
        "whatsapp.config",
        string="Configuration WhatsApp par défaut",
        config_parameter="whatsapp_business_api.config_id",
    )

    def set_values(self):
        res = super().set_values()
        if self.whatsapp_config_id:
            self.env["ir.config_parameter"].sudo().set_param(
                "whatsapp_business_api.config_id", self.whatsapp_config_id.id
            )
        return res

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        config_id = icp.get_param("whatsapp_business_api.config_id")
        res.update(
            whatsapp_config_id=int(config_id) if config_id else False,
        )
        return res
