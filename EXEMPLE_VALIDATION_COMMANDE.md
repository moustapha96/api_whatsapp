# Exemple : Validation de commande via WhatsApp

## Scénario

Envoyer les détails d'une commande (nom client, montant) au partenaire via WhatsApp avec des boutons pour valider ou rejeter la commande, puis mettre à jour l'état de la commande selon la réponse.

---

## Étape 1 : Créer le template dans Meta Business Suite

### Configuration du template

1. Allez dans **Meta Business Suite** → **WhatsApp Manager** → **Message Templates**
2. Cliquez sur **"Create Template"**
3. Remplissez :

**Template Name** : `order_validation`

**Category** : `UTILITY`

**Language** : `French (fr)`

**Type** : `Interactive` → `Button`

**Body** :
```
Bonjour ,

Détails de votre commande :

- Numéro : {{1}}

- Montant : {{2}} F CFA

Souhaitez-vous valider cette commande ?
```

**Buttons** :
- **Bouton 1** :
  - ID : `btn_validate_order`
  - Titre : "Valider"
  
- **Bouton 2** :
  - ID : `btn_reject_order`
  - Titre : "Rejeter"

**Note** : 
- {{1}} sera remplacé par le numéro de commande (ex: SO001)
- {{2}} sera remplacé par le montant en F CFA (ex: 15000)

4. **Soumettez** et attendez l'approbation

---

## Étape 2 : Créer les actions de boutons dans Odoo

### Action pour "Valider"

1. Allez dans **WhatsApp > Actions de boutons**
2. Créez une nouvelle action :

**Nom** : Validation de commande

**ID du bouton** : `btn_validate_order`

**Type d'action** : Code Python

**Code Python** :
```python
# Récupère la commande associée au message
order = env['sale.order'].search([
    ('partner_id.phone', '=', message.phone.replace(' ', '').replace('-', '').replace('.', ''))
], order='create_date desc', limit=1)

if order:
    # Met à jour l'état de la commande
    order.write({
        'state': 'sale',  # État "Confirmé"
        'x_whatsapp_validated': True,  # Champ personnalisé si nécessaire
    })
    
    # Envoie un message de confirmation
    if message.config_id:
        message.config_id.send_text_message(
            message.phone,
            f"✅ Commande {order.name} validée avec succès ! Merci."
        )
    
    # Log
    _logger.info("Commande %s validée via WhatsApp par %s", order.name, message.phone)
else:
    _logger.warning("Aucune commande trouvée pour le numéro %s", message.phone)
```

### Action pour "Rejeter"

1. Créez une autre action :

**Nom** : Rejet de commande

**ID du bouton** : `btn_reject_order`

**Type d'action** : Code Python

**Code Python** :
```python
# Récupère la commande associée au message
order = env['sale.order'].search([
    ('partner_id.phone', '=', message.phone.replace(' ', '').replace('-', '').replace('.', ''))
], order='create_date desc', limit=1)

if order:
    # Met à jour l'état de la commande
    order.write({
        'state': 'cancel',  # État "Annulé"
        'x_whatsapp_rejected': True,  # Champ personnalisé si nécessaire
    })
    
    # Envoie un message de confirmation
    if message.config_id:
        message.config_id.send_text_message(
            message.phone,
            f"❌ Commande {order.name} rejetée. N'hésitez pas à nous contacter si vous avez des questions."
        )
    
    # Log
    _logger.info("Commande %s rejetée via WhatsApp par %s", order.name, message.phone)
else:
    _logger.warning("Aucune commande trouvée pour le numéro %s", message.phone)
```

---

## Étape 3 : Créer une méthode pour envoyer la commande

Créez un fichier `models/sale_order_whatsapp.py` :

```python
# whatsapp_business_api/models/sale_order_whatsapp.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_send_order_validation_whatsapp(self):
        """Envoie les détails de la commande via WhatsApp pour validation"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            raise ValidationError(_("Aucun partenaire associé à cette commande."))
        
        if not self.partner_id.phone:
            raise ValidationError(_("Le partenaire n'a pas de numéro de téléphone."))
        
        # Récupère la configuration WhatsApp active
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        # Nettoie le numéro de téléphone
        phone = config._validate_phone_number(self.partner_id.phone)
        
        # Prépare les paramètres du template
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": self.partner_id.name or "Client"},
                    {"type": "text", "text": self.name},
                    {"type": "text", "text": f"{self.amount_total:.2f}"},
                    {"type": "text", "text": self.date_order.strftime("%d/%m/%Y") if self.date_order else datetime.now().strftime("%d/%m/%Y")}
                ]
            }
        ]
        
        try:
            # Envoie le template
            config.send_template_message(
                to_phone=phone,
                template_name="order_validation",
                language_code="fr",
                components=components
            )
            
            # Met à jour la commande pour indiquer qu'un message a été envoyé
            self.write({
                'x_whatsapp_validation_sent': True,
                'x_whatsapp_validation_sent_date': fields.Datetime.now()
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Message de validation envoyé à %s') % self.partner_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi du message de validation")
            raise ValidationError(_("Erreur lors de l'envoi du message : %s") % str(e))
```

