# whatsapp_business_api/controllers/whatsapp_webhook.py
from odoo import http
from odoo.http import request, Response
import logging
import json

_logger = logging.getLogger(__name__)


class WhatsappWebhookController(http.Controller):

    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["GET","POST"], csrf=False)
    def whatsapp_verify(self, **kwargs):
        """
        Vérification du webhook par Meta (GET).
        Meta envoie : hub.mode, hub.verify_token, hub.challenge
        """
        mode = kwargs.get("hub.mode")
        verify_token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")

        _logger.info("WhatsApp Webhook Verify GET : %s", kwargs)

        if mode == "subscribe" and verify_token:
            config = request.env["whatsapp.config"].sudo().search([("is_active", "=", True)], limit=1)
            if config and verify_token == config.verify_token:
                return Response(challenge, status=200, mimetype="text/plain")

        return Response("Error: verification failed", status=403)

    @http.route("/whatsapp/webhook", type="json", auth="public", methods=["POST"], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        """
        Réception des événements webhook (POST JSON).
        """
        try:
            raw_data = request.httprequest.data
            if not raw_data:
                _logger.warning("Webhook WhatsApp reçu sans données")
                return {"status": "error", "message": "no data"}
            
            data = json.loads(raw_data.decode("utf-8"))
        except json.JSONDecodeError as e:
            _logger.exception("Impossible de parser le JSON du webhook WhatsApp : %s", e)
            return {"status": "error", "message": "invalid json"}
        except Exception as e:
            _logger.exception("Erreur lors de la lecture du webhook WhatsApp : %s", e)
            return {"status": "error", "message": str(e)}

        # Log structuré du webhook reçu
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value", {})
        messages_count = len(value.get("messages") or [])
        statuses_count = len(value.get("statuses") or [])
        
        _logger.info("WhatsApp Webhook POST reçu : %d message(s), %d statut(s)", 
                    messages_count, statuses_count)

        try:
            created_records = request.env["whatsapp.message"].sudo().create_from_webhook(data)
            _logger.info("Webhook traité avec succès : %d enregistrement(s) créé(s)", len(created_records))
        except Exception as e:
            _logger.exception("Erreur lors du traitement du webhook WhatsApp : %s", e)
            # Retourne toujours 200 pour éviter que Meta renvoie le webhook
            return {"status": "error", "message": str(e)}

        return {"status": "ok"}

    @http.route("/whatsapp/test/send", type="json", auth="user", methods=["POST"], csrf=False)
    def whatsapp_test_send(self, phone=None, message=None, **kwargs):
        """
        Endpoint simple pour tester l'envoi depuis un client externe ou via JS.
        """
        if not phone or not message:
            return {"status": "error", "message": "phone et message sont requis"}

        config = request.env["whatsapp.config"].sudo().get_active_config()
        res = config.send_text_message(phone, message)
        return {"status": "ok", "response": res}
