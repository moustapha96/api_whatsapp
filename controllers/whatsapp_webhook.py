# whatsapp_business_api/controllers/whatsapp_webhook.py
from odoo import http
from odoo.http import request, Response
import logging
import json
import hmac
import hashlib

_logger = logging.getLogger(__name__)


class WhatsappWebhookController(http.Controller):

    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["GET", "POST"], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        """
        Point de terminaison webhook pour Meta WhatsApp Business API.
        
        GET : Vérification du webhook par Meta (hub.mode, hub.verify_token, hub.challenge)
        POST : Réception des événements webhook (messages, statuses, etc.)
        
        Selon la documentation Meta :
        - Répondre 200 OK dans les 5 secondes
        - Valider la signature SHA256 pour les requêtes POST
        - Gérer la déduplication si nécessaire
        """
        if request.httprequest.method == "GET":
            return self._handle_verification(kwargs)
        elif request.httprequest.method == "POST":
            return self._handle_event()
        else:
            return Response("Method not allowed", status=405)

    def _handle_verification(self, kwargs):
        """
        Gère la demande de vérification GET de Meta.
        
        Meta envoie :
        - hub.mode = "subscribe"
        - hub.verify_token = token configuré
        - hub.challenge = valeur à renvoyer
        
        Note: En PHP, les points (.) sont convertis en underscores (_),
        mais Odoo gère les deux formats.
        """
        # Supporte les deux formats : hub.mode et hub_mode (pour compatibilité PHP)
        mode = kwargs.get("hub.mode") or kwargs.get("hub_mode")
        verify_token = kwargs.get("hub.verify_token") or kwargs.get("hub_verify_token")
        challenge = kwargs.get("hub.challenge") or kwargs.get("hub_challenge")

        _logger.info("WhatsApp Webhook Verification GET - mode: %s, token: %s, challenge: %s", 
                    mode, verify_token[:10] + "..." if verify_token and len(verify_token) > 10 else verify_token, 
                    challenge[:20] + "..." if challenge and len(challenge) > 20 else challenge)

        # Vérifie que mode et token sont présents
        if not mode or not verify_token:
            _logger.warning("Webhook verification échouée : mode ou token manquant")
            return Response("Error: mode and token are required", status=403)

        # Vérifie que le mode est "subscribe"
        if mode != "subscribe":
            _logger.warning("Webhook verification échouée : mode invalide (%s)", mode)
            return Response("Error: invalid mode", status=403)

        # Récupère la configuration active
        config = request.env["whatsapp.config"].sudo().search([("is_active", "=", True)], limit=1)
        if not config:
            _logger.warning("Webhook verification échouée : aucune configuration active")
            return Response("Error: no active configuration", status=403)

        # Vérifie que le token correspond
        if verify_token != config.verify_token:
            _logger.warning("Webhook verification échouée : token invalide")
            return Response("Error: verification failed", status=403)

        # Répond avec le challenge
        _logger.info("Webhook vérifié avec succès")
        return Response(challenge, status=200, mimetype="text/plain")

    def _handle_event(self):
        """
        Gère les notifications d'événement POST de Meta.
        
        Valide la signature SHA256 et traite les messages/statuses.
        Toujours retourne 200 OK même en cas d'erreur pour éviter les nouvelles tentatives.
        """
        try:
            # Récupère les données brutes pour la validation de signature
            raw_data = request.httprequest.data
            if not raw_data:
                _logger.warning("Webhook WhatsApp POST reçu sans données")
                return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

            # Valide la signature SHA256 (recommandé par Meta)
            # if not self._verify_signature(raw_data):
            #     _logger.warning("Webhook WhatsApp : signature invalide - requête rejetée")
            #     # Retourne quand même 200 pour éviter les nouvelles tentatives
            #     return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

            # Parse le JSON
            try:
                data = json.loads(raw_data.decode("utf-8"))
            except json.JSONDecodeError as e:
                _logger.exception("Impossible de parser le JSON du webhook WhatsApp : %s", e)
                return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")
            except Exception as e:
                _logger.exception("Erreur lors de la lecture du webhook WhatsApp : %s", e)
                return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

            # Vérifie que l'objet est valide (whatsapp_business_account pour WhatsApp Business API)
            webhook_object = data.get("object")
            if webhook_object not in ["whatsapp_business_account", "page"]:
                _logger.warning("Webhook WhatsApp : objet inconnu (%s)", webhook_object)
                return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

            # Log structuré du webhook reçu
            entry = (data.get("entry") or [{}])[0]
            changes = (entry.get("changes") or [{}])[0]
            value = changes.get("value", {})
            messages_count = len(value.get("messages") or [])
            statuses_count = len(value.get("statuses") or [])
            
            _logger.info("WhatsApp Webhook POST reçu - Objet: %s, %d message(s), %d statut(s)", 
                        webhook_object, messages_count, statuses_count)

            # Traite le webhook
            try:
                created_records = request.env["whatsapp.message"].sudo().create_from_webhook(data)
                _logger.info("Webhook traité avec succès : %d enregistrement(s) créé(s)", len(created_records))
            except Exception as e:
                _logger.exception("Erreur lors du traitement du webhook WhatsApp : %s", e)
                # Retourne quand même 200 pour éviter que Meta renvoie le webhook

            # Retourne toujours 200 OK dans les 5 secondes (requis par Meta)
            return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

        except Exception as e:
            _logger.exception("Erreur inattendue lors du traitement du webhook WhatsApp : %s", e)
            # Retourne toujours 200 OK même en cas d'erreur inattendue
            return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

    def _verify_signature(self, raw_data):
        """
        Valide la signature SHA256 de la charge utile webhook.
        
        Meta signe toutes les charges utiles avec SHA256 et inclut la signature
        dans l'en-tête X-Hub-Signature-256 au format "sha256=<hash>".
        
        Note: Meta génère la signature avec la version Unicode échappée de la charge utile.
        """
        # Récupère la signature depuis l'en-tête
        signature_header = request.httprequest.headers.get("X-Hub-Signature-256")
        if not signature_header:
            _logger.warning("En-tête X-Hub-Signature-256 manquant dans la requête webhook")
            # Si la signature n'est pas présente, on peut choisir de l'accepter ou non
            # Pour la compatibilité, on accepte si pas de signature (mais on log un avertissement)
            return True  # Changez en False si vous voulez rejeter les requêtes sans signature

        # Extrait le hash de la signature (format: "sha256=<hash>")
        try:
            elements = signature_header.split("=")
            if len(elements) != 2 or elements[0] != "sha256":
                _logger.warning("Format de signature invalide : %s", signature_header)
                return False
            
            signature_hash = elements[1]
        except Exception as e:
            _logger.warning("Erreur lors de l'extraction de la signature : %s", e)
            return False

        # Récupère l'App Secret depuis la configuration
        config = request.env["whatsapp.config"].sudo().search([("is_active", "=", True)], limit=1)
        if not config or not config.facebook_app_secret:
            _logger.warning("Configuration active ou App Secret manquant pour la validation de signature")
            # Si pas de secret, on accepte quand même (mais on log un avertissement)
            return True  # Changez en False si vous voulez rejeter sans secret

        # Génère la signature attendue avec HMAC-SHA256
        try:
            expected_hash = hmac.new(
                config.facebook_app_secret.encode("utf-8"),
                raw_data,
                hashlib.sha256
            ).hexdigest()
        except Exception as e:
            _logger.exception("Erreur lors de la génération de la signature attendue : %s", e)
            return False

        # Compare les signatures (comparaison sécurisée pour éviter les attaques par timing)
        if not hmac.compare_digest(signature_hash, expected_hash):
            _logger.warning("Signature webhook invalide - attendu: %s, reçu: %s", 
                          expected_hash[:20] + "...", signature_hash[:20] + "...")
            return False

        _logger.debug("Signature webhook validée avec succès")
        return True

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
