# Guide complet : Création de templates WhatsApp

## Vue d'ensemble

Les templates WhatsApp permettent d'envoyer des messages à tout moment, même hors de la fenêtre de 24h. Ils doivent être créés et approuvés dans Meta Business Suite avant d'être utilisés.

## Accès à Meta Business Suite

1. Allez sur [business.facebook.com](https://business.facebook.com)
2. Connectez-vous avec votre compte Facebook Business
3. Sélectionnez votre compte WhatsApp Business
4. Allez dans **WhatsApp Manager** → **Message Templates**

## Types de templates disponibles

### 1. Template Texte (Text)

**Utilisation** : Messages texte simples avec ou sans paramètres

**Étapes de création** :

1. Cliquez sur **"Create Template"**
2. Sélectionnez **"Text"**
3. Remplissez :
   - **Template Name** : `simple_text_message` (minuscules, sans espaces)
   - **Category** : `UTILITY` (recommandé) ou `MARKETING`
   - **Language** : `French (fr)` ou votre langue
   - **Message** : Votre texte

**Exemple de template simple** :
```
Bonjour,

Ceci est un message simple que vous pouvez envoyer à tout moment.

Merci.
```

**Exemple avec paramètres** :
```
Bonjour {{1}},

Votre commande {{2}} est prête. Montant : {{3}} €.

Merci de votre confiance.
```

**Règles** :
- Maximum 1024 caractères
- Paramètres : `{{1}}`, `{{2}}`, etc. (jusqu'à 10)
- Pas de liens URL dans le texte (utilisez un template avec bouton)

---

### 2. Template Image (Image)

**Utilisation** : Messages avec image

**Étapes de création** :

1. Cliquez sur **"Create Template"**
2. Sélectionnez **"Image"**
3. Remplissez :
   - **Template Name** : `image_notification`
   - **Category** : `UTILITY` ou `MARKETING`
   - **Language** : `French (fr)`
   - **Upload Image** : Téléchargez votre image (max 5MB)
   - **Caption** (optionnel) : Légende sous l'image

**Exemple de légende avec paramètres** :
```
Bonjour {{1}},

Voici votre facture pour la commande {{2}}.
```

**Règles** :
- Formats acceptés : JPG, PNG, WEBP
- Taille max : 5MB
- Dimensions recommandées : 800x800px (carré) ou 1200x675px (paysage)
- Légende : Maximum 1024 caractères
- Paramètres possibles dans la légende

---

### 3. Template Vidéo (Video)

**Utilisation** : Messages avec vidéo

**Étapes de création** :

1. Cliquez sur **"Create Template"**
2. Sélectionnez **"Video"**
3. Remplissez :
   - **Template Name** : `video_tutorial`
   - **Category** : `UTILITY` ou `MARKETING`
   - **Language** : `French (fr)`
   - **Upload Video** : Téléchargez votre vidéo
   - **Caption** (optionnel) : Légende

**Règles** :
- Formats acceptés : MP4, 3GP
- Taille max : 16MB
- Durée max : 60 secondes
- Légende : Maximum 1024 caractères

---

### 4. Template Document (Document)

**Utilisation** : Envoi de documents (PDF, etc.)

**Étapes de création** :

1. Cliquez sur **"Create Template"**
2. Sélectionnez **"Document"**
3. Remplissez :
   - **Template Name** : `send_invoice`
   - **Category** : `UTILITY`
   - **Language** : `French (fr)`
   - **Upload Document** : Téléchargez votre document
   - **Caption** (optionnel) : Description

**Règles** :
- Formats acceptés : PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX
- Taille max : 100MB
- Légende : Maximum 1024 caractères

---

### 5. Template avec Boutons (Interactive)

**Utilisation** : Messages avec boutons interactifs

**Étapes de création** :

1. Cliquez sur **"Create Template"**
2. Sélectionnez **"Interactive"**
3. Choisissez le type :
   - **Button** : Jusqu'à 3 boutons de réponse rapide
   - **List** : Liste déroulante (jusqu'à 10 options)

**Exemple avec boutons** :

**Template Name** : `order_confirmation_buttons`

**Header** (optionnel) : Image ou texte
**Body** :
```
Votre commande {{1}} est prête !

Que souhaitez-vous faire ?
```

**Buttons** :
- Bouton 1 : ID = `btn_track`, Titre = "Suivre la commande"
- Bouton 2 : ID = `btn_contact`, Titre = "Contacter le support"
- Bouton 3 : ID = `btn_feedback`, Titre = "Laisser un avis"

**Règles** :
- Maximum 3 boutons pour type "Button"
- Maximum 10 options pour type "List"
- Titre bouton : Maximum 20 caractères
- ID bouton : Maximum 256 caractères (utilisez des underscores)

---

### 6. Template Localisation (Location)

**Utilisation** : Envoi de coordonnées GPS

**Étapes de création** :

1. Cliquez sur **"Create Template"**
2. Sélectionnez **"Location"**
3. Remplissez :
   - **Template Name** : `send_location`
   - **Category** : `UTILITY`
   - **Language** : `French (fr)`
   - **Body** : Message accompagnant la localisation

**Exemple** :
```
Bonjour {{1}},

Voici l'emplacement de notre magasin :

{{2}}
```

**Règles** :
- Les coordonnées sont envoyées via l'API, pas dans le template
- Le template contient juste le texte

---

## Catégories de templates

### UTILITY (Recommandé pour débuter)

**Utilisation** : Messages transactionnels, notifications, confirmations

**Avantages** :
- ✅ Validation généralement rapide (quelques heures)
- ✅ Moins de restrictions
- ✅ Idéal pour les confirmations de commande, factures, rendez-vous

**Exemples** :
- Confirmation de commande
- Envoi de facture
- Rappel de rendez-vous
- Notification de livraison

### MARKETING

**Utilisation** : Messages promotionnels, publicités

**Restrictions** :
- ⚠️ Validation plus stricte
- ⚠️ Peut prendre plusieurs jours
- ⚠️ Doit respecter les politiques publicitaires de Meta

**Exemples** :
- Offres promotionnelles
- Nouveaux produits
- Événements

### AUTHENTICATION

**Utilisation** : Codes de vérification, OTP

**Restrictions** :
- ⚠️ Réservé aux codes de sécurité
- ⚠️ Format très strict

**Exemples** :
- Code de vérification
- Code OTP
- Code d'accès temporaire

---

## Règles générales pour tous les templates

### Nom du template

- ✅ Utilisez des minuscules uniquement
- ✅ Pas d'espaces (utilisez des underscores `_`)
- ✅ Pas de caractères spéciaux (sauf `_`)
- ✅ Maximum 512 caractères
- ✅ Exemples valides : `simple_message`, `order_confirmation`, `send_invoice_2024`

### Paramètres

- Format : `{{1}}`, `{{2}}`, `{{3}}`, etc.
- Maximum 10 paramètres par template
- Les paramètres sont remplacés par des valeurs dynamiques lors de l'envoi
- Exemple : `Bonjour {{1}}, votre commande {{2}} est prête.`

### Langue

- Choisissez la langue principale du template
- Vous pouvez créer plusieurs versions du même template dans différentes langues
- Format : `fr`, `en`, `fr_FR`, `en_US`, etc.

---

## Processus de validation

### 1. Création du template

1. Remplissez tous les champs requis
2. Vérifiez l'aperçu
3. Cliquez sur **"Submit"**

### 2. Statuts possibles

- **PENDING** : En attente de validation (quelques heures à quelques jours)
- **APPROVED** : Approuvé, prêt à être utilisé ✅
- **REJECTED** : Rejeté (consultez les raisons et corrigez)
- **DISABLED** : Désactivé (peut être réactivé)

### 3. Si le template est rejeté

1. Consultez les raisons dans Meta Business Suite
2. Corrigez les problèmes mentionnés
3. Créez un nouveau template avec les corrections
4. Soumettez à nouveau

**Raisons courantes de rejet** :
- Contenu non conforme aux politiques
- Format incorrect
- Paramètres mal utilisés
- Catégorie inappropriée

---

## Synchronisation dans Odoo

Une fois le template approuvé dans Meta :

1. Allez dans **WhatsApp > Configuration**
2. Cliquez sur **"Synchroniser les templates"**
3. Les templates approuvés apparaîtront dans **WhatsApp > Templates**

**Note** : Seuls les templates avec le statut **APPROVED** seront synchronisés.

---

## Utilisation dans Odoo

### Via l'interface

1. Allez dans **WhatsApp > Envoyer un template**
2. Sélectionnez votre template
3. Remplissez les paramètres si nécessaire (format JSON)
4. Envoyez

### Via code Python

```python
config = env['whatsapp.config'].get_active_config()

# Template simple (sans paramètres)
config.send_template_message(
    to_phone="+33612345678",
    template_name="simple_text_message",
    language_code="fr",
    components=None
)

# Template avec paramètres
config.send_template_message(
    to_phone="+33612345678",
    template_name="order_confirmation",
    language_code="fr",
    components=[
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": "Jean Dupont"},
                {"type": "text", "text": "CMD-2024-001"},
                {"type": "text", "text": "150.00"}
            ]
        }
    ]
)
```

---

## Exemples de templates complets

### Exemple 1 : Confirmation de commande (Texte avec paramètres)

**Template Name** : `order_confirmation`

**Category** : UTILITY

**Language** : French (fr)

**Message** :
```
Bonjour {{1}},

Votre commande {{2}} a été confirmée.

Montant total : {{3}} €
Date de livraison prévue : {{4}}

Merci de votre confiance !
```

**Paramètres** :
- {{1}} : Nom du client
- {{2}} : Numéro de commande
- {{3}} : Montant
- {{4}} : Date de livraison

---

### Exemple 2 : Envoi de facture (Image avec légende)

**Template Name** : `send_invoice`

**Category** : UTILITY

**Language** : French (fr)

**Type** : Image

**Image** : Facture en PDF convertie en image

**Caption** :
```
Bonjour {{1}},

Voici votre facture pour la commande {{2}}.

Montant : {{3}} €
Date : {{4}}
```

---

### Exemple 3 : Rappel de rendez-vous (Texte avec boutons)

**Template Name** : `appointment_reminder`

**Category** : UTILITY

**Language** : French (fr)

**Type** : Interactive (Button)

**Body** :
```
Bonjour {{1}},

Rappel : Vous avez un rendez-vous le {{2}} à {{3}}.

Souhaitez-vous confirmer ou modifier ?
```

**Buttons** :
- ID : `btn_confirm`, Titre : "Confirmer"
- ID : `btn_reschedule`, Titre : "Reporter"
- ID : `btn_cancel`, Titre : "Annuler"

---

## Conseils pour une validation rapide

1. **Utilisez UTILITY** pour commencer (validation plus rapide)
2. **Messages clairs et professionnels**
3. **Respectez les limites de caractères**
4. **Testez les paramètres** avant de soumettre
5. **Évitez le contenu promotionnel** dans UTILITY
6. **Vérifiez l'orthographe** et la grammaire
7. **Utilisez des noms de templates descriptifs**

---

## Checklist avant soumission

- [ ] Nom du template en minuscules avec underscores
- [ ] Catégorie appropriée (UTILITY recommandé)
- [ ] Langue correcte
- [ ] Paramètres correctement formatés ({{1}}, {{2}}, etc.)
- [ ] Respect des limites de caractères
- [ ] Contenu conforme aux politiques Meta
- [ ] Image/vidéo dans les formats et tailles acceptés
- [ ] Boutons avec IDs et titres valides (si applicable)

---

## Support et ressources

- **Documentation Meta** : [developers.facebook.com/docs/whatsapp](https://developers.facebook.com/docs/whatsapp)
- **Politiques WhatsApp** : [business.facebook.com/policies](https://business.facebook.com/policies)
- **Support Meta Business** : Via Meta Business Suite

---

## Résumé rapide

1. **Créer** : Meta Business Suite → WhatsApp Manager → Message Templates → Create Template
2. **Remplir** : Nom, catégorie, langue, contenu
3. **Soumettre** : Cliquez sur "Submit"
4. **Attendre** : Validation (quelques heures à quelques jours)
5. **Synchroniser** : Dans Odoo → Configuration → Synchroniser les templates
6. **Utiliser** : WhatsApp > Envoyer un template

Bon courage pour la création de vos templates ! 🚀

