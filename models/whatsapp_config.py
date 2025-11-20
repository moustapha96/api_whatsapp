# whatsapp_business_api/models/whatsapp_config.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class WhatsappConfig(models.Model):
    _name = "whatsapp.config"
    _description = "Configuration WhatsApp Business"

    name = fields.Char(
        string="Nom",
        default="WhatsApp Business",
        required=True,
    )

    facebook_app_id = fields.Char(
        "Facebook App ID",
        default="25467073689577747"
    )
    facebook_app_secret = fields.Char(
        "Facebook App Secret",
        default="e0c48b599f8d2dd80933d50cd8caf463"
    )

    whatsapp_business_account_id = fields.Char(
        "WhatsApp Business Account ID",
        default="1231205165506123"
    )
    phone_number_id = fields.Char(
        "Phone Number ID",
        default="881068025087844",
        required=True
    )
    access_token = fields.Char(
        "Access Token (permanent)",
        default="EAFp6Kyi8aRMBP8QK49Eh8nbgA1IKnOwEzRhqS0HoZBiSQZCo0JOiT1SFB0TdRCZBGw3Xg78QdptUry8ywZCZC7LFEBdzesbgStIz7JnyLaHZA9ZATwyRriY42T4j3JXVzPA22I4FL3AWbclgEiGyvmoaj5eGeZARX89D5BRknDo2xJNYZAf3a8a8czbo2UtdXXgZDZD",
        required=True
    )

    verify_token = fields.Char(
        string="Verify Token Webhook",
        help="Token utilisé par Meta pour vérifier le webhook",
        default="ccbmshop",
        required=True,
    )

    webhook_url = fields.Char(
        string="URL Webhook",
        help="URL publique exposée à Meta (ex: https://ton-domaine.com/whatsapp/webhook)",
        default="https://orbitcity-dev-api-whatsapp-25642789.dev.odoo.com/whatsapp/webhook/1"
    )

    is_active = fields.Boolean(string="Actif", default=True)

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    @api.model
    def send_text_to_partner(self, partner_id, message_text, preview_url=False, config_id=None):
        """
        Fonction utilitaire pour envoyer un message texte WhatsApp à un partenaire.
        Cette fonction peut être appelée depuis n'importe quel module.
        
        Exemple d'utilisation depuis un autre module :
        ```python
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if config:
            result = config.send_text_to_partner(
                partner_id=self.partner_id.id,
                message_text="Bonjour, votre commande est prête !"
            )
        ```
        
        Args:
            partner_id: ID du partenaire (res.partner) ou objet partenaire
            message_text: Texte du message à envoyer
            preview_url: Si True, active la prévisualisation des liens (défaut: False)
            config_id: ID de la configuration WhatsApp à utiliser (optionnel, utilise la config active par défaut)
        
        Returns:
            dict: Résultat avec 'success', 'message_id', 'message_record', 'error'
        
        Raises:
            ValidationError: Si le partenaire n'a pas de numéro de téléphone ou si l'envoi échoue
        """
        # Récupère le partenaire
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        if not partner.exists():
            raise ValidationError(_("Partenaire introuvable."))
        
        # Récupère le numéro de téléphone
        phone = partner.phone or partner.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % partner.name)
        
        # Récupère la configuration
        if config_id:
            config = self.browse(config_id)
        else:
            config = self.search([('is_active', '=', True)], limit=1)
        
        if not config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        # Valide et nettoie le numéro
        phone = config._validate_phone_number(phone)
        
        # Envoie le message
        result = config.send_text_message(
            to_phone=phone,
            body_text=message_text,
            preview_url=preview_url
        )
        
        # Récupère le message créé
        message_record = None
        if isinstance(result, dict) and result.get('message_record'):
            message_record = result['message_record']
        else:
            message_record = self.env['whatsapp.message'].search([
                ('config_id', '=', config.id),
                ('phone', '=', phone),
                ('content', '=', message_text),
                ('direction', '=', 'out')
            ], order='create_date desc', limit=1)
        
        # Crée ou met à jour la conversation
        conversation = self.env['whatsapp.conversation'].search([
            ('phone', '=', phone),
            ('contact_id', '=', partner.id)
        ], limit=1)
        
        if not conversation:
            conversation = self.env['whatsapp.conversation'].create({
                'name': f"{partner.name} - {phone}",
                'phone': phone,
                'contact_id': partner.id,
                'contact_name': partner.name,
            })
        
        # Lie le message à la conversation et au partenaire
        if message_record:
            message_record.conversation_id = conversation.id
            message_record.contact_id = partner.id
        
        return result

    def get_active_config(self):
        config = self.search([("is_active", "=", True)], limit=1)
        if not config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        return config

    def _get_headers(self):
        self.ensure_one()
        if not self.access_token:
            raise ValidationError(_("Le token d'accès WhatsApp n'est pas configuré."))
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _send_whatsapp_request(self, payload):
        """
        Envoi brut vers l'API WhatsApp Cloud.
        payload : dict Python (sera json.dumps)
        Retourne: (data, message_id, raw_response, error_message)
        """
        self.ensure_one()
        url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
        headers = self._get_headers()

        _logger.info("Envoi requête WhatsApp : %s", payload)
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            _logger.info("Réponse WhatsApp : %s - %s", response.status_code, response.text)
            
            # Parse la réponse
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {"error": {"message": "Réponse invalide de l'API"}}
            
            # Vérifie les erreurs dans la réponse
            if response.status_code != 200 or data.get("error"):
                error_info = data.get("error", {})
                error_message = error_info.get("message", f"Erreur HTTP {response.status_code}")
                error_type = error_info.get("type", "Unknown")
                error_code = error_info.get("code", response.status_code)
                error_subcode = error_info.get("error_subcode")
                
                # Messages d'erreur spécifiques selon le code
                if error_code == 131047:
                    error_message = "Le numéro de téléphone n'est pas un numéro WhatsApp valide ou n'est pas inscrit sur WhatsApp"
                elif error_code == 131026:
                    error_message = "Fenêtre de 24h expirée : Vous ne pouvez envoyer des messages texte que dans les 24h après le dernier message du client. Utilisez un template WhatsApp."
                elif error_code == 131031:
                    error_message = "Le numéro de téléphone n'est pas autorisé. Vérifiez qu'il est dans votre liste de numéros test (mode développement)"
                elif error_code == 190:
                    error_message = "Token d'accès invalide ou expiré. Vérifiez votre access_token"
                elif error_code == 100:
                    error_message = "Paramètres invalides. Vérifiez le format du numéro de téléphone"
                
                full_error = f"[{error_type}] {error_message} (Code: {error_code}"
                if error_subcode:
                    full_error += f", SubCode: {error_subcode}"
                full_error += ")"
                
                _logger.error("Erreur API WhatsApp : %s - Réponse complète: %s", full_error, response.text)
                return None, None, response.text, full_error
            
            # Extrait le message_id
            message_id = None
            try:
                message_id = data.get("messages", [{}])[0].get("id")
            except Exception:
                pass

            return data, message_id, response.text, None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erreur de connexion : {str(e)}"
            _logger.exception("Erreur en envoyant une requête WhatsApp : %s", e)
            return None, None, str(e), error_msg
        except Exception as e:
            error_msg = f"Erreur inattendue : {str(e)}"
            _logger.exception("Erreur inattendue lors de l'envoi WhatsApp : %s", e)
            return None, None, str(e), error_msg

    # ---------------------------------------------------------------------
    # Envoi de messages : texte, média, localisation, template
    # ---------------------------------------------------------------------

    def _validate_phone_number(self, phone):
        """Valide et nettoie le numéro de téléphone"""
        if not phone:
            raise ValidationError(_("Numéro de téléphone manquant."))
        
        # Nettoie le numéro
        phone = phone.replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '')
        
        # Vérifie le format
        if not phone.startswith('+'):
            # Si commence par 0, remplace par l'indicatif du pays (à adapter)
            if phone.startswith('0'):
                phone = '+33' + phone[1:]  # Exemple pour la France
            else:
                phone = '+' + phone
        
        # Vérifie que c'est un numéro valide (au moins 10 chiffres après le +)
        digits_only = phone[1:].replace('+', '')
        if not digits_only.isdigit() or len(digits_only) < 10:
            raise ValidationError(_("Format de numéro de téléphone invalide. Format attendu: +33612345678"))
        
        return phone

    def send_text_message(self, to_phone, body_text, preview_url=False):
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        
        # Valide et nettoie le numéro
        to_phone = self._validate_phone_number(to_phone)
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {
                "body": body_text,
                "preview_url": preview_url,
            },
        }
        data, message_id, raw_response, error_message = self._send_whatsapp_request(payload)

        # Détermine le statut et le message d'erreur
        if error_message:
            status = "error"
            response_summary = error_message
        elif message_id:
            status = "sent"
            response_summary = f"Message envoyé avec succès (ID: {message_id})"
        else:
            status = "error"
            response_summary = "Erreur : Aucun ID de message retourné"

        message_record = self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": body_text,
            "message_type": "text",
            "status": status,
            "wa_status": error_message or "sent",
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response or "",
        })
        
        # Retourne le résultat avec le message créé
        result = {
            "success": not bool(error_message),
            "message_id": message_id,
            "message_record": message_record,
            "error": error_message
        }
        
        # Si erreur, lève une exception pour que le wizard puisse la gérer
        if error_message:
            raise ValidationError(_("Erreur lors de l'envoi du message : %s") % error_message)
        
        return data if data else result

    def send_interactive_message(self, to_phone, body_text, buttons=None):
        """
        Envoie un message avec boutons interactifs.
        
        Args:
            to_phone: Numéro de téléphone destinataire
            body_text: Texte du message
            buttons: Liste de dictionnaires avec les boutons
                Exemple:
                [
                    {"type": "reply", "reply": {"id": "btn_yes", "title": "Oui"}},
                    {"type": "reply", "reply": {"id": "btn_no", "title": "Non"}},
                ]
        """
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        
        if not buttons:
            buttons = []
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body_text
                },
                "action": {
                    "buttons": buttons
                }
            }
        }
        
        data, message_id, raw_response, error_message = self._send_whatsapp_request(payload)

        # Détermine le statut
        if error_message:
            status = "error"
        elif message_id:
            status = "sent"
        else:
            status = "error"

        message_record = self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": body_text,
            "message_type": "interactive",
            "status": status,
            "wa_status": error_message or "sent",
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response or "",
        })
        
        if error_message:
            raise ValidationError(_("Erreur lors de l'envoi du message interactif : %s") % error_message)
        
        return {
            "success": True if message_id else False,
            "message_id": message_id,
            "message_record": message_record,
            "error": error_message
        }

    def send_image_message(self, to_phone, image_id=None, image_link=None, caption=None):
        """
        image_id : ID média uploadé chez Meta
        image_link : URL publique d'une image (si pas d'ID)
        """
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        if not image_id and not image_link:
            raise ValidationError(_("Vous devez fournir soit un image_id, soit un image_link."))

        image_payload = {}
        if image_id:
            image_payload["id"] = image_id
        if image_link:
            image_payload["link"] = image_link
        if caption:
            image_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "image",
            "image": image_payload,
        }
        data, message_id, raw_response = self._send_whatsapp_request(payload)

        self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": caption or "",
            "message_type": "image",
            "status": "sent",
            "media_id": image_id,
            "media_url": image_link,
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response,
        })
        return data

    def send_document_message(self, to_phone, document_id=None, document_link=None,
                              filename=None, caption=None):
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        if not document_id and not document_link:
            raise ValidationError(_("Vous devez fournir soit un document_id, soit un document_link."))

        doc_payload = {}
        if document_id:
            doc_payload["id"] = document_id
        if document_link:
            doc_payload["link"] = document_link
        if filename:
            doc_payload["filename"] = filename
        if caption:
            doc_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "document",
            "document": doc_payload,
        }
        data, message_id, raw_response = self._send_whatsapp_request(payload)

        self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": caption or "",
            "message_type": "document",
            "status": "sent",
            "media_id": document_id,
            "media_url": document_link,
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response,
        })
        return data

    def send_audio_message(self, to_phone, audio_id=None, audio_link=None):
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        if not audio_id and not audio_link:
            raise ValidationError(_("Vous devez fournir soit un audio_id, soit un audio_link."))

        audio_payload = {}
        if audio_id:
            audio_payload["id"] = audio_id
        if audio_link:
            audio_payload["link"] = audio_link

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "audio",
            "audio": audio_payload,
        }
        data, message_id, raw_response = self._send_whatsapp_request(payload)

        self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "message_type": "audio",
            "status": "sent",
            "media_id": audio_id,
            "media_url": audio_link,
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response,
        })
        return data

    def send_video_message(self, to_phone, video_id=None, video_link=None, caption=None):
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        if not video_id and not video_link:
            raise ValidationError(_("Vous devez fournir soit un video_id, soit un video_link."))

        video_payload = {}
        if video_id:
            video_payload["id"] = video_id
        if video_link:
            video_payload["link"] = video_link
        if caption:
            video_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "video",
            "video": video_payload,
        }
        data, message_id, raw_response = self._send_whatsapp_request(payload)

        self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": caption or "",
            "message_type": "video",
            "status": "sent",
            "media_id": video_id,
            "media_url": video_link,
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response,
        })
        return data

    def send_location_message(self, to_phone, latitude, longitude,
                              name=None, address=None):
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        if latitude is None or longitude is None:
            raise ValidationError(_("Latitude et longitude sont requis pour un message de localisation."))

        loc_payload = {
            "latitude": str(latitude),
            "longitude": str(longitude),
        }
        if name:
            loc_payload["name"] = name
        if address:
            loc_payload["address"] = address

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "location",
            "location": loc_payload,
        }
        data, message_id, raw_response = self._send_whatsapp_request(payload)

        self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": f"{latitude}, {longitude}",
            "message_type": "location",
            "status": "sent",
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response,
        })
        return data

    def send_template_message(
        self,
        to_phone,
        template_name,
        language_code="fr",
        components=None,
    ):
        """
        Envoie un message template WhatsApp.
        
        IMPORTANT : Le template doit être créé et approuvé dans Meta Business Suite avant utilisation.
        
        Args:
            to_phone: Numéro de téléphone destinataire (format international)
            template_name: Nom du template tel que défini dans Meta (ex: "simple_text_message")
            language_code: Code langue ('fr', 'fr_FR', 'en', etc.)
            components: Liste de composants pour les paramètres (body, header, buttons)
        
        Exemples de components:
        
        # Template simple (sans paramètres)
        components = None
        
        # Template avec paramètres dans le body
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Jean Dupont"},
                    {"type": "text", "text": "CMD-2024-001"},
                    {"type": "text", "text": "150.00"}
                ]
            }
        ]
        
        # Template avec header image et body paramètres
        components = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "link": "https://example.com/invoice.jpg"
                        }
                    }
                ]
            },
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Jean Dupont"},
                    {"type": "text", "text": "150.00"}
                ]
            }
        ]
        
        # Template avec header document
        components = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "document",
                        "document": {
                            "link": "https://example.com/invoice.pdf"
                        }
                    }
                ]
            },
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Votre facture"}
                ]
            }
        ]
        
        # Template avec boutons (les boutons sont définis dans le template Meta)
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Jean Dupont"}
                ]
            }
        ]
        """
        if not to_phone:
            raise ValidationError(_("Numéro de téléphone destinataire manquant."))
        if not template_name:
            raise ValidationError(_("Nom du template WhatsApp manquant."))

        template = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": template,
        }
        data, message_id, raw_response, error_message = self._send_whatsapp_request(payload)

        # Détermine le statut
        if error_message:
            status = "error"
        elif message_id:
            status = "sent"
        else:
            status = "error"

        message_record = self.env["whatsapp.message"].create({
            "config_id": self.id,
            "direction": "out",
            "wa_message_id": message_id,
            "phone": to_phone,
            "content": f"Template: {template_name}",
            "message_type": "template",
            "status": status,
            "wa_status": error_message or "sent",
            "template_name": template_name,
            "template_language": language_code,
            "template_components": json.dumps(components or []),
            "raw_payload": json.dumps(payload),
            "raw_response": raw_response or "",
        })
        
        # Retourne le résultat avec le message créé
        result = {
            "success": not bool(error_message),
            "message_id": message_id,
            "message_record": message_record,
            "error": error_message
        }
        
        # Si erreur, lève une exception pour que le wizard puisse la gérer
        if error_message:
            raise ValidationError(_("Erreur lors de l'envoi du template : %s") % error_message)
        
        return data if data else result

    # ---------------------------------------------------------------------
    # Actions de configuration
    # ---------------------------------------------------------------------

    def action_verify_parameters(self):
        """Vérifie les paramètres de configuration en testant la connexion"""
        self.ensure_one()
        try:
            # Test de connexion en récupérant les informations du compte
            url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Les paramètres sont corrects ! Connexion réussie.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except requests.exceptions.RequestException as e:
            raise ValidationError(_("Erreur de connexion : %s") % str(e))
        except Exception as e:
            raise ValidationError(_("Erreur lors de la vérification : %s") % str(e))

    def action_sync_templates(self):
        """Synchronise les templates depuis l'API Meta"""
        self.ensure_one()
        try:
            # Récupère les templates depuis l'API Meta
            url = f"https://graph.facebook.com/v21.0/{self.whatsapp_business_account_id}/message_templates"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            templates = data.get('data', [])
            created_count = 0
            updated_count = 0
            
            for template_data in templates:
                wa_name = template_data.get('name', '')
                status = template_data.get('status', 'UNKNOWN')
                category = template_data.get('category', 'UNKNOWN')
                
                # Extrait le code langue
                language = template_data.get('language', {})
                if isinstance(language, dict):
                    language_code = language.get('code', 'fr')
                else:
                    language_code = str(language) if language else 'fr'
                
                # Cherche le template existant
                template = self.env['whatsapp.template'].search([
                    ('wa_name', '=', wa_name)
                ], limit=1)
                
                template_vals = {
                    'wa_name': wa_name,
                    'status': status,
                    'category': category,
                    'language_code': language_code,
                }
                
                if template:
                    template.write(template_vals)
                    updated_count += 1
                else:
                    template_vals['name'] = wa_name
                    self.env['whatsapp.template'].create(template_vals)
                    created_count += 1
            
            message = _('Synchronisation terminée : %d créés, %d mis à jour') % (created_count, updated_count)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except requests.exceptions.RequestException as e:
            raise ValidationError(_("Erreur lors de la synchronisation des templates : %s") % str(e))
        except Exception as e:
            raise ValidationError(_("Erreur lors de la synchronisation : %s") % str(e))

    def action_fetch_sent_messages(self):
        """Récupère les messages envoyés depuis l'API"""
        self.ensure_one()
        try:
            # Récupère les messages envoyés depuis la base de données locale
            sent_messages = self.env['whatsapp.message'].search([
                ('config_id', '=', self.id),
                ('direction', '=', 'out'),
                ('status', 'in', ['sent', 'delivered', 'read'])
            ], limit=100, order='create_date desc')
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Messages envoyés'),
                'res_model': 'whatsapp.message',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', sent_messages.ids)],
                'target': 'current',
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors de la récupération des messages : %s") % str(e))

    def action_fetch_failed_messages(self):
        """Récupère les messages non envoyés (en erreur)"""
        self.ensure_one()
        try:
            # Récupère les messages en erreur
            failed_messages = self.env['whatsapp.message'].search([
                ('config_id', '=', self.id),
                ('direction', '=', 'out'),
                ('status', '=', 'error')
            ], limit=100, order='create_date desc')
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Messages non envoyés'),
                'res_model': 'whatsapp.message',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', failed_messages.ids)],
                'target': 'current',
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors de la récupération des messages : %s") % str(e))

    def action_fetch_message_statuses(self):
        """Récupère les statuts des messages depuis l'API Meta"""
        self.ensure_one()
        try:
            # Récupère les messages avec statut en attente de mise à jour
            messages_to_check = self.env['whatsapp.message'].search([
                ('config_id', '=', self.id),
                ('direction', '=', 'out'),
                ('wa_message_id', '!=', False),
                ('status', 'in', ['sent', 'delivered'])
            ], limit=50)
            
            updated_count = 0
            for message in messages_to_check:
                try:
                    # Vérifie le statut du message via l'API
                    url = f"https://graph.facebook.com/v21.0/{message.wa_message_id}"
                    headers = self._get_headers()
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        # Met à jour le statut si nécessaire
                        # Note: L'API Meta ne retourne pas directement le statut, 
                        # mais on peut utiliser le webhook pour cela
                        updated_count += 1
                except Exception:
                    continue
            
            message = _('Vérification terminée : %d messages vérifiés') % updated_count
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors de la vérification des statuts : %s") % str(e))

    def action_fetch_incoming_messages(self):
        """Récupère les messages entrants"""
        self.ensure_one()
        try:
            # Récupère les messages entrants
            incoming_messages = self.env['whatsapp.message'].search([
                ('config_id', '=', self.id),
                ('direction', '=', 'in')
            ], limit=100, order='create_date desc')
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Messages entrants'),
                'res_model': 'whatsapp.message',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', incoming_messages.ids)],
                'target': 'current',
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors de la récupération des messages : %s") % str(e))

    def action_diagnose_message_delivery(self):
        """Diagnostique pourquoi les messages ne sont pas reçus"""
        self.ensure_one()
        try:
            # Récupère les messages envoyés récemment qui n'ont pas été lus
            recent_messages = self.env['whatsapp.message'].search([
                ('config_id', '=', self.id),
                ('direction', '=', 'out'),
                ('status', '=', 'sent'),
                ('create_date', '>=', fields.Datetime.now() - timedelta(days=1))
            ], limit=10, order='create_date desc')
            
            issues = []
            for msg in recent_messages:
                # Vérifie le format du numéro
                if not msg.phone or not msg.phone.startswith('+'):
                    issues.append(f"Message {msg.id}: Numéro invalide ({msg.phone})")
                
                # Vérifie si c'est un message texte (sujet à la fenêtre de 24h)
                if msg.message_type == 'text':
                    # Vérifie s'il y a eu un message entrant récent
                    last_incoming = self.env['whatsapp.message'].search([
                        ('phone', '=', msg.phone),
                        ('direction', '=', 'in'),
                        ('create_date', '<', msg.create_date)
                    ], order='create_date desc', limit=1)
                    
                    if last_incoming:
                        time_diff = msg.create_date - last_incoming.create_date
                        if time_diff.total_seconds() > 86400:  # 24 heures
                            issues.append(f"Message {msg.id}: Fenêtre de 24h expirée (dernier message client: {time_diff})")
                    else:
                        issues.append(f"Message {msg.id}: Aucun message entrant précédent - Utilisez un template WhatsApp")
                
                # Vérifie la réponse de l'API
                if msg.raw_response:
                    try:
                        response_data = json.loads(msg.raw_response)
                        if response_data.get('error'):
                            error = response_data['error']
                            issues.append(f"Message {msg.id}: Erreur API - {error.get('message')} (Code: {error.get('code')})")
                    except:
                        pass
            
            if issues:
                message = _("Problèmes détectés :\n\n") + "\n".join(issues[:10])
            else:
                message = _("Aucun problème détecté dans les messages récents.")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Diagnostic'),
                    'message': message,
                    'type': 'info' if issues else 'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors du diagnostic : %s") % str(e))
