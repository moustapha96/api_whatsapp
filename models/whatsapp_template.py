# whatsapp_business_api/models/whatsapp_template.py
from odoo import models, fields, api, _
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

    body_text = fields.Text(
        string="Texte du corps (Meta)",
        help="Texte du template avec variables {{1}}, {{2}}, etc. Utilisé pour envoyer le template vers WhatsApp Business. Exemple : « Votre facture {{1}} est prête » ou « {{1}} » pour un seul paramètre."
    )

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

    def clean_text(self, text):
        """Nettoie le texte avant l'envoi : corrige mojibake puis normalise en UTF-8."""
        if not text:
            return ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", "ignore")
        # Corrige les séquences mojibake courantes (UTF-8 lu en Latin-1)
        replacements = [
            ("\ufffd", "?"),
            ("Ã©", "e"), ("Ã¨", "e"), ("Ãª", "e"), ("Ã«", "e"),
            ("Ã ", "a"), ("Ã¢", "a"), ("Ã¥", "a"),
            ("Ã§", "c"),
            ("Ã¹", "u"), ("Ã»", "u"), ("Ã¼", "u"),
            ("Ã¯", "i"), ("Ã®", "i"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        # Translittération accents -> ASCII pour éviter rejet Meta (encodage)
        accent_to_ascii = [
            ("à", "a"), ("á", "a"), ("â", "a"), ("ã", "a"), ("ä", "a"), ("å", "a"),
            ("è", "e"), ("é", "e"), ("ê", "e"), ("ë", "e"),
            ("ì", "i"), ("í", "i"), ("î", "i"), ("ï", "i"),
            ("ò", "o"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ö", "o"),
            ("ù", "u"), ("ú", "u"), ("û", "u"), ("ü", "u"),
            ("ñ", "n"), ("ç", "c"), ("œ", "oe"), ("æ", "ae"),
        ]
        for acc, asc in accent_to_ascii:
            text = text.replace(acc, asc)
        return text.encode("utf-8", "ignore").decode("utf-8").strip()

    def _validate_wa_name(self):
        """Valide le nom du template (wa_name). Retourne (True, "") ou (False, message_erreur)."""
        self.ensure_one()
        if not self.wa_name or not self.wa_name.strip():
            return False, _("Le nom du template (wa_name) est requis.")
        if " " in self.wa_name:
            return False, _("Le nom du template ne doit pas contenir d'espaces.")
        if not self.wa_name.islower():
            return False, _("Le nom du template doit être en minuscules.")
        return True, ""

    def _get_body_text_for_meta(self):
        """Retourne le texte du corps pour l'API Meta (avec {{1}}, {{2}}, etc.)."""
        self.ensure_one()
        if self.body_text and self.body_text.strip():
            return self.body_text.strip()
        structure = self.get_parameter_structure()
        body_params = structure.get("body") or []
        if not body_params:
            return "Message"
        return " ".join("{{%d}}" % p.get("index", i + 1) for i, p in enumerate(body_params))

    def _validate_template(self):
        """Valide les données du template avant envoi vers Meta. Retourne une liste d'erreurs (vide si OK)."""
        self.ensure_one()
        errors = []
        ok, msg = self._validate_wa_name()
        if not ok:
            errors.append(msg)
        if not self.body_text or not self.body_text.strip():
            errors.append(_("Le texte du corps (body_text) est obligatoire."))
        else:
            structure = self.get_parameter_structure()
            body_params = structure.get("body") or []
            if body_params and "{{" not in self.body_text:
                errors.append(_("Le texte du corps doit contenir des placeholders (ex: {{1}}) lorsque le template a des paramètres."))
        lang = (self.language_code or "").strip()
        if not lang:
            errors.append(_("Le code langue est obligatoire (ex: fr_FR, en_US)."))
        category = (self.category or "").strip().upper()
        if category not in ("UTILITY", "MARKETING", "AUTHENTICATION", "UNKNOWN"):
            errors.append(_("La catégorie doit être UTILITY, MARKETING ou AUTHENTICATION."))
        return errors

    def _build_meta_create_payload(self):
        """Construit le payload pour créer le template dans WhatsApp Business (Meta).
        Conforme aux exemples Meta :
        - positionnel : parameter_format "positional", example.body_text = [ ["val1", "val2"] ]
        - nommé : parameter_format "named", example.body_text_named_params = [ { param_name, example }, ... ]
        """
        self.ensure_one()
        raw_body = self.body_text or self._get_body_text_for_meta() or ""
        body_text = self.clean_text(raw_body)
        structure = self.get_parameter_structure()
        body_params = structure.get("body") or []

        body_component = {"type": "body", "text": body_text}

        if body_params:
            has_named = any(p.get("param_name") for p in body_params)
            if has_named:
                body_component["example"] = {
                    "body_text_named_params": [
                        {
                            "param_name": p.get("param_name", "param_%d" % (i + 1)),
                            "example": p.get("example", "Exemple%d" % (i + 1)),
                        }
                        for i, p in enumerate(body_params)
                    ]
                }
            else:
                example_values = ["Exemple%d" % (i + 1) for i in range(len(body_params))]
                body_component["example"] = {"body_text": [example_values]}

        components = [body_component]
        lang = (self.language_code or "fr").strip()
        if lang.lower().startswith("fr"):
            lang = "fr_FR"
        elif lang.lower().startswith("en"):
            lang = "en_US"
        category = (self.category or "UNKNOWN").strip().upper()
        if category not in ("UTILITY", "MARKETING", "AUTHENTICATION"):
            category = "UTILITY"
        category_lower = category.lower()
        name_safe = (self.wa_name or "").lower().replace(" ", "_").strip()
        payload = {
            "name": name_safe or "template",
            "language": lang,
            "category": category_lower,
            "components": components,
        }
        if body_params:
            payload["parameter_format"] = "named" if any(p.get("param_name") for p in body_params) else "positional"
        return payload
