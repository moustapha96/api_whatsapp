# Documentation Technique - Module WhatsApp Business API pour Odoo

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Modèles de données](#modèles-de-données)
4. [API et méthodes principales](#api-et-méthodes-principales)
5. [Contrôleurs et Webhooks](#contrôleurs-et-webhooks)
6. [Vues et interfaces](#vues-et-interfaces)
7. [Sécurité](#sécurité)
8. [Intégrations](#intégrations)
9. [Configuration](#configuration)
10. [Exemples d'utilisation](#exemples-dutilisation)

---

## Vue d'ensemble

### Informations générales

- **Nom du module** : `api_whatsapp`
- **Version** : 16.0.1.0.0
- **Auteur** : Al Hussein
- **Licence** : LGPL-3
- **Catégorie** : CCBM
- **Odoo Version** : 16.0

### Dépendances

**Modules Odoo** :
- `base` : Fonctionnalités de base d'Odoo
- `contacts` : Gestion des contacts/partenaires
- `sale` : Commandes de vente (optionnel, pour l'intégration)

**Dépendances Python** :
- `requests` : Pour les appels API HTTP

### Fonctionnalités principales

1. **Configuration WhatsApp Business Cloud API**
   - Gestion des tokens d'accès
   - Configuration des endpoints
   - Gestion des webhooks

2. **Envoi de messages**
   - Messages texte simples
   - Templates WhatsApp approuvés
   - Messages interactifs avec boutons
   - Messages média (image, vidéo, document, audio, localisation)

3. **Réception de messages**
   - Webhook pour recevoir les messages entrants
   - Traitement des statuts de messages
   - Gestion des interactions (boutons)

4. **Journalisation**
   - Historique complet des messages
   - Suivi des statuts
   - Gestion des conversations

5. **Templates**
   - Synchronisation des templates depuis Meta
   - Gestion des templates approuvés
   - Utilisation des templates avec paramètres

6. **Actions de boutons**
   - Configuration d'actions automatiques
   - Exécution de code Python personnalisé
   - Mise à jour de contacts
   - Création de tickets

7. **Intégrations**
   - Intégration avec `sale.order` (commandes)
   - Intégration avec `res.partner` (partenaires)
   - Envoi automatique de notifications

---

## Architecture

### Structure du module

```
api_whatsapp/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── whatsapp_webhook.py          # Contrôleur webhook
├── models/
│   ├── __init__.py
│   ├── whatsapp_config.py           # Configuration WhatsApp
│   ├── whatsapp_message.py         # Messages WhatsApp
│   ├── whatsapp_conversation.py    # Conversations
│   ├── whatsapp_template.py        # Templates
│   ├── whatsapp_send_message.py    # Wizards d'envoi
│   ├── whatsapp_send_partner_message.py  # Wizard envoi partenaire
│   ├── whatsapp_button_action.py   # Actions de boutons
│   ├── sale_order_whatsapp.py      # Extension sale.order
│   └── res_config_settings.py      # Paramètres système
├── views/
│   ├── whatsapp_config_views.xml
│   ├── whatsapp_message_views.xml
│   ├── whatsapp_conversation_views.xml
│   ├── whatsapp_template_views.xml
│   ├── whatsapp_send_message_views.xml
│   ├── whatsapp_send_partner_message_views.xml
│   ├── whatsapp_button_action_views.xml
│   ├── res_partner_whatsapp_views.xml
│   └── sale_order_whatsapp_views.xml
├── security/
│   └── ir.model.access.csv          # Droits d'accès
└── data/
    ├── whatsapp_template_examples.xml
    ├── whatsapp_button_action_examples.xml
    └── whatsapp_order_validation_actions.xml
```

### Flux de données

```
┌─────────────┐
│   Odoo      │
│  Interface  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Models Odoo    │
│  (whatsapp.*)   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  WhatsApp API   │
│  (Meta Cloud)   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   Webhook       │
│  (Réception)    │
└─────────────────┘
```

---

## Modèles de données

### 1. `whatsapp.config`

**Description** : Configuration principale de l'API WhatsApp Business Cloud.

**Champs principaux** :
- `name` (Char) : Nom de la configuration
- `phone_number_id` (Char) : ID du numéro de téléphone WhatsApp
- `access_token` (Char) : Token d'accès API
- `api_version` (Char) : Version de l'API (défaut: v21.0)
- `webhook_verify_token` (Char) : Token de vérification webhook
- `webhook_url` (Char) : URL du webhook
- `is_active` (Boolean) : Configuration active

**Méthodes principales** :
- `send_text_message(to_phone, body_text, preview_url=False)` : Envoie un message texte
- `send_template_message(to_phone, template_name, language_code, components=None)` : Envoie un template
- `send_interactive_message(to_phone, body_text, buttons=None)` : Envoie un message avec boutons
- `send_text_to_partner(partner_id, message_text, preview_url=False, config_id=None)` : Fonction utilitaire pour envoyer à un partenaire
- `action_sync_templates()` : Synchronise les templates depuis Meta
- `action_verify_parameters()` : Vérifie les paramètres de configuration
- `_validate_phone_number(phone)` : Valide et nettoie un numéro de téléphone

### 2. `whatsapp.message`

**Description** : Journal de tous les messages WhatsApp (entrants et sortants).

**Champs principaux** :
- `direction` (Selection) : "in" (entrant) ou "out" (sortant)
- `config_id` (Many2one) : Configuration utilisée
- `conversation_id` (Many2one) : Conversation associée
- `contact_id` (Many2one) : Contact/partenaire
- `phone` (Char) : Numéro de téléphone
- `wa_message_id` (Char) : ID du message WhatsApp
- `wa_status` (Char) : Statut brut WhatsApp
- `content` (Text) : Contenu du message
- `message_type` (Selection) : Type (text, image, video, etc.)
- `status` (Selection) : Statut (sent, delivered, read, error, etc.)
- `raw_payload` (Text) : Payload JSON envoyé
- `raw_response` (Text) : Réponse JSON reçue
- `error_help` (Text) : Aide pour les erreurs (champ calculé)

**Méthodes principales** :
- `create_from_webhook(webhook_data)` : Crée un message depuis un webhook
- `_process_button_action()` : Traite les actions de boutons interactifs

### 3. `whatsapp.conversation`

**Description** : Regroupe les messages par conversation.

**Champs principaux** :
- `name` (Char) : Identifiant de la conversation
- `phone` (Char) : Numéro de téléphone
- `contact_id` (Many2one) : Contact associé
- `contact_name` (Char) : Nom du contact
- `message_ids` (One2many) : Messages de la conversation
- `message_count` (Integer) : Nombre de messages (calculé)

**Méthodes principales** :
- `_compute_message_count()` : Calcule le nombre de messages

### 4. `whatsapp.template`

**Description** : Templates WhatsApp synchronisés depuis Meta.

**Champs principaux** :
- `name` (Char) : Nom du template
- `wa_name` (Char) : Nom dans WhatsApp
- `language_code` (Char) : Code langue
- `category` (Char) : Catégorie (UTILITY, MARKETING, etc.)
- `status` (Char) : Statut (APPROVED, PENDING, etc.)
- `description` (Text) : Description

### 5. `whatsapp.send.message` (TransientModel)

**Description** : Wizard pour envoyer un message texte simple.

**Champs principaux** :
- `config_id` (Many2one) : Configuration
- `phone` (Char) : Numéro de téléphone
- `contact_id` (Many2one) : Contact
- `message` (Text) : Message à envoyer
- `preview_url` (Boolean) : Prévisualisation des liens

**Méthodes principales** :
- `action_send_message()` : Envoie le message

### 6. `whatsapp.send.template` (TransientModel)

**Description** : Wizard pour envoyer un message via template.

**Champs principaux** :
- `config_id` (Many2one) : Configuration
- `template_id` (Many2one) : Template à utiliser
- `phone` (Char) : Numéro de téléphone
- `contact_id` (Many2one) : Contact
- `language_code` (Char) : Code langue
- `template_params` (Text) : Paramètres JSON du template
- `use_custom_message` (Boolean) : Utiliser un message personnalisé
- `custom_message` (Text) : Message personnalisé

**Méthodes principales** :
- `action_send_template()` : Envoie le template ou le message personnalisé

### 7. `whatsapp.send.partner.message` (TransientModel)

**Description** : Wizard pour envoyer un message à un partenaire.

**Champs principaux** :
- `config_id` (Many2one) : Configuration
- `partner_id` (Many2one) : Partenaire
- `phone` (Char) : Numéro de téléphone
- `message` (Text) : Message
- `preview_url` (Boolean) : Prévisualisation des liens

**Méthodes principales** :
- `action_send_message()` : Envoie le message au partenaire

### 8. `whatsapp.send.interactive` (TransientModel)

**Description** : Wizard pour envoyer un message avec boutons interactifs.

**Champs principaux** :
- `config_id` (Many2one) : Configuration
- `phone` (Char) : Numéro de téléphone
- `contact_id` (Many2one) : Contact
- `message` (Text) : Message
- `button_1_id`, `button_1_title` : Bouton 1
- `button_2_id`, `button_2_title` : Bouton 2
- `button_3_id`, `button_3_title` : Bouton 3

**Méthodes principales** :
- `action_send_interactive()` : Envoie le message avec boutons

### 9. `whatsapp.button.action`

**Description** : Actions à exécuter lors d'un clic sur un bouton WhatsApp.

**Champs principaux** :
- `name` (Char) : Nom de l'action
- `button_id` (Char) : ID du bouton (unique)
- `action_type` (Selection) : Type d'action
  - `send_message` : Envoyer un message
  - `update_contact` : Mettre à jour le contact
  - `create_ticket` : Créer un ticket
  - `update_status` : Mettre à jour le statut
  - `custom_python` : Code Python personnalisé
- `message_to_send` (Text) : Message à envoyer
- `contact_field_to_update` (Char) : Champ contact à mettre à jour
- `contact_field_value` (Char) : Valeur à définir
- `python_code` (Text) : Code Python à exécuter
- `active` (Boolean) : Actif
- `sequence` (Integer) : Séquence

**Méthodes principales** :
- `execute_action(message, contact=None)` : Exécute l'action

### 10. `sale.order` (Extension)

**Description** : Extension du modèle `sale.order` pour l'intégration WhatsApp.

**Champs ajoutés** :
- `x_whatsapp_validation_sent` (Boolean) : Validation WhatsApp envoyée
- `x_whatsapp_validation_sent_date` (Datetime) : Date envoi validation
- `x_whatsapp_validated` (Boolean) : Validée via WhatsApp
- `x_whatsapp_rejected` (Boolean) : Rejetée via WhatsApp
- `x_whatsapp_creation_sent` (Boolean) : Message de création envoyé
- `x_whatsapp_creation_sent_date` (Datetime) : Date envoi message création

**Méthodes principales** :
- `create(vals_list)` : Surcharge pour envoyer un message à la création
- `_send_whatsapp_creation_notification()` : Envoie la notification de création
- `action_send_order_validation_whatsapp()` : Envoie les détails pour validation

---

## API et méthodes principales

### Configuration WhatsApp

#### `whatsapp.config.send_text_message()`

**Signature** :
```python
def send_text_message(self, to_phone, body_text, preview_url=False)
```

**Description** : Envoie un message texte simple.

**Paramètres** :
- `to_phone` (str) : Numéro de téléphone destinataire (format international)
- `body_text` (str) : Texte du message
- `preview_url` (bool) : Activer la prévisualisation des liens

**Retour** :
```python
{
    'success': bool,
    'message_id': str,  # ID WhatsApp
    'message_record': recordset,  # Enregistrement whatsapp.message
    'error': str or None
}
```

**Exemple** :
```python
config = env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
result = config.send_text_message(
    to_phone="+33612345678",
    body_text="Bonjour, votre commande est prête !"
)
```

#### `whatsapp.config.send_template_message()`

**Signature** :
```python
def send_template_message(self, to_phone, template_name, language_code, components=None)
```

**Description** : Envoie un message via un template WhatsApp approuvé.

**Paramètres** :
- `to_phone` (str) : Numéro de téléphone destinataire
- `template_name` (str) : Nom du template (tel que défini dans Meta)
- `language_code` (str) : Code langue (ex: "fr")
- `components` (list) : Liste des composants avec paramètres

**Format des components** :
```python
components = [
    {
        "type": "body",
        "parameters": [
            {"type": "text", "text": "Valeur 1"},
            {"type": "text", "text": "Valeur 2"}
        ]
    },
    {
        "type": "header",
        "parameters": [
            {
                "type": "image",
                "image": {"link": "https://example.com/image.jpg"}
            }
        ]
    }
]
```

**Exemple** :
```python
config = env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
result = config.send_template_message(
    to_phone="+33612345678",
    template_name="order_confirmation",
    language_code="fr",
    components=[
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": "Jean Dupont"},
                {"type": "text", "text": "SO001"}
            ]
        }
    ]
)
```

#### `whatsapp.config.send_interactive_message()`

**Signature** :
```python
def send_interactive_message(self, to_phone, body_text, buttons=None)
```

**Description** : Envoie un message avec boutons interactifs.

**Paramètres** :
- `to_phone` (str) : Numéro de téléphone destinataire
- `body_text` (str) : Texte du message
- `buttons` (list) : Liste des boutons

**Format des buttons** :
```python
buttons = [
    {
        "type": "reply",
        "reply": {
            "id": "btn_yes",
            "title": "Oui"
        }
    },
    {
        "type": "reply",
        "reply": {
            "id": "btn_no",
            "title": "Non"
        }
    }
]
```

**Exemple** :
```python
config = env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
result = config.send_interactive_message(
    to_phone="+33612345678",
    body_text="Souhaitez-vous valider cette commande ?",
    buttons=[
        {"type": "reply", "reply": {"id": "btn_validate", "title": "Valider"}},
        {"type": "reply", "reply": {"id": "btn_reject", "title": "Rejeter"}}
    ]
)
```

#### `whatsapp.config.send_text_to_partner()`

**Signature** :
```python
@api.model
def send_text_to_partner(self, partner_id, message_text, preview_url=False, config_id=None)
```

**Description** : Fonction utilitaire pour envoyer un message texte à un partenaire. Peut être appelée depuis n'importe quel module.

**Paramètres** :
- `partner_id` (int ou recordset) : ID ou objet partenaire
- `message_text` (str) : Texte du message
- `preview_url` (bool) : Prévisualisation des liens
- `config_id` (int, optionnel) : ID de la configuration (utilise la config active par défaut)

**Retour** : Même format que `send_text_message()`

**Exemple** :
```python
config = env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
result = config.send_text_to_partner(
    partner_id=partner.id,
    message_text="Bonjour, votre commande est prête !"
)
```

### Actions de boutons

#### `whatsapp.button.action.execute_action()`

**Signature** :
```python
def execute_action(self, message, contact=None)
```

**Description** : Exécute l'action définie pour un bouton.

**Paramètres** :
- `message` (recordset) : Message WhatsApp qui a déclenché l'action
- `contact` (recordset, optionnel) : Contact associé

**Retour** :
```python
{
    'success': bool,
    'message': str
}
```

**Types d'actions** :
- `send_message` : Envoie un message automatique
- `update_contact` : Met à jour un champ du contact
- `create_ticket` : Crée un ticket (nécessite module helpdesk)
- `update_status` : Met à jour le statut
- `custom_python` : Exécute du code Python personnalisé

**Exemple de code Python personnalisé** :
```python
# Variables disponibles : env, message, contact, button_id, self
if contact:
    # Mettre à jour le contact
    contact.write({'x_whatsapp_status': 'validated'})

# Chercher la commande associée
order = env['sale.order'].search([
    ('partner_id', '=', contact.id)
], limit=1)

if order:
    order.write({'state': 'sale'})
```

---

## Contrôleurs et Webhooks

### Webhook Controller

**Fichier** : `controllers/whatsapp_webhook.py`

**Route** : `/whatsapp/webhook/<int:config_id>`

**Méthode** : POST

**Description** : Reçoit les webhooks de WhatsApp (messages entrants, statuts, interactions).

**Fonctionnalités** :
1. **Vérification du webhook** (GET) : Meta vérifie l'URL avec un challenge
2. **Réception des messages** (POST) : Traite les messages entrants
3. **Statuts de messages** : Met à jour les statuts (sent, delivered, read, failed)
4. **Interactions** : Traite les clics sur les boutons

**Format des données reçues** :
```json
{
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "...",
                    "phone_number_id": "..."
                },
                "contacts": [...],
                "messages": [...],
                "statuses": [...]
            },
            "field": "messages"
        }]
    }]
}
```

**Traitement** :
- Crée des enregistrements `whatsapp.message` pour les messages entrants
- Met à jour les statuts des messages sortants
- Traite les interactions (boutons) et exécute les actions associées
- Crée ou met à jour les conversations

---

## Vues et interfaces

### Menus principaux

1. **WhatsApp > Configuration**
   - Configuration de l'API
   - Vérification des paramètres
   - Synchronisation des templates

2. **WhatsApp > Envoyer un message**
   - Wizard pour envoyer un message texte

3. **WhatsApp > Envoyer un template**
   - Wizard pour envoyer un template

4. **WhatsApp > Envoyer message au partenaire**
   - Wizard pour envoyer à un partenaire

5. **WhatsApp > Conversations**
   - Liste des conversations
   - Détails des messages

6. **WhatsApp > Messages**
   - Journal complet des messages
   - Détails et statuts

7. **WhatsApp > Templates**
   - Templates synchronisés
   - Statuts et détails

8. **WhatsApp > Actions de boutons**
   - Configuration des actions
   - Gestion des interactions

### Vues personnalisées

#### Formulaire partenaire (`res.partner`)
- Bouton "Envoyer WhatsApp" dans le header
- Visible uniquement si le partenaire a un numéro de téléphone

#### Formulaire commande (`sale.order`)
- Bouton "Envoyer validation WhatsApp" (via action serveur)
- Champs de suivi WhatsApp

---

## Sécurité

### Droits d'accès

**Fichier** : `security/ir.model.access.csv`

**Groupes** :
- `base.group_user` : Accès complet (lecture, écriture, création, suppression) pour tous les modèles

**Modèles protégés** :
- `whatsapp.config`
- `whatsapp.message`
- `whatsapp.conversation`
- `whatsapp.template`
- `whatsapp.send.message`
- `whatsapp.send.template`
- `whatsapp.send.interactive`
- `whatsapp.send.partner.message`
- `whatsapp.button.action`

### Webhook Security

- **Token de vérification** : `webhook_verify_token` pour valider les requêtes Meta
- **HTTPS requis** : Les webhooks doivent être en HTTPS
- **Validation des signatures** : Meta signe les requêtes (à implémenter si nécessaire)

---

## Intégrations

### 1. Intégration avec `sale.order`

**Fonctionnalités** :
- Envoi automatique de notification à la création d'une commande
- Envoi de validation avec boutons interactifs
- Suivi des validations/rejets via WhatsApp

**Champs ajoutés** :
- `x_whatsapp_creation_sent` : Message de création envoyé
- `x_whatsapp_validation_sent` : Validation envoyée
- `x_whatsapp_validated` : Validée via WhatsApp
- `x_whatsapp_rejected` : Rejetée via WhatsApp

**Méthodes** :
- `create()` : Surcharge pour notification automatique
- `_send_whatsapp_creation_notification()` : Envoie la notification
- `action_send_order_validation_whatsapp()` : Envoie pour validation

### 2. Intégration avec `res.partner`

**Fonctionnalités** :
- Bouton WhatsApp dans le formulaire partenaire
- Envoi direct depuis le partenaire

**Vue héritée** : `base.view_partner_form`

### 3. Utilisation depuis d'autres modules

**Fonction utilitaire** :
```python
config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
if config:
    result = config.send_text_to_partner(
        partner_id=partner.id,
        message_text="Votre message ici"
    )
```

---

## Configuration

### Configuration initiale

1. **Créer une configuration WhatsApp** :
   - Aller dans **WhatsApp > Configuration**
   - Créer une nouvelle configuration
   - Remplir :
     - Nom
     - Phone Number ID (depuis Meta)
     - Access Token (depuis Meta)
     - Webhook Verify Token (générer un token sécurisé)
     - Webhook URL (ex: `https://votre-domaine.com/whatsapp/webhook/1`)

2. **Configurer le webhook dans Meta** :
   - Aller dans Meta Business Suite
   - WhatsApp Manager → Configuration → Webhooks
   - Ajouter l'URL du webhook
   - Ajouter le token de vérification
   - S'abonner aux événements : `messages`, `message_status`

3. **Synchroniser les templates** :
   - Dans Odoo : **WhatsApp > Configuration**
   - Cliquer sur **"Synchroniser les templates"**

### Configuration des actions de boutons

1. **Créer une action** :
   - Aller dans **WhatsApp > Actions de boutons**
   - Créer une nouvelle action
   - Définir :
     - Nom
     - ID du bouton (doit correspondre à l'ID dans le template)
     - Type d'action
     - Paramètres selon le type

2. **Exemple d'action** :
   - Nom : "Valider commande"
   - ID bouton : `btn_validate_order`
   - Type : `custom_python`
   - Code Python : (voir exemples dans `data/whatsapp_order_validation_actions.xml`)

---

## Exemples d'utilisation

### Exemple 1 : Envoi simple depuis un autre module

```python
from odoo import models, fields, api

class MonModele(models.Model):
    _name = 'mon.modele'
    
    def action_envoyer_notification(self):
        config = self.env['whatsapp.config'].search([
            ('is_active', '=', True)
        ], limit=1)
        
        if config:
            result = config.send_text_to_partner(
                partner_id=self.partner_id.id,
                message_text=f"Bonjour {self.partner_id.name}, votre demande est prête !"
            )
            
            if result.get('success'):
                # Succès
                pass
            else:
                # Erreur
                _logger.error("Erreur envoi WhatsApp: %s", result.get('error'))
```

### Exemple 2 : Envoi de template avec paramètres

```python
config = env['whatsapp.config'].search([('is_active', '=', True)], limit=1)

components = [
    {
        "type": "body",
        "parameters": [
            {"type": "text", "text": "Jean Dupont"},
            {"type": "text", "text": "SO001"},
            {"type": "text", "text": "15000"}
        ]
    }
]

result = config.send_template_message(
    to_phone="+33612345678",
    template_name="order_confirmation",
    language_code="fr",
    components=components
)
```

### Exemple 3 : Message interactif avec boutons

```python
config = env['whatsapp.config'].search([('is_active', '=', True)], limit=1)

buttons = [
    {
        "type": "reply",
        "reply": {
            "id": "btn_yes",
            "title": "Oui"
        }
    },
    {
        "type": "reply",
        "reply": {
            "id": "btn_no",
            "title": "Non"
        }
    }
]

result = config.send_interactive_message(
    to_phone="+33612345678",
    body_text="Souhaitez-vous confirmer cette commande ?",
    buttons=buttons
)
```

### Exemple 4 : Action de bouton personnalisée

```python
# Dans whatsapp.button.action, type = custom_python
# Code Python :

# Variables disponibles : env, message, contact, button_id, self

# Chercher la commande associée
if message.content:
    # Le contenu peut contenir l'ID de la commande
    order_number = message.content.split()[-1]  # Exemple
    order = env['sale.order'].search([
        ('name', '=', order_number)
    ], limit=1)
    
    if order and button_id == 'btn_validate_order':
        order.write({
            'state': 'sale',
            'x_whatsapp_validated': True
        })
        
        # Envoyer une confirmation
        config = env['whatsapp.config'].search([
            ('is_active', '=', True)
        ], limit=1)
        
        if config and contact:
            config.send_text_to_partner(
                partner_id=contact.id,
                message_text="Votre commande a été validée avec succès !"
            )
```

### Exemple 5 : Notification automatique à la création

Le module envoie automatiquement une notification à la création d'une commande `sale.order`. Le message inclut :
- Nom du client
- Numéro de commande
- Type de commande (si disponible)
- Montant
- Type de crédit (si disponible)
- Message personnalisé selon le type

---

## Gestion des erreurs

### Codes d'erreur WhatsApp courants

- **131026** : Fenêtre de 24h expirée (utiliser un template)
- **131047** : Numéro de téléphone invalide
- **131048** : Template non trouvé
- **131051** : Paramètres de template invalides

### Gestion dans le code

Toutes les méthodes retournent un dictionnaire avec :
- `success` : Booléen indiquant le succès
- `error` : Message d'erreur si échec
- `message_id` : ID du message si succès
- `message_record` : Enregistrement créé

Les erreurs sont également loggées dans les logs Odoo.

---

## Limitations et bonnes pratiques

### Limitations

1. **Fenêtre de 24h** : Les messages texte simples ne peuvent être envoyés que si le client a écrit dans les 24h
2. **Templates** : Doivent être créés et approuvés dans Meta Business Suite
3. **Rate limiting** : WhatsApp limite le nombre de messages par seconde
4. **Webhook HTTPS** : Les webhooks doivent être en HTTPS

### Bonnes pratiques

1. **Utiliser des templates** pour les messages hors fenêtre de 24h
2. **Valider les numéros** avant l'envoi
3. **Gérer les erreurs** gracieusement
4. **Logger les actions** pour le débogage
5. **Tester avec des numéros de test** avant la production
6. **Respecter les politiques WhatsApp** (spam, contenu, etc.)

---

## Support et maintenance

### Logs

Les logs sont disponibles dans :
- **Paramètres > Technique > Logs**
- Rechercher : `whatsapp` ou `api_whatsapp`

### Débogage

1. Vérifier la configuration active
2. Vérifier les logs Odoo
3. Vérifier les logs Meta Business Suite
4. Tester avec l'outil "Vérifier les paramètres"
5. Vérifier le statut des templates

### Mise à jour

Pour mettre à jour le module :
1. Sauvegarder la base de données
2. Mettre à jour le module dans Odoo
3. Vérifier les migrations de données
4. Tester les fonctionnalités

---

## Conclusion

Ce module fournit une intégration complète de WhatsApp Business Cloud API avec Odoo, permettant :
- L'envoi et la réception de messages
- La gestion des templates
- Les interactions avec boutons
- L'intégration avec les modules Odoo existants
- Une API simple et réutilisable

Pour plus d'informations, consultez les guides spécifiques dans le répertoire du module.

