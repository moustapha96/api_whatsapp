# whatsapp_business_api/models/whatsapp_send_message.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class WhatsappSendMessage(models.TransientModel):
    _name = "whatsapp.send.message"
    _description = "Wizard pour envoyer un message WhatsApp"

    config_id = fields.Many2one(
        "whatsapp.config",
        string="Configuration WhatsApp",
        required=True,
        help="Configuration WhatsApp à utiliser pour l'envoi",
    )

    phone = fields.Char(
        string="Numéro de téléphone",
        required=True,
        help="Numéro au format international (ex: +33612345678)",
    )

    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        help="Sélectionner un contact pour remplir automatiquement le numéro",
    )

    message = fields.Text(
        string="Message",
        required=True,
        help="Contenu du message à envoyer",
    )

    preview_url = fields.Boolean(
        string="Aperçu des liens",
        default=False,
        help="Si activé, les liens dans le message seront prévisualisés",
    )

    @api.model
    def default_get(self, fields_list):
        """Charge la configuration active par défaut et les valeurs du contexte"""
        res = super().default_get(fields_list)
        if 'config_id' in fields_list:
            config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
            if config:
                res['config_id'] = config.id
        
        # Support du paramètre default_message depuis le contexte
        if 'default_message' in self.env.context and 'message' in fields_list:
            res['message'] = self.env.context.get('default_message', '')
        
        return res

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        """Remplit automatiquement le numéro de téléphone depuis le contact"""
        if self.contact_id and self.contact_id.phone:
            # Nettoie le numéro de téléphone
            phone = self.contact_id.phone.replace(' ', '').replace('-', '').replace('.', '')
            if not phone.startswith('+'):
                # Ajoute le + si absent
                phone = '+' + phone.lstrip('+')
            self.phone = phone

    def action_send_message(self):
        """Envoie le message WhatsApp"""
        self.ensure_one()
        
        if not self.config_id:
            raise ValidationError(_("Veuillez sélectionner une configuration WhatsApp."))
        
        if not self.phone:
            raise ValidationError(_("Veuillez saisir un numéro de téléphone."))
        
        if not self.message:
            raise ValidationError(_("Veuillez saisir un message."))

        # Valide et nettoie le numéro de téléphone
        phone = self.config_id._validate_phone_number(self.phone)

        message_record = None
        try:
            # Envoie le message
            self.config_id.send_text_message(
                to_phone=phone,
                body_text=self.message,
                preview_url=self.preview_url
            )
            
            # Récupère le message créé
            message_record = self.env['whatsapp.message'].search([
                ('config_id', '=', self.config_id.id),
                ('phone', '=', phone),
                ('content', '=', self.message),
                ('direction', '=', 'out')
            ], order='create_date desc', limit=1)
            
            # Crée ou met à jour la conversation si un contact est associé
            if self.contact_id:
                conversation = self.env['whatsapp.conversation'].search([
                    ('phone', '=', phone),
                    ('contact_id', '=', self.contact_id.id)
                ], limit=1)
                
                if not conversation:
                    conversation = self.env['whatsapp.conversation'].create({
                        'name': f"{self.contact_id.name} - {phone}",
                        'phone': phone,
                        'contact_id': self.contact_id.id,
                        'contact_name': self.contact_id.name,
                    })
                
                # Lie le message à la conversation
                if message_record and conversation:
                    message_record.conversation_id = conversation.id
            
            # Retourne la vue du message pour voir le résultat
            if message_record:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Résultat de l\'envoi'),
                    'res_model': 'whatsapp.message',
                    'res_id': message_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Succès'),
                        'message': _('Message WhatsApp envoyé avec succès !'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except ValidationError as e:
            # Récupère le message d'erreur créé
            message_record = self.env['whatsapp.message'].search([
                ('config_id', '=', self.config_id.id),
                ('phone', '=', phone),
                ('content', '=', self.message),
                ('direction', '=', 'out'),
                ('status', '=', 'error')
            ], order='create_date desc', limit=1)
            
            # Affiche le message d'erreur et ouvre la vue du message
            if message_record:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Erreur d\'envoi'),
                    'res_model': 'whatsapp.message',
                    'res_id': message_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                    'context': {'form_view_initial_mode': 'readonly'}
                }
            else:
                raise
        except Exception as e:
            raise ValidationError(_("Erreur lors de l'envoi du message : %s") % str(e))


