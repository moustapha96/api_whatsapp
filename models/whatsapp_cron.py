# whatsapp_business_api/models/whatsapp_cron.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WhatsappCron(models.Model):
    _name = "whatsapp.cron"
    _description = "Tâches planifiées WhatsApp"

    @api.model
    def send_unpaid_invoice_reminders(self):
        """Cron job pour envoyer des rappels pour les factures impayées"""
        # Récupère la configuration WhatsApp active
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        
        if not config or not config.auto_send_unpaid_invoices:
            _logger.info("Envoi automatique de factures impayées désactivé ou configuration non trouvée")
            return
        
        # Calcule la date limite (nombre de jours après l'échéance)
        days_after_due = config.unpaid_invoice_days or 7
        date_limit = fields.Date.today() - timedelta(days=days_after_due)
        
        # Cherche les factures impayées dont l'échéance est dépassée depuis X jours
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('amount_residual', '>', 0),
            ('x_whatsapp_unpaid_reminder_sent', '=', False),
            ('invoice_date_due', '<=', date_limit),
        ])
        
        _logger.info("Trouvé %s facture(s) impayée(s) à traiter", len(invoices))
        
        for invoice in invoices:
            try:
                invoice._send_unpaid_invoice_reminder()
            except Exception as e:
                _logger.exception("Erreur lors de l'envoi du rappel pour la facture %s: %s", invoice.name, str(e))

