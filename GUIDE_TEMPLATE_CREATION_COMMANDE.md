# Guide : Créer un template WhatsApp pour la confirmation de création de commande

## Vue d'ensemble

Ce guide vous explique comment créer un template WhatsApp dans Meta Business Suite pour envoyer automatiquement une confirmation de création de commande à vos clients.

## Étape 1 : Accéder à Meta Business Suite

1. Allez sur [business.facebook.com](https://business.facebook.com)
2. Connectez-vous avec votre compte Meta Business
3. Sélectionnez votre compte WhatsApp Business
4. Allez dans **WhatsApp Manager** → **Message Templates**

## Étape 2 : Créer le template

### 2.1 Informations de base

Cliquez sur **"Create Template"** et remplissez :

**Template Name** : `order_creation_confirmation`

> ⚠️ **Important** : Le nom doit être exactement `order_creation_confirmation` pour que le module Odoo puisse l'utiliser.

**Category** : `UTILITY`

> 💡 **Note** : La catégorie UTILITY est généralement approuvée plus rapidement que MARKETING.

**Language** : `French (fr)`

**Type** : `Text` (Message texte simple)

### 2.2 Contenu du template

#### Option 1 : Template simple (sans paramètres)

Si vous voulez un message fixe sans variables dynamiques :

**Body** :
```
Bonjour,

Votre commande a été créée avec succès.

Merci de votre confiance !
```

#### Option 2 : Template avec paramètres (recommandé)

Si vous voulez personnaliser le message avec des informations dynamiques :

**Body** :
```
Bonjour {{1}},

Votre commande numéro {{2}} a été créée avec succès.

Type : {{3}}
Montant : {{4}} F CFA

Votre commande sera traitée dans les plus brefs délais.
```

**Paramètres** :
- `{{1}}` = Nom du client
- `{{2}}` = Numéro de commande
- `{{3}}` = Type de commande (Commande, Précommande, Commande crédit)
- `{{4}}` = Montant en F CFA

#### Option 3 : Template complet avec type de crédit

Si vous voulez inclure le type de crédit pour les commandes à crédit :

**Body** :
```
Bonjour {{1}},

Votre commande numéro {{2}} a été créée avec succès.

Type : {{3}}
Montant : {{4}} F CFA
{{5}}

Votre commande est actuellement en attente de validation.
```

**Paramètres** :
- `{{1}}` = Nom du client
- `{{2}}` = Numéro de commande
- `{{3}}` = Type de commande
- `{{4}}` = Montant en F CFA
- `{{5}}` = Type de crédit (optionnel, vide si pas de crédit)

### 2.3 Soumettre le template

1. Vérifiez que toutes les informations sont correctes
2. Cliquez sur **"Submit"** ou **"Soumettre"**
3. Attendez l'approbation (généralement quelques heures à quelques jours)

## Étape 3 : Synchroniser le template dans Odoo

Une fois le template approuvé par Meta :

1. Dans Odoo : **WhatsApp > Configuration**
2. Cliquez sur **"Synchroniser les templates"**
3. Le template `order_creation_confirmation` apparaîtra dans **WhatsApp > Templates**

## Étape 4 : Adapter le code Odoo (si nécessaire)

### Option A : Utiliser le template avec paramètres

Si vous avez créé un template avec paramètres, vous devez modifier le code dans `models/sale_order_whatsapp.py` pour utiliser `send_template_message` au lieu de `send_text_message`.

**Exemple de modification** :

```python
# Dans la méthode _send_whatsapp_creation_notification()

# Au lieu de :
result = config.send_text_to_partner(
    partner_id=self.partner_id.id,
    message_text=message
)

# Utilisez :
components = [
    {
        "type": "body",
        "parameters": [
            {"type": "text", "text": self.partner_id.name},  # {{1}}
            {"type": "text", "text": self.name},  # {{2}}
            {"type": "text", "text": type_sale_display},  # {{3}}
            {"type": "text", "text": f"{self.amount_total:.0f}"}  # {{4}}
        ]
    }
]

result = config.send_template_message(
    to_phone=phone,
    template_name="order_creation_confirmation",
    language_code="fr",
    components=components
)
```

### Option B : Garder le message texte simple (actuel)

Le code actuel utilise `send_text_to_partner` qui envoie un message texte simple. Cela fonctionne mais est soumis à la fenêtre de 24h.

**Avantage du template** : Vous pouvez envoyer même hors de la fenêtre de 24h.

## Exemples de messages selon le type de commande

### Commande normale (order)
```
Bonjour Jean Dupont,

Votre commande numéro SO001 a été créée avec succès.
Type : Commande
Montant : 15000 F CFA

Votre commande sera traitée dans les plus brefs délais.
```

### Précommande (preorder)
```
Bonjour Marie Martin,

Votre commande numéro SO002 a été créée avec succès.
Type : Précommande
Montant : 25000 F CFA

Votre précommande a été enregistrée et sera traitée selon les délais convenus.
```

### Commande crédit (creditorder)
```
Bonjour Pierre Sarr,

Votre commande numéro SO003 a été créée avec succès.
Type : Commande crédit
Montant : 50000 F CFA

Type de crédit : Crédit Direct

Votre commande est actuellement en attente de validation.
```

## Avantages d'utiliser un template

✅ **Envoi hors fenêtre de 24h** : Vous pouvez envoyer même si le client ne vous a pas écrit récemment

✅ **Messages structurés** : Format professionnel et cohérent

✅ **Approbation Meta** : Les templates sont vérifiés par Meta, ce qui améliore la délivrabilité

✅ **Personnalisation** : Variables dynamiques pour chaque client

## Dépannage

### Le template n'apparaît pas dans Odoo

1. Vérifiez que le template est **approuvé** dans Meta Business Suite
2. Vérifiez que le **nom du template** est exactement `order_creation_confirmation`
3. Cliquez sur **"Synchroniser les templates"** dans Odoo
4. Vérifiez les logs Odoo pour voir les erreurs éventuelles

### Le message n'est pas envoyé

1. Vérifiez que le partenaire a un **numéro de téléphone** valide
2. Vérifiez qu'une **configuration WhatsApp active** existe
3. Vérifiez les **logs Odoo** pour voir les erreurs
4. Vérifiez que le template est bien **approuvé** et **synchronisé**

### Erreur "Template not found"

1. Vérifiez que le nom du template dans Meta est exactement `order_creation_confirmation`
2. Vérifiez que le template est dans la langue `fr` (French)
3. Synchronisez les templates dans Odoo

## Configuration recommandée

Pour une meilleure expérience, nous recommandons :

1. **Créer le template avec paramètres** pour plus de flexibilité
2. **Utiliser la catégorie UTILITY** pour une approbation plus rapide
3. **Tester avec un numéro de test** avant de l'utiliser en production
4. **Garder le message simple et clair** pour une meilleure compréhension

## Support

Pour toute question ou problème :
- Consultez les logs Odoo : **Paramètres > Technique > Logs**
- Vérifiez le statut du template dans Meta Business Suite
- Contactez le support technique si nécessaire

---

**Note** : Le code actuel utilise `send_text_to_partner` qui envoie un message texte simple. Si vous voulez utiliser un template WhatsApp approuvé (pour envoyer hors de la fenêtre de 24h), vous devrez modifier le code comme indiqué dans l'Option A ci-dessus.