class WhatsappSendTemplate(models.TransientModel):
    _name = "whatsapp.send.template"
    _description = "Wizard pour envoyer un message WhatsApp via template"

    config_id = fields.Many2one(
        "whatsapp.config",
        string="Configuration WhatsApp",
        required=True,
        help="Configuration WhatsApp à utiliser pour l'envoi",
    )

    phone = fields.Char(
        string="Numéro de téléphone",
        required=True,
        help="Numéro au format international (ex: +33612345678)",
    )

    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        help="Sélectionner un contact pour remplir automatiquement le numéro",
    )

    template_id = fields.Many2one(
        "whatsapp.template",
        string="Template WhatsApp",
        required=True,
        help="Template WhatsApp à utiliser",
    )

    language_code = fields.Char(
        string="Code langue",
        default="fr",
        help="Code langue du template (ex: fr, en, fr_FR)",
    )

    template_params = fields.Text(
        string="Paramètres du template (JSON)",
        help="""Paramètres du template au format JSON.
        Exemple pour un template avec 2 paramètres dans le body:
        [
          {
            "type": "body",
            "parameters": [
              {"type": "text", "text": "Valeur paramètre 1"},
              {"type": "text", "text": "Valeur paramètre 2"}
            ]
          }
        ]""",
    )
    
    custom_message = fields.Text(
        string="Message personnalisé",
        help="Si vous remplissez ce champ, le message sera envoyé comme message texte simple (sujet à la fenêtre de 24h) au lieu d'utiliser le template. Laissez vide pour utiliser le template approuvé."
    )
    
    use_custom_message = fields.Boolean(
        string="Utiliser un message personnalisé",
        default=False,
        help="Cochez cette case pour envoyer un message texte personnalisé au lieu du template"
    )

    @api.model
    def default_get(self, fields_list):
        """Charge la configuration active par défaut"""
        res = super().default_get(fields_list)
        if 'config_id' in fields_list:
            config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
            if config:
                res['config_id'] = config.id
        return res

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        """Remplit automatiquement le numéro de téléphone depuis le contact"""
        if self.contact_id and self.contact_id.phone:
            phone = self.contact_id.phone.replace(' ', '').replace('-', '').replace('.', '')
            if not phone.startswith('+'):
                phone = '+' + phone.lstrip('+')
            self.phone = phone

    # Champs pour stocker les valeurs des paramètres dynamiquement
    parameter_values = fields.Text(
        string="Valeurs des paramètres (JSON)",
        help="Stocke les valeurs saisies pour les paramètres du template",
        default="{}",
    )
    
    template_structure_json = fields.Text(
        string="Structure du template (JSON)",
        compute="_compute_template_structure_json",
        store=False,
        help="Structure du template au format JSON pour le widget JavaScript",
    )
    
    template_has_parameters = fields.Boolean(
        string="Template a des paramètres",
        compute="_compute_template_has_parameters",
        store=False,
        help="Indique si le template sélectionné a des paramètres",
    )
    
    @api.depends('template_id', 'template_id.parameter_structure')
    def _compute_template_structure_json(self):
        """Calcule la structure du template au format JSON pour le widget"""
        for record in self:
            if record.template_id and record.template_id.parameter_structure:
                record.template_structure_json = record.template_id.parameter_structure
            else:
                record.template_structure_json = "{}"
    
    @api.depends('template_id', 'template_id.has_parameters')
    def _compute_template_has_parameters(self):
        """Calcule si le template a des paramètres"""
        for record in self:
            if record.template_id:
                # Force le calcul de has_parameters sur le template
                record.template_id._compute_has_parameters()
                record.template_has_parameters = record.template_id.has_parameters
            else:
                record.template_has_parameters = False
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Met à jour le code langue depuis le template et réinitialise les paramètres"""
        if self.template_id:
            self.language_code = self.template_id.language_code or "fr"
            # Réinitialise les valeurs des paramètres
            self.parameter_values = "{}"
            self.template_params = ""
            # Force le recalcul de la structure pour que le JavaScript puisse la lire
            self._compute_template_structure_json()
            self._compute_template_has_parameters()
    
    @api.onchange('use_custom_message')
    def _onchange_use_custom_message(self):
        """Réinitialise le message personnalisé si on désactive"""
        if not self.use_custom_message:
            self.custom_message = False
    
    def get_template_structure(self):
        """Retourne la structure du template sélectionné (pour JavaScript)"""
        self.ensure_one()
        if self.template_id and self.template_id.parameter_structure:
            return {
                'structure': self.template_id.parameter_structure,
                'has_parameters': self.template_id.has_parameters
            }
        return {
            'structure': '{}',
            'has_parameters': False
        }
    
    def _build_components_from_values(self, param_values):
        """
        Construit les components à partir des valeurs saisies.
        
        Args:
            param_values: Dict avec les valeurs, format:
                {
                    "body_1": "Valeur 1",
                    "body_2": "Valeur 2",
                    "header_1": "URL image",
                    "button_0": "URL bouton"
                }
        
        Returns:
            Liste de components au format Meta
        """
        if not param_values:
            return None
        
        structure = self.template_id.get_parameter_structure() if self.template_id else {}
        components = []
        
        # Construit les paramètres du header
        header_params = []
        if structure.get("header"):
            for param_def in structure.get("header", []):
                param_key = f"header_{param_def.get('index', 1)}"
                value = param_values.get(param_key, "")
                if value:
                    if param_def.get("type") == "image":
                        header_params.append({
                            "type": "image",
                            "image": {"link": value}
                        })
                    elif param_def.get("type") == "document":
                        header_params.append({
                            "type": "document",
                            "document": {"link": value}
                        })
                    elif param_def.get("type") == "text":
                        header_params.append({
                            "type": "text",
                            "text": value
                        })
        
        if header_params:
            components.append({
                "type": "header",
                "parameters": header_params
            })
        
        # Construit les paramètres du body
        body_params = []
        if structure.get("body"):
            for param_def in structure.get("body", []):
                param_key = f"body_{param_def.get('index', 1)}"
                value = param_values.get(param_key, "")
                if value:
                    body_params.append({
                        "type": "text",
                        "text": value
                    })
        
        if body_params:
            components.append({
                "type": "body",
                "parameters": body_params
            })
        
        # Construit les paramètres des boutons
        button_params = []
        if structure.get("buttons"):
            for param_def in structure.get("buttons", []):
                param_key = f"button_{param_def.get('index', 0)}"
                value = param_values.get(param_key, "")
                if value:
                    button_params.append({
                        "type": "text",
                        "text": value
                    })
        
        if button_params:
            # Trouve le premier bouton de type URL dans la structure
            for param_def in structure.get("buttons", []):
                if param_def.get("type") == "url":
                    components.append({
                        "type": "button",
                        "sub_type": "url",
                        "index": str(param_def.get("index", 0)),
                        "parameters": button_params[:1]  # Prend seulement le premier paramètre pour le bouton URL
                    })
                    break
        
        return components if components else None
    
    def _build_components_from_structure(self, structure, param_values):
        """
        Construit les components à partir de la structure du template.
        Utilisé comme fallback si aucune valeur n'est fournie.
        """
        return self._build_components_from_values(param_values)

    def action_send_template(self):
        """Envoie le message WhatsApp via template ou message texte personnalisé"""
        self.ensure_one()
        
        if not self.config_id:
            raise ValidationError(_("Veuillez sélectionner une configuration WhatsApp."))
        
        if not self.phone:
            raise ValidationError(_("Veuillez saisir un numéro de téléphone."))

        # Valide et nettoie le numéro de téléphone
        phone = self.config_id._validate_phone_number(self.phone)

        message_record = None
        
        # Si un message personnalisé est fourni, envoyer comme message texte simple
        if self.use_custom_message and self.custom_message:
            if not self.custom_message.strip():
                raise ValidationError(_("Veuillez saisir un message personnalisé."))
            
            try:
                # Envoie un message texte simple
                self.config_id.send_text_message(
                    to_phone=phone,
                    body_text=self.custom_message
                )
                
                # Récupère le message créé
                message_record = self.env['whatsapp.message'].search([
                    ('config_id', '=', self.config_id.id),
                    ('phone', '=', phone),
                    ('content', '=', self.custom_message),
                    ('direction', '=', 'out'),
                    ('message_type', '=', 'text')
                ], order='create_date desc', limit=1)
                
                # Crée ou met à jour la conversation si un contact est associé
                if self.contact_id:
                    conversation = self.env['whatsapp.conversation'].search([
                        ('phone', '=', phone),
                        ('contact_id', '=', self.contact_id.id)
                    ], limit=1)
                    
                    if not conversation:
                        conversation = self.env['whatsapp.conversation'].create({
                            'name': f"{self.contact_id.name} - {phone}",
                            'phone': phone,
                            'contact_id': self.contact_id.id,
                            'contact_name': self.contact_id.name,
                        })
                    
                    # Lie le message à la conversation
                    if message_record and conversation:
                        message_record.conversation_id = conversation.id
                
            except ValidationError as e:
                # Récupère le message d'erreur créé
                error_message_record = self.env['whatsapp.message'].search([
                    ('config_id', '=', self.config_id.id),
                    ('phone', '=', phone),
                    ('content', '=', self.custom_message),
                    ('direction', '=', 'out'),
                    ('status', '=', 'error')
                ], order='create_date desc', limit=1)
                
                if error_message_record:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Erreur d\'envoi'),
                        'res_model': 'whatsapp.message',
                        'res_id': error_message_record.id,
                        'view_mode': 'form',
                        'target': 'current',
                        'context': {'form_view_initial_mode': 'readonly'}
                    }
                else:
                    raise
            except Exception as e:
                raise ValidationError(_("Erreur lors de l'envoi du message texte : %s") % str(e))
        
        # Sinon, utiliser le template
        else:
            if not self.template_id:
                raise ValidationError(_("Veuillez sélectionner un template ou activer le message personnalisé."))

            # Construit les components à partir des valeurs saisies ou du JSON manuel
            components = None
            
            # Priorité 1 : Utilise les valeurs saisies dans parameter_values si disponibles
            if self.parameter_values and self.parameter_values.strip() != "{}":
                try:
                    param_values = json.loads(self.parameter_values)
                    components = self._build_components_from_values(param_values)
                except json.JSONDecodeError:
                    _logger.warning("Format JSON invalide pour parameter_values, utilisation de template_params")
                    # Fallback sur template_params
                    if self.template_params:
                        try:
                            components = json.loads(self.template_params)
                        except json.JSONDecodeError:
                            raise ValidationError(_("Format JSON invalide pour les paramètres du template."))
            
            # Priorité 2 : Utilise template_params si parameter_values est vide
            elif self.template_params:
                try:
                    components = json.loads(self.template_params)
                except json.JSONDecodeError:
                    raise ValidationError(_("Format JSON invalide pour les paramètres du template."))
            
            # Si le template a des paramètres mais qu'aucune valeur n'est fournie, on essaie de construire depuis la structure
            elif self.template_id.has_parameters:
                structure = self.template_id.get_parameter_structure()
                if structure:
                    # Construit des components vides pour permettre l'envoi (l'utilisateur devra les remplir)
                    components = self._build_components_from_structure(structure, {})

            try:
                # Envoie le message template
                self.config_id.send_template_message(
                    to_phone=phone,
                    template_name=self.template_id.wa_name,
                    language_code=self.language_code or "fr",
                    components=components
                )
            
                # Récupère le message créé
                message_record = self.env['whatsapp.message'].search([
                    ('config_id', '=', self.config_id.id),
                    ('phone', '=', phone),
                    ('template_name', '=', self.template_id.wa_name),
                    ('direction', '=', 'out')
                ], order='create_date desc', limit=1)
            
                # Crée ou met à jour la conversation si un contact est associé
                if self.contact_id:
                    conversation = self.env['whatsapp.conversation'].search([
                        ('phone', '=', phone),
                        ('contact_id', '=', self.contact_id.id)
                    ], limit=1)
                
                    if not conversation:
                        conversation = self.env['whatsapp.conversation'].create({
                            'name': f"{self.contact_id.name} - {phone}",
                            'phone': phone,
                            'contact_id': self.contact_id.id,
                            'contact_name': self.contact_id.name,
                        })
                
                    # Lie le message à la conversation
                    if message_record and conversation:
                        message_record.conversation_id = conversation.id
            
            except ValidationError as e:
                # Récupère le message d'erreur créé
                error_message_record = self.env['whatsapp.message'].search([
                    ('config_id', '=', self.config_id.id),
                    ('phone', '=', phone),
                    ('template_name', '=', self.template_id.wa_name),
                    ('direction', '=', 'out'),
                    ('status', '=', 'error')
                ], order='create_date desc', limit=1)
                
                if error_message_record:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Erreur d\'envoi'),
                        'res_model': 'whatsapp.message',
                        'res_id': error_message_record.id,
                        'view_mode': 'form',
                        'target': 'current',
                        'context': {'form_view_initial_mode': 'readonly'}
                    }
                else:
                    raise
            except Exception as e:
                raise ValidationError(_("Erreur lors de l'envoi du message template : %s") % str(e))
        
        # Retourne la vue du message pour voir le résultat (pour les deux cas)
        if message_record:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Résultat de l\'envoi'),
                'res_model': 'whatsapp.message',
                'res_id': message_record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            message_type = _('texte personnalisé') if (self.use_custom_message and self.custom_message) else _('template')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Message WhatsApp (%s) envoyé avec succès !') % message_type,
                    'type': 'success',
                    'sticky': False,
                }
            }


class WhatsappSendInteractive(models.TransientModel):
    _name = "whatsapp.send.interactive"
    _description = "Wizard pour envoyer un message WhatsApp avec boutons"

    config_id = fields.Many2one(
        "whatsapp.config",
        string="Configuration WhatsApp",
        required=True,
        help="Configuration WhatsApp à utiliser pour l'envoi",
    )

    phone = fields.Char(
        string="Numéro de téléphone",
        required=True,
        help="Numéro au format international (ex: +33612345678)",
    )

    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        help="Sélectionner un contact pour remplir automatiquement le numéro",
    )

    message = fields.Text(
        string="Message",
        required=True,
        help="Contenu du message avec boutons",
    )

    button_1_id = fields.Char("ID Bouton 1", default="btn_1")
    button_1_title = fields.Char("Titre Bouton 1", default="Oui")

    button_2_id = fields.Char("ID Bouton 2", default="btn_2")
    button_2_title = fields.Char("Titre Bouton 2", default="Non")

    button_3_id = fields.Char("ID Bouton 3", default="btn_3")
    button_3_title = fields.Char("Titre Bouton 3", default="Plus d'infos")

    @api.model
    def default_get(self, fields_list):
        """Charge la configuration active par défaut"""
        res = super().default_get(fields_list)
        if 'config_id' in fields_list:
            config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
            if config:
                res['config_id'] = config.id
        return res

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        """Remplit automatiquement le numéro de téléphone depuis le contact"""
        if self.contact_id and self.contact_id.phone:
            phone = self.contact_id.phone.replace(' ', '').replace('-', '').replace('.', '')
            if not phone.startswith('+'):
                phone = '+' + phone.lstrip('+')
            self.phone = phone

    def action_send_interactive(self):
        """Envoie le message avec boutons"""
        self.ensure_one()
        
        if not self.config_id:
            raise ValidationError(_("Veuillez sélectionner une configuration WhatsApp."))
        
        if not self.phone:
            raise ValidationError(_("Veuillez saisir un numéro de téléphone."))
        
        if not self.message:
            raise ValidationError(_("Veuillez saisir un message."))

        # Valide et nettoie le numéro de téléphone
        phone = self.config_id._validate_phone_number(self.phone)

        # Construit la liste des boutons
        buttons = []
        if self.button_1_id and self.button_1_title:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": self.button_1_id,
                    "title": self.button_1_title
                }
            })
        if self.button_2_id and self.button_2_title:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": self.button_2_id,
                    "title": self.button_2_title
                }
            })
        if self.button_3_id and self.button_3_title:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": self.button_3_id,
                    "title": self.button_3_title
                }
            })

        if not buttons:
            raise ValidationError(_("Veuillez définir au moins un bouton."))

        message_record = None
        try:
            # Envoie le message interactif
            self.config_id.send_interactive_message(
                to_phone=phone,
                body_text=self.message,
                buttons=buttons
            )
            
            # Récupère le message créé
            message_record = self.env['whatsapp.message'].search([
                ('config_id', '=', self.config_id.id),
                ('phone', '=', phone),
                ('content', '=', self.message),
                ('direction', '=', 'out'),
                ('message_type', '=', 'interactive')
            ], order='create_date desc', limit=1)
            
            # Crée ou met à jour la conversation
            if self.contact_id:
                conversation = self.env['whatsapp.conversation'].search([
                    ('phone', '=', phone),
                    ('contact_id', '=', self.contact_id.id)
                ], limit=1)
                
                if not conversation:
                    conversation = self.env['whatsapp.conversation'].create({
                        'name': f"{self.contact_id.name} - {phone}",
                        'phone': phone,
                        'contact_id': self.contact_id.id,
                        'contact_name': self.contact_id.name,
                    })
                
                if message_record and conversation:
                    message_record.conversation_id = conversation.id
            
            if message_record:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Résultat de l\'envoi'),
                    'res_model': 'whatsapp.message',
                    'res_id': message_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Succès'),
                        'message': _('Message WhatsApp avec boutons envoyé avec succès !'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except ValidationError as e:
            message_record = self.env['whatsapp.message'].search([
                ('config_id', '=', self.config_id.id),
                ('phone', '=', phone),
                ('content', '=', self.message),
                ('direction', '=', 'out'),
                ('status', '=', 'error')
            ], order='create_date desc', limit=1)
            
            if message_record:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Erreur d\'envoi'),
                    'res_model': 'whatsapp.message',
                    'res_id': message_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                raise
        except Exception as e:
            raise ValidationError(_("Erreur lors de l'envoi du message : %s") % str(e))


class WhatsappSendScenarioWizard(models.TransientModel):
    _name = "whatsapp.send.scenario.wizard"
    _description = "Wizard pour envoyer un scénario interactif"

    scenario_id = fields.Many2one(
        'whatsapp.interactive.scenario',
        string="Scénario",
        required=True,
        help="Scénario interactif à envoyer"
    )

    config_id = fields.Many2one(
        'whatsapp.config',
        string="Configuration WhatsApp",
        help="Configuration à utiliser (si non spécifiée, utilise la configuration du scénario ou la configuration active)"
    )

    contact_id = fields.Many2one(
        'res.partner',
        string="Contact",
        help="Contact destinataire (optionnel)"
    )

    phone = fields.Char(
        string="Numéro de téléphone",
        required=True,
        help="Numéro de téléphone au format international (ex: +33612345678)"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'config_id' in fields_list and not res.get('config_id'):
            config = self.env['whatsapp.config'].get_active_config()
            if config:
                res['config_id'] = config.id
        return res

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        """Remplit automatiquement le numéro de téléphone depuis le contact"""
        if self.contact_id and self.contact_id.phone:
            phone = self.contact_id.phone.replace(' ', '').replace('-', '').replace('.', '')
            if not phone.startswith('+'):
                phone = '+' + phone.lstrip('+')
            self.phone = phone

    def action_send_scenario(self):
        """Envoie le scénario"""
        self.ensure_one()
        
        if not self.scenario_id:
            raise ValidationError(_("Veuillez sélectionner un scénario."))
        
        if not self.phone:
            raise ValidationError(_("Veuillez saisir un numéro de téléphone."))

        # Utilise la configuration du wizard ou celle du scénario
        if self.config_id:
            self.scenario_id.config_id = self.config_id

        result = self.scenario_id.send_scenario(
            to_phone=self.phone,
            contact_id=self.contact_id.id if self.contact_id else None
        )

        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Scénario "%s" envoyé avec succès !') % self.scenario_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError(_("Erreur lors de l'envoi du scénario : %s") % result.get('error', 'Erreur inconnue'))
