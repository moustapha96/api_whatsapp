# whatsapp_business_api/models/whatsapp_message.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class WhatsappMessage(models.Model):
    _name = "whatsapp.message"
    _description = "Journal des messages WhatsApp"
    _order = "create_date desc"

    direction = fields.Selection(
        [
            ("in", "Entrant"),
            ("out", "Sortant"),
        ],
        string="Direction",
        required=True,
    )

    config_id = fields.Many2one(
        "whatsapp.config",
        string="Configuration",
        ondelete="set null",
    )

    conversation_id = fields.Many2one(
        "whatsapp.conversation",
        string="Conversation",
        ondelete="set null",
    )

    wa_message_id = fields.Char("ID Message WhatsApp")
    wa_conversation_id = fields.Char("ID Conversation")
    wa_status = fields.Char("Statut WhatsApp brut")

    phone = fields.Char("Numéro de téléphone")
    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        ondelete="set null",
    )
    contact_name = fields.Char("Nom contact (si disponible)")

    content = fields.Text("Contenu du message")
    message_type = fields.Selection(
        [
            ("text", "Texte"),
            ("image", "Image"),
            ("audio", "Audio"),
            ("video", "Vidéo"),
            ("document", "Document"),
            ("sticker", "Sticker"),
            ("location", "Localisation"),
            ("contacts", "Contacts"),
            ("interactive", "Interactif / Boutons"),
            ("template", "Template"),
            ("unknown", "Inconnu"),
        ],
        string="Type de message",
        default="text",
    )

    status = fields.Selection(
        [
            ("received", "Reçu"),
            ("sent", "Envoyé"),
            ("delivered", "Délivré"),
            ("read", "Lu"),
            ("error", "Erreur"),
        ],
        string="Statut interne",
        default="received",
    )

    # Infos média
    media_id = fields.Char("ID Média (Meta)")
    media_url = fields.Char("URL Média (si lien)")
    media_mime_type = fields.Char("Type MIME")
    caption = fields.Char("Légende média")

    # Infos template
    template_name = fields.Char("Nom du template")
    template_language = fields.Char("Langue du template")
    template_components = fields.Text("Components template (JSON)")

    raw_payload = fields.Text("Payload brut")
    raw_response = fields.Text("Réponse brute API")
    
    error_help = fields.Text(
        string="Aide sur l'erreur",
        compute="_compute_error_help",
        help="Message d'aide pour résoudre les problèmes d'envoi"
    )
    
    def action_reply_message(self):
        """
        Ouvre le wizard pour répondre à ce message.
        """
        self.ensure_one()
        
        if self.direction != 'in':
            raise ValidationError(_("Vous ne pouvez répondre qu'aux messages entrants."))
        
        if not self.phone:
            raise ValidationError(_("Aucun numéro de téléphone associé à ce message."))
        
        # Récupère la configuration active
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        # Ouvre le wizard d'envoi de message avec les valeurs pré-remplies
        return {
            'type': 'ir.actions.act_window',
            'name': _('Répondre au message'),
            'res_model': 'whatsapp.send.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_id': config.id,
                'default_phone': self.phone,
                'default_contact_id': self.contact_id.id if self.contact_id else False,
                'default_message': '',  # L'utilisateur peut saisir sa réponse
            }
        }
    
    @api.depends('status', 'wa_status', 'raw_response', 'message_type', 'phone')
    def _compute_error_help(self):
        """Calcule un message d'aide selon le type d'erreur"""
        for rec in self:
            help_text = ""
            
            if rec.status == 'error' or (rec.wa_status and 'error' in rec.wa_status.lower()):
                # Analyse la réponse pour donner des conseils
                if rec.raw_response:
                    try:
                        response_data = json.loads(rec.raw_response)
                        error = response_data.get('error', {})
                        error_code = error.get('code')
                        
                        if error_code == 131026:
                            help_text = "⚠️ FENÊTRE DE 24H EXPIRÉE\n\nVous ne pouvez envoyer des messages texte que dans les 24h après le dernier message du client.\n\n✅ SOLUTION : Utilisez un template WhatsApp approuvé pour envoyer des messages hors de la fenêtre de 24h."
                        elif error_code == 131047:
                            help_text = "⚠️ NUMÉRO INVALIDE\n\nLe numéro n'est pas un numéro WhatsApp valide ou n'est pas inscrit sur WhatsApp.\n\n✅ SOLUTION : Vérifiez que le numéro est correct et que la personne a WhatsApp installé."
                        elif error_code == 131031:
                            help_text = "⚠️ NUMÉRO NON AUTORISÉ\n\nEn mode développement, seuls les numéros de test sont autorisés.\n\n✅ SOLUTION : Ajoutez ce numéro dans votre liste de numéros test dans Meta Business Suite."
                        elif error_code == 190:
                            help_text = "⚠️ TOKEN INVALIDE\n\nLe token d'accès est invalide ou expiré.\n\n✅ SOLUTION : Régénérez votre access_token dans Meta Business Suite."
                        elif error_code == 100:
                            help_text = "⚠️ FORMAT INVALIDE\n\nLe format du numéro de téléphone est invalide.\n\n✅ SOLUTION : Utilisez le format international : +33612345678"
                        else:
                            help_text = f"⚠️ ERREUR API\n\nCode: {error_code}\nMessage: {error.get('message', 'Erreur inconnue')}\n\n✅ Vérifiez les logs pour plus de détails."
                    except:
                        if '131026' in rec.raw_response or '24' in rec.raw_response:
                            help_text = "⚠️ FENÊTRE DE 24H EXPIRÉE\n\n✅ SOLUTION : Utilisez un template WhatsApp."
                        elif '131047' in rec.raw_response:
                            help_text = "⚠️ NUMÉRO INVALIDE\n\n✅ SOLUTION : Vérifiez que le numéro est correct et que la personne a WhatsApp."
                        else:
                            help_text = "⚠️ ERREUR D'ENVOI\n\n✅ Vérifiez la réponse API dans l'onglet 'Réponse API' pour plus de détails."
            
            elif rec.status == 'sent' and rec.message_type == 'text':
                # Vérifie si c'est un message texte qui pourrait ne pas être reçu
                help_text = "ℹ️ MESSAGE TEXTE ENVOYÉ\n\n⚠️ ATTENTION : Les messages texte ne peuvent être envoyés que dans les 24h après le dernier message du client.\n\n✅ Si le message n'arrive pas, utilisez un template WhatsApp approuvé."
            
            rec.error_help = help_text

    # ------------------------------------------------------------------
    # Création à partir du webhook
    # ------------------------------------------------------------------
    def _normalize_phone(self, phone):
        """Normalise un numéro de téléphone pour la recherche"""
        if not phone:
            return None
        # Nettoie le numéro
        phone_clean = phone.replace(' ', '').replace('-', '').replace('.', '').replace('(', '').replace(')', '')
        # Ajoute le + si absent
        if phone_clean and not phone_clean.startswith('+'):
            phone_clean = '+' + phone_clean.lstrip('+')
        return phone_clean

    def _find_or_create_contact(self, phone, contact_name=None):
        """Trouve ou crée un contact à partir d'un numéro de téléphone"""
        if not phone:
            return None
        
        phone_clean = self._normalize_phone(phone)
        if not phone_clean:
            return None
        
        # Cherche le contact par numéro (phone ou mobile)
        contact = self.env['res.partner'].search([
            '|',
            ('phone', 'ilike', phone_clean),
            ('mobile', 'ilike', phone_clean)
        ], limit=1)
        
        # Si pas trouvé, cherche avec des variantes (sans le +)
        if not contact and phone_clean.startswith('+'):
            phone_without_plus = phone_clean[1:]
            contact = self.env['res.partner'].search([
                '|',
                ('phone', 'ilike', phone_without_plus),
                ('mobile', 'ilike', phone_without_plus)
            ], limit=1)
        
        # Si toujours pas trouvé et qu'on a un nom, on peut créer un contact
        if not contact and contact_name:
            # Optionnel : créer un contact automatiquement
            # contact = self.env['res.partner'].create({
            #     'name': contact_name,
            #     'phone': phone_clean,
            # })
            pass
        
        return contact

    def _find_or_create_conversation(self, phone, contact=None, contact_name=None):
        """Trouve ou crée une conversation"""
        if not phone:
            return None
        
        phone_clean = self._normalize_phone(phone)
        if not phone_clean:
            return None
        
        # Cherche la conversation
        domain = [('phone', '=', phone_clean)]
        if contact:
            domain.append(('contact_id', '=', contact.id))
        
        conversation = self.env['whatsapp.conversation'].search(domain, limit=1)
        
        # Si pas trouvée, crée une nouvelle conversation
        if not conversation:
            name = contact_name or contact.name if contact else phone_clean
            conversation = self.env['whatsapp.conversation'].create({
                'name': f"{name} - {phone_clean}",
                'phone': phone_clean,
                'contact_id': contact.id if contact else False,
                'contact_name': contact_name or (contact.name if contact else None),
            })
        
        # Met à jour le contact si nécessaire
        if contact and not conversation.contact_id:
            conversation.contact_id = contact.id
            if contact.name:
                conversation.contact_name = contact.name
        
        return conversation

    @api.model
    def create_from_webhook(self, payload):
        """Crée des enregistrements à partir du JSON du webhook."""
        data_str = json.dumps(payload)

        entry = (payload.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value", {})

        messages = value.get("messages") or []
        statuses = value.get("statuses") or []
        contacts_data = value.get("contacts") or []  # Informations de contact fournies par WhatsApp

        config = self.env["whatsapp.config"].search([("is_active", "=", True)], limit=1)

        created_records = self.env["whatsapp.message"]
        
        # Crée un mapping des contacts par numéro de téléphone
        contacts_map = {}
        for contact_data in contacts_data:
            phone = contact_data.get("wa_id")
            if phone:
                contacts_map[phone] = {
                    'name': contact_data.get("profile", {}).get("name", ""),
                    'phone': phone
                }

        # Messages entrants
        for msg in messages:
            mtype = msg.get("type", "unknown")
            from_phone = msg.get("from")
            metadata = value.get("metadata", {})
            wa_conversation_id = metadata.get("display_phone_number")

            text_body = ""
            caption = None
            media_id = None
            media_url = None
            media_mime = None
            template_name = None
            template_lang = None
            template_components = None
            message_type = "unknown"

            if mtype == "text":
                text_body = msg.get("text", {}).get("body", "")
                message_type = "text"

            elif mtype == "image":
                image = msg.get("image", {}) or {}
                caption = image.get("caption")
                media_id = image.get("id")
                media_mime = image.get("mime_type")
                message_type = "image"

            elif mtype == "document":
                doc = msg.get("document", {}) or {}
                caption = doc.get("caption")
                media_id = doc.get("id")
                media_mime = doc.get("mime_type")
                media_url = doc.get("link")  # si renvoyé
                message_type = "document"

            elif mtype == "audio":
                audio = msg.get("audio", {}) or {}
                media_id = audio.get("id")
                media_mime = audio.get("mime_type")
                message_type = "audio"

            elif mtype == "video":
                video = msg.get("video", {}) or {}
                caption = video.get("caption")
                media_id = video.get("id")
                media_mime = video.get("mime_type")
                message_type = "video"

            elif mtype == "sticker":
                sticker = msg.get("sticker", {}) or {}
                media_id = sticker.get("id")
                media_mime = sticker.get("mime_type")
                message_type = "sticker"

            elif mtype == "location":
                loc = msg.get("location", {}) or {}
                lat = loc.get("latitude")
                lng = loc.get("longitude")
                name = loc.get("name")
                address = loc.get("address")
                text_body = f"{lat}, {lng} - {name or ''} {address or ''}"
                message_type = "location"

            elif mtype == "contacts":
                # On log juste le JSON, tu pourras parser plus précisément si besoin
                message_type = "contacts"
                text_body = json.dumps(msg.get("contacts", []))

            elif mtype == "interactive":
                message_type = "interactive"
                interactive = msg.get("interactive", {}) or {}
                button_id = None
                
                # Traite les réponses de boutons
                if interactive.get("type") == "button_reply":
                    br = interactive.get("button_reply", {})
                    button_id = br.get("id")
                    text_body = br.get("title") or button_id or "Bouton cliqué"
                elif interactive.get("type") == "list_reply":
                    lr = interactive.get("list_reply", {})
                    button_id = lr.get("id")
                    text_body = lr.get("title") or button_id or "Option sélectionnée"
                else:
                    text_body = json.dumps(interactive)
                
                # Stocke l'ID du bouton dans le contenu pour référence
                if button_id:
                    text_body = f"[Bouton: {button_id}] {text_body}"

            elif mtype == "template":
                # Message template reçu (réponse à un template)
                template_data = msg.get("template", {}) or {}
                template_name = template_data.get("name")
                template_lang = template_data.get("language")
                template_components = template_data.get("components", [])
                
                message_type = "template"
                template_name = template_name or "unknown_template"
                template_lang = template_lang or {}
                text_body = f"Template: {template_name}"
                
                # Extrait le texte du body si disponible
                for comp in template_components:
                    if comp.get("type") == "body":
                        params = comp.get("parameters", [])
                        if params:
                            text_body = " ".join([p.get("text", "") for p in params if p.get("type") == "text"])

            elif mtype == "reaction":
                # Réaction à un message
                reaction = msg.get("reaction", {}) or {}
                emoji = reaction.get("emoji", "")
                message_id = reaction.get("message_id")
                message_type = "reaction"
                text_body = f"Réaction: {emoji}" if emoji else "Réaction"

            elif mtype == "unsupported":
                # Type de message non supporté
                message_type = "unsupported"
                text_body = "Message non supporté"
                _logger.warning("Message non supporté reçu : %s", json.dumps(msg))

            else:
                message_type = "unknown"
                text_body = str(msg)
                _logger.warning("Type de message inconnu reçu : %s - Contenu: %s", mtype, json.dumps(msg))

            # Trouve ou crée le contact
            contact = self._find_or_create_contact(
                from_phone,
                contacts_map.get(from_phone, {}).get('name')
            )
            
            # Trouve ou crée la conversation
            conversation = self._find_or_create_conversation(
                from_phone,
                contact,
                contacts_map.get(from_phone, {}).get('name')
            )
            
            # Extrait les informations de template si c'est un message template
            template_name_val = None
            template_lang_val = None
            template_components_val = None
            if mtype == "template":
                template_data = msg.get("template", {}) or {}
                template_name_val = template_data.get("name")
                template_lang_val = template_data.get("language")
                if isinstance(template_lang_val, dict):
                    template_lang_val = template_lang_val.get("code")
                template_components_val = json.dumps(template_data.get("components", []))

            rec = self.create({
                "direction": "in",
                "config_id": config.id if config else False,
                "conversation_id": conversation.id if conversation else False,
                "contact_id": contact.id if contact else False,
                "contact_name": contacts_map.get(from_phone, {}).get('name') or (contact.name if contact else None),
                "wa_message_id": msg.get("id"),
                "wa_conversation_id": wa_conversation_id,
                "phone": from_phone,
                "content": text_body,
                "message_type": message_type,
                "status": "received",
                "media_id": media_id,
                "media_url": media_url,
                "media_mime_type": media_mime,
                "caption": caption,
                "template_name": template_name_val,
                "template_language": template_lang_val,
                "template_components": template_components_val,
                "raw_payload": data_str,
            })
            created_records |= rec
            
            _logger.info("Message entrant créé : ID=%s, Type=%s, Phone=%s, Contact=%s", 
                        rec.id, message_type, from_phone, contact.name if contact else "N/A")
            
            # Si c'est un message interactif, exécute les actions associées
            if mtype == "interactive":
                try:
                    rec._process_button_action(interactive)
                except Exception as e:
                    _logger.exception("Erreur lors du traitement de l'action de bouton pour le message %s", rec.id)

        # Statuts (message status updates)
        for st in statuses:
            message_id = st.get("id")
            status = st.get("status")  # sent, delivered, read, failed, etc.
            phone = st.get("recipient_id")
            timestamp = st.get("timestamp")
            
            # Gère les erreurs de statut
            error_data = st.get("errors", [])
            error_message = None
            if error_data:
                error_message = json.dumps(error_data)
                _logger.warning("Erreur de statut pour le message %s : %s", message_id, error_message)

            # Mappe les statuts WhatsApp vers les statuts internes
            status_mapping = {
                "sent": "sent",
                "delivered": "delivered",
                "read": "read",
                "failed": "error",
                "deleted": "error",
            }
            
            internal_status = status_mapping.get(status, "sent")

            msg_rec = self.search([("wa_message_id", "=", message_id)], limit=1)
            if msg_rec:
                # Met à jour le statut
                update_vals = {
                    "wa_status": status,
                    "status": internal_status,
                }
                
                # Ajoute le message d'erreur si présent
                if error_message:
                    update_vals["raw_response"] = error_message
                    if status == "failed":
                        update_vals["content"] = f"[ÉCHEC] {msg_rec.content or 'Message non délivré'}"
                
                msg_rec.write(update_vals)
                
                _logger.info("Statut mis à jour pour le message %s (ID WhatsApp: %s) : %s -> %s", 
                            msg_rec.id, message_id, status, internal_status)
                
                # Si le message est lu, met à jour aussi la conversation
                if status == "read" and msg_rec.conversation_id:
                    # Optionnel : marquer la conversation comme lue
                    pass
            else:
                # Message non trouvé, crée un enregistrement de statut
                # Trouve le contact si possible
                contact = self._find_or_create_contact(phone) if phone else None
                conversation = self._find_or_create_conversation(phone, contact) if phone else None
                
                rec = self.create({
                    "direction": "out",
                    "config_id": config.id if config else False,
                    "conversation_id": conversation.id if conversation else False,
                    "contact_id": contact.id if contact else False,
                    "wa_message_id": message_id,
                    "phone": phone,
                    "wa_status": status,
                    "status": internal_status,
                    "raw_payload": data_str,
                    "raw_response": error_message or "",
                })
                created_records |= rec
                
                _logger.info("Enregistrement de statut créé pour le message WhatsApp %s : %s", message_id, status)

        return created_records

    def _process_button_action(self, interactive_data):
        """Traite les actions associées aux boutons cliqués"""
        self.ensure_one()
        
        try:
            # Extrait l'ID du bouton
            button_id = None
            if interactive_data.get("type") == "button_reply":
                button_id = interactive_data.get("button_reply", {}).get("id")
            elif interactive_data.get("type") == "list_reply":
                button_id = interactive_data.get("list_reply", {}).get("id")
            
            if not button_id:
                _logger.warning("Aucun ID de bouton trouvé dans le message interactif (Message ID: %s)", self.id)
                return
            
            _logger.info("Traitement de l'action de bouton : button_id=%s, message_id=%s, phone=%s", 
                        button_id, self.id, self.phone)
            
            # Utilise le contact déjà lié au message, sinon cherche
            contact = self.contact_id
            if not contact and self.phone:
                contact = self._find_or_create_contact(self.phone)
                if contact:
                    self.contact_id = contact.id
            
            # Cherche d'abord dans les scénarios interactifs
            scenarios = self.env['whatsapp.interactive.scenario'].search([
                ('active', '=', True)
            ])
            
            scenario_found = None
            for scenario in scenarios:
                if button_id in [scenario.button_1_id, scenario.button_2_id, scenario.button_3_id]:
                    scenario_found = scenario
                    break
            
            if scenario_found:
                _logger.info("Scénario interactif trouvé pour le bouton %s : %s", button_id, scenario_found.name)
                result = scenario_found.handle_button_click(button_id, self, contact)
                if result.get('success'):
                    self.content = f"[Scénario: {scenario_found.name}] Réponse envoyée"
                else:
                    self.content = f"[Scénario: {scenario_found.name}] Erreur : {result.get('message', 'Erreur inconnue')}"
                return
            
            # Si pas de scénario, cherche les actions de boutons classiques
            # D'abord recherche exacte
            actions = self.env['whatsapp.button.action'].search([
                ('button_id', '=', button_id),
                ('active', '=', True)
            ])
            
            # Si pas trouvé, cherche par préfixe (pour les IDs dynamiques comme btn_validate_order_98)
            if not actions:
                # Cherche les actions dont le button_id est un préfixe du button_id reçu
                all_actions = self.env['whatsapp.button.action'].search([
                    ('active', '=', True)
                ])
                
                for action in all_actions:
                    # Vérifie si le button_id reçu commence par le button_id de l'action suivi d'un underscore
                    # Exemple: button_id="btn_validate_order_98" et action.button_id="btn_validate_order"
                    if button_id.startswith(action.button_id + '_') or button_id == action.button_id:
                        actions |= action
                        # Ne break pas pour permettre de trouver toutes les actions correspondantes
                        # Mais généralement il n'y en a qu'une, donc on peut break
                        break
            
            if not actions:
                _logger.info("Aucune action trouvée pour le bouton %s (Message ID: %s, Phone: %s)", 
                            button_id, self.id, self.phone)
                # Met à jour le contenu du message pour indiquer qu'aucune action n'a été trouvée
                self.content = f"[Bouton: {button_id}] Aucune action configurée"
                return
            
            _logger.info("Actions trouvées pour le bouton %s : %s", button_id, [a.name for a in actions])
            
            # Exécute chaque action
            # Passe le button_id réel (avec ID) à l'action pour qu'elle puisse l'utiliser
            for action in actions:
                try:
                    _logger.info("Exécution de l'action '%s' (ID: %s) pour le bouton %s", 
                                action.name, action.id, button_id)
                    # Passe le button_id réel (avec ID de la commande) à l'action
                    result = action.execute_action(self, contact, button_id=button_id)
                    _logger.info("Action '%s' exécutée avec succès : %s", action.name, result.get('message', 'OK'))
                    
                    # Met à jour le contenu du message avec le résultat
                    if result.get('success'):
                        self.content = f"[Bouton: {button_id}] Action '{action.name}' exécutée : {result.get('message', 'Succès')}"
                    else:
                        self.content = f"[Bouton: {button_id}] Action '{action.name}' échouée : {result.get('message', 'Erreur')}"
                        
                except Exception as e:
                    _logger.exception("Erreur lors de l'exécution de l'action '%s' (ID: %s) : %s", 
                                    action.name, action.id, str(e))
                    self.content = f"[Bouton: {button_id}] Erreur lors de l'exécution de l'action '{action.name}' : {str(e)}"
                    
        except Exception as e:
            _logger.exception("Erreur lors du traitement de l'action de bouton (Message ID: %s) : %s", self.id, e)
            self.content = f"[Erreur traitement bouton] {str(e)}"
