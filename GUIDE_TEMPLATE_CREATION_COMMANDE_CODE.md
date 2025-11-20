# Code pour utiliser un template WhatsApp au lieu d'un message texte

## Vue d'ensemble

Ce guide explique comment modifier le code pour utiliser un template WhatsApp approuvé au lieu d'un message texte simple. Cela permet d'envoyer des messages même hors de la fenêtre de 24h.

## Modification du code

### Fichier à modifier

`models/sale_order_whatsapp.py`

### Méthode à modifier

`_send_whatsapp_creation_notification()`

## Code complet modifié

Remplacez la méthode `_send_whatsapp_creation_notification()` par ce code :

```python
def _send_whatsapp_creation_notification(self):
    """Envoie un message WhatsApp pour confirmer la création de la commande"""
    self.ensure_one()
    
    # Vérifie qu'il y a un partenaire avec un numéro de téléphone
    if not self.partner_id:
        return
    
    # Vérifie si le partenaire a un numéro de téléphone
    phone = self.partner_id.phone or self.partner_id.mobile
    if not phone:
        _logger.info("Pas de numéro de téléphone pour le partenaire %s, message WhatsApp non envoyé", self.partner_id.name)
        return
    
    # Vérifie si le message a déjà été envoyé (évite les doublons)
    if self.x_whatsapp_creation_sent:
        return
    
    # Récupère la configuration WhatsApp active
    config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
    if not config:
        _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer le message de création")
        return
    
    try:
        # Nettoie le numéro de téléphone
        phone = config._validate_phone_number(phone)
        
        # Prépare les traductions pour le type de vente
        type_sale_translations = {
            'order': 'Commande',
            'preorder': 'Précommande',
            'creditorder': 'Commande crédit'
        }
        
        # Détermine le type de vente à afficher
        type_sale_display = 'Commande'  # Par défaut
        if hasattr(self, 'type_sale') and self.type_sale:
            type_sale_display = type_sale_translations.get(self.type_sale, self.type_sale)
        
        # Prépare les paramètres du template
        # Template : order_creation_confirmation
        # Paramètres : {{1}} = Nom client, {{2}} = Numéro commande, {{3}} = Type, {{4}} = Montant
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": self.partner_id.name or "Client"},  # {{1}}
                    {"type": "text", "text": self.name},  # {{2}}
                    {"type": "text", "text": type_sale_display},  # {{3}}
                    {"type": "text", "text": f"{self.amount_total:.0f}" if self.amount_total else "0"}  # {{4}}
                ]
            }
        ]
        
        # Envoie le template
        result = config.send_template_message(
            to_phone=phone,
            template_name="order_creation_confirmation",
            language_code="fr",
            components=components
        )
        
        # Met à jour la commande pour indiquer qu'un message a été envoyé
        if result.get('success') or result.get('message_record'):
            self.write({
                'x_whatsapp_creation_sent': True,
                'x_whatsapp_creation_sent_date': fields.Datetime.now()
            })
            _logger.info("Message WhatsApp de création envoyé avec succès pour la commande %s", self.name)
        else:
            _logger.warning("Échec de l'envoi du message WhatsApp pour la commande %s: %s", self.name, result.get('error', 'Erreur inconnue'))
            
    except Exception as e:
        _logger.exception("Erreur lors de l'envoi du message WhatsApp de création pour la commande %s", self.name)
        # Ne lève pas d'exception pour ne pas bloquer la création de la commande
```

## Template WhatsApp à créer

### Nom du template
`order_creation_confirmation`

### Catégorie
`UTILITY`

### Langue
`French (fr)`

### Type
`Text`

### Body du template
```
Bonjour {{1}},

Votre commande numéro {{2}} a été créée avec succès.

Type : {{3}}
Montant : {{4}} F CFA

Votre commande sera traitée dans les plus brefs délais.
```

### Paramètres
- `{{1}}` = Nom du client
- `{{2}}` = Numéro de commande
- `{{3}}` = Type de commande (Commande, Précommande, Commande crédit)
- `{{4}}` = Montant en F CFA

## Version avec type de crédit (optionnel)

Si vous voulez inclure le type de crédit, vous pouvez créer un template avec 5 paramètres :

### Body du template (version complète)
```
Bonjour {{1}},

Votre commande numéro {{2}} a été créée avec succès.

Type : {{3}}
Montant : {{4}} F CFA
{{5}}

Votre commande est actuellement en attente de validation.
```

### Code modifié pour inclure le type de crédit

```python
# Prépare les paramètres du template
parameters = [
    {"type": "text", "text": self.partner_id.name or "Client"},  # {{1}}
    {"type": "text", "text": self.name},  # {{2}}
    {"type": "text", "text": type_sale_display},  # {{3}}
    {"type": "text", "text": f"{self.amount_total:.0f}" if self.amount_total else "0"}  # {{4}}
]

# Ajoute le type de crédit si disponible
if hasattr(self, 'credit_type') and self.credit_type:
    try:
        credit_type_field = self._fields.get('credit_type')
        if credit_type_field and credit_type_field.selection:
            credit_type_label = dict(credit_type_field.selection).get(self.credit_type, self.credit_type)
        else:
            credit_type_label = self.credit_type
        parameters.append({"type": "text", "text": f"Type de crédit : {credit_type_label}"})  # {{5}}
    except Exception:
        parameters.append({"type": "text", "text": f"Type de crédit : {self.credit_type}"})  # {{5}}
else:
    parameters.append({"type": "text", "text": ""})  # {{5}} vide si pas de crédit

components = [
    {
        "type": "body",
        "parameters": parameters
    }
]
```

## Avantages de cette approche

✅ **Envoi hors fenêtre de 24h** : Vous pouvez envoyer même si le client ne vous a pas écrit récemment

✅ **Messages structurés** : Format professionnel et cohérent

✅ **Approbation Meta** : Les templates sont vérifiés par Meta, ce qui améliore la délivrabilité

✅ **Personnalisation** : Variables dynamiques pour chaque client

## Comparaison : Message texte vs Template

| Caractéristique | Message texte | Template |
|----------------|---------------|----------|
| Fenêtre de 24h | ❌ Nécessaire | ✅ Non nécessaire |
| Approbation Meta | ❌ Non requise | ✅ Requise |
| Personnalisation | ✅ Flexible | ✅ Structurée |
| Délivrabilité | ⚠️ Moyenne | ✅ Excellente |
| Temps de mise en place | ✅ Immédiat | ⚠️ Quelques jours |

## Instructions

1. **Créez le template** dans Meta Business Suite (voir `GUIDE_TEMPLATE_CREATION_COMMANDE.md`)
2. **Attendez l'approbation** (généralement quelques heures à quelques jours)
3. **Synchronisez** dans Odoo : WhatsApp > Configuration → "Synchroniser les templates"
4. **Remplacez le code** dans `models/sale_order_whatsapp.py` avec le code ci-dessus
5. **Redémarrez Odoo** ou mettez à jour le module
6. **Testez** en créant une nouvelle commande

## Dépannage

### Le template n'est pas trouvé

- Vérifiez que le nom est exactement `order_creation_confirmation`
- Vérifiez que le template est approuvé dans Meta
- Synchronisez les templates dans Odoo

### Erreur lors de l'envoi

- Vérifiez les logs Odoo pour voir l'erreur exacte
- Vérifiez que tous les paramètres sont fournis
- Vérifiez que le numéro de téléphone est valide

---

**Note** : Le code actuel utilise `send_text_to_partner` (message texte simple). Pour utiliser un template, remplacez-le par `send_template_message` comme montré ci-dessus.