---

## Étape 4 : Ajouter des champs personnalisés à la commande (optionnel)

Si vous voulez suivre l'état de validation WhatsApp, ajoutez ces champs dans `models/sale_order_whatsapp.py` :

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_whatsapp_validation_sent = fields.Boolean(
        string="Validation WhatsApp envoyée",
        default=False
    )
    
    x_whatsapp_validation_sent_date = fields.Datetime(
        string="Date envoi validation WhatsApp"
    )
    
    x_whatsapp_validated = fields.Boolean(
        string="Validée via WhatsApp",
        default=False
    )
    
    x_whatsapp_rejected = fields.Boolean(
        string="Rejetée via WhatsApp",
        default=False
    )
```

---

## Étape 5 : Ajouter un bouton dans la vue de commande

Créez `views/sale_order_whatsapp_views.xml` :

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_order_form_whatsapp" model="ir.ui.view">
        <field name="name">sale.order.form.whatsapp</field>
        <field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <xpath expr="//header" position="inside">
                <button name="action_send_order_validation_whatsapp"
                        type="object"
                        string="Envoyer validation WhatsApp"
                        class="btn-primary"
                        icon="fa-whatsapp"
                        attrs="{'invisible': [('state', 'in', ['cancel', 'done'])]}"/>
            </xpath>
        </field>
    </record>
</odoo>
```

---

## Étape 6 : Mettre à jour le manifest

Ajoutez dans `__manifest__.py` :

```python
"depends": ["base", "contacts", "sale"],  # Ajoutez "sale" si pas déjà présent

"data": [
    # ... autres fichiers
    "views/sale_order_whatsapp_views.xml",
],
```

---

## Utilisation

### 1. Synchroniser le template

1. Allez dans **WhatsApp > Configuration**
2. Cliquez sur **"Synchroniser les templates"**
3. Vérifiez que `order_validation` apparaît

### 2. Créer les actions de boutons

1. Allez dans **WhatsApp > Actions de boutons**
2. Créez les deux actions (`btn_validate_order` et `btn_reject_order`)
3. Copiez-collez les codes Python fournis

### 3. Envoyer la validation

1. Ouvrez une commande de vente
2. Cliquez sur **"Envoyer validation WhatsApp"**
3. Le message est envoyé au partenaire avec les détails

### 4. Le partenaire répond

- Si le partenaire clique sur **"Valider"** :
  - La commande passe à l'état "Confirmé" (sale)
  - Un message de confirmation est envoyé
  
- Si le partenaire clique sur **"Rejeter"** :
  - La commande passe à l'état "Annulé" (cancel)
  - Un message de confirmation est envoyé

---

## Code complet amélioré (avec recherche par numéro de commande)

Si vous voulez être plus précis dans la recherche de la commande, modifiez les actions de boutons :

```python
# Pour btn_validate_order
import re

# Extrait le numéro de commande du message précédent
# Cherche dans les messages précédents du même numéro
previous_messages = env['whatsapp.message'].search([
    ('phone', '=', message.phone),
    ('direction', '=', 'out'),
    ('template_name', '=', 'order_validation'),
    ('create_date', '<', message.create_date)
], order='create_date desc', limit=1)

if previous_messages and previous_messages.template_components:
    import json
    components = json.loads(previous_messages.template_components)
    if components and components[0].get('parameters'):
        order_number = components[0]['parameters'][1].get('text', '')
        
        # Cherche la commande par numéro
        order = env['sale.order'].search([
            ('name', '=', order_number)
        ], limit=1)
        
        if order:
            order.write({'state': 'sale'})
            message.config_id.send_text_message(
                message.phone,
                f"✅ Commande {order.name} validée avec succès !"
            )
```

---

## Résumé

1. ✅ **Template créé** dans Meta : `order_validation` avec 2 boutons
2. ✅ **Actions créées** dans Odoo : `btn_validate_order` et `btn_reject_order`
3. ✅ **Méthode ajoutée** : `action_send_order_validation_whatsapp()` sur sale.order
4. ✅ **Bouton ajouté** dans la vue de commande
5. ✅ **État mis à jour** selon la réponse du partenaire

Le système est maintenant opérationnel ! 🚀

