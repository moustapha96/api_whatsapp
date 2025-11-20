# whatsapp_business_api/models/whatsapp_send_message.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


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

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Met à jour le code langue depuis le template"""
        if self.template_id:
            self.language_code = self.template_id.language_code or "fr"
    
    @api.onchange('use_custom_message')
    def _onchange_use_custom_message(self):
        """Réinitialise le message personnalisé si on désactive"""
        if not self.use_custom_message:
            self.custom_message = False

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

            # Parse les paramètres du template
            components = None
            if self.template_params:
                try:
                    components = json.loads(self.template_params)
                except json.JSONDecodeError:
                    raise ValidationError(_("Format JSON invalide pour les paramètres du template."))

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
