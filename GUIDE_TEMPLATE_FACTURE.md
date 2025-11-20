# Guide : Créer un template WhatsApp pour envoyer les factures avec bouton de téléchargement

## Vue d'ensemble

Ce guide explique comment créer un template WhatsApp dans Meta Business Suite qui permet d'envoyer les factures avec un bouton pour télécharger directement le PDF.

## Étape 1 : Créer le template dans Meta Business Suite

1. **Connectez-vous à Meta Business Suite**
   - Allez sur [business.facebook.com](https://business.facebook.com)
   - Sélectionnez votre compte WhatsApp Business

2. **Accédez aux templates**
   - Allez dans **WhatsApp Manager** → **Message Templates**
   - Cliquez sur **Create Template**

3. **Remplissez les informations de base**
   - **Category** : `UTILITY` (ou `MARKETING` selon votre cas)
   - **Template Name** : `invoice_with_download` (⚠️ **IMPORTANT** : ce nom exact doit être utilisé)
   - **Language** : `French (fr)` ou votre langue préférée

## Étape 2 : Définir le contenu du template

### Header (Optionnel)
- Vous pouvez laisser le header vide ou ajouter une image/document
- Pour ce cas, on peut laisser vide

### Body (Corps du message)

**Texte du template :**
```
Bonjour {{1}},

Votre facture {{2}} a été validée.

Montant total : {{3}}
Date : {{4}}

Merci de votre confiance !
```

**Paramètres :**
- `{{1}}` = Nom du partenaire
- `{{2}}` = Numéro de facture (ex: INV/2024/001)
- `{{3}}` = Montant total (ex: 15000 F CFA)
- `{{4}}` = Date de la facture (ex: 19/11/2024)

### Footer (Optionnel)
- Vous pouvez ajouter un footer si nécessaire

### Bouton URL

**Type de bouton** : `URL Button`

**Texte du bouton** : `Télécharger la facture` (ou `Download Invoice`)

**URL dynamique** : Le lien sera fourni dynamiquement par Odoo via les paramètres du template.

**⚠️ IMPORTANT** : Dans Meta Business Suite, vous devez définir le bouton comme "URL Button". L'URL sera passée dynamiquement via les paramètres du template lors de l'envoi.

**Configuration du bouton dans Meta** :
1. Ajoutez un bouton de type "URL Button"
2. Dans le champ URL, vous pouvez mettre un placeholder ou une URL de base (ex: `https://your-domain.com/invoice`)
3. Odoo remplacera cette URL par l'URL complète du PDF lors de l'envoi via les paramètres du template

**Note** : WhatsApp permet de passer des URLs dynamiques dans les boutons URL via les paramètres du template. L'URL sera fournie dans le composant `button` avec `sub_type: "url"` et `index: "0"` (pour le premier bouton URL).

## Étape 3 : Structure du template recommandée

### Option 1 : Template avec bouton URL (Recommandé)

**Nom du template** : `invoice_with_download`

**Body :**
```
Bonjour {{1}},

Votre facture {{2}} a été validée.

Montant total : {{3}}
Date : {{4}}

Cliquez sur le bouton ci-dessous pour télécharger votre facture.

Merci de votre confiance !
```

**Bouton :**
- Type : `URL Button`
- Texte : `Télécharger la facture`
- URL : `https://your-domain.com/invoice/{{5}}` (où {{5}} sera l'URL complète du PDF)

**⚠️ Note** : WhatsApp ne permet pas directement les URLs complètement dynamiques dans les boutons. Vous devrez peut-être utiliser une URL de redirection.

### Option 2 : Template simple avec lien dans le message

Si les boutons URL dynamiques ne fonctionnent pas, vous pouvez créer un template simple et Odoo ajoutera le lien dans le message.

**Nom du template** : `invoice_notification`

**Body :**
```
Bonjour {{1}},

Votre facture {{2}} a été validée.

Montant total : {{3}}
Date : {{4}}

{{5}}

Merci de votre confiance !
```

Où `{{5}}` sera le lien de téléchargement.

## Étape 4 : Soumettre le template pour approbation

1. Vérifiez que tous les champs sont remplis correctement
2. Cliquez sur **Submit** pour soumettre le template
3. Attendez l'approbation de Meta (généralement quelques heures à quelques jours)

## Étape 5 : Synchroniser le template dans Odoo

Une fois le template approuvé :

1. Dans Odoo, allez dans **WhatsApp > Configuration**
2. Cliquez sur **Synchroniser les templates**
3. Le template `invoice_with_download` devrait apparaître dans **WhatsApp > Templates**

## Étape 6 : Configuration dans Odoo

Le code Odoo est déjà configuré pour utiliser le template `invoice_with_download`. Si vous utilisez un nom différent, modifiez la ligne suivante dans `account_move_whatsapp.py` :

```python
template_name = "invoice_with_download"  # Changez ce nom si nécessaire
```

## Structure JSON du template (pour référence)

Lors de l'envoi, Odoo génère automatiquement cette structure :

```json
{
  "name": "invoice_with_download",
  "language": {
    "code": "fr"
  },
  "components": [
    {
      "type": "body",
      "parameters": [
        {"type": "text", "text": "Nom du partenaire"},
        {"type": "text", "text": "INV/2024/001"},
        {"type": "text", "text": "15000 F CFA"},
        {"type": "text", "text": "19/11/2024"}
      ]
    },
    {
      "type": "button",
      "sub_type": "url",
      "index": "0",
      "parameters": [
        {
          "type": "text",
          "text": "https://your-domain.com/web/content/123?download=true"
        }
      ]
    }
  ]
}
```

## Dépannage

### Le template n'est pas trouvé
- Vérifiez que le template est approuvé dans Meta Business Suite
- Vérifiez que le nom du template correspond exactement (sensible à la casse)
- Synchronisez les templates dans Odoo

### Le bouton ne fonctionne pas
- Vérifiez que l'URL est accessible publiquement
- Vérifiez que l'URL commence par `https://`
- Assurez-vous que le bouton est de type "URL Button" dans le template

### Fallback automatique
Si le template n'est pas trouvé ou si une erreur survient, Odoo utilisera automatiquement :
1. Envoi direct du PDF via `send_document_message`
2. Si cela échoue, envoi d'un message texte avec le lien

## Exemple de template approuvé

**Nom** : `invoice_with_download`
**Catégorie** : `UTILITY`
**Langue** : `French (fr)`

**Body** :
```
Bonjour {{1}},

Votre facture {{2}} a été validée.

Montant total : {{3}}
Date : {{4}}

Merci de votre confiance !
```

**Bouton** :
- Type : URL Button
- Texte : Télécharger la facture
- URL : (sera fournie dynamiquement par Odoo)

