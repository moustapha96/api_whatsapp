# Guide : Créer un template WhatsApp simple pour messages texte

## Pourquoi utiliser un template ?

Les messages texte simples ne peuvent être envoyés que dans les **24 heures** après le dernier message du client. Pour envoyer des messages à tout moment, vous devez utiliser un **template WhatsApp approuvé**.

## Étapes pour créer un template dans Meta Business Suite

### 1. Accéder à Meta Business Suite

1. Allez sur [business.facebook.com](https://business.facebook.com)
2. Sélectionnez votre compte WhatsApp Business
3. Allez dans **WhatsApp Manager** > **Message Templates**

### 2. Créer un nouveau template

1. Cliquez sur **"Create Template"**
2. Choisissez **"Text"** comme type de message
3. Remplissez les informations :

**Exemple de template simple :**

- **Template Name** : `simple_message` (sans espaces, en minuscules)
- **Category** : **UTILITY** (pour messages transactionnels/informatifs)
- **Language** : **French (fr)** ou votre langue
- **Message** :
```
Bonjour ! Ceci est un message simple que vous pouvez envoyer à tout moment, même hors de la fenêtre de 24h.
```

### 3. Template avec paramètres (optionnel)

Si vous voulez personnaliser le message :

**Template Name** : `personalized_message`

**Message** :
```
Bonjour {{1}} ! Votre commande {{2}} est prête. Merci de votre confiance.
```

Où :
- `{{1}}` sera remplacé par le nom du client
- `{{2}}` sera remplacé par le numéro de commande

### 4. Soumettre pour approbation

1. Cliquez sur **"Submit"**
2. Attendez l'approbation (généralement quelques minutes à quelques heures)
3. Une fois approuvé, le statut passe à **"Approved"**

### 5. Synchroniser dans Odoo

1. Allez dans **WhatsApp > Configuration**
2. Cliquez sur **"Synchroniser les templates"**
3. Vos templates apparaîtront dans **WhatsApp > Templates**

## Utiliser le template dans Odoo

### Méthode 1 : Via le wizard

1. Allez dans **WhatsApp > Envoyer un template**
2. Sélectionnez votre template
3. Remplissez les paramètres si nécessaire (format JSON)
4. Envoyez

### Méthode 2 : Via code Python

```python
config = env['whatsapp.config'].get_active_config()
config.send_template_message(
    to_phone="+33612345678",
    template_name="simple_message",
    language_code="fr",
    components=None  # Pas de paramètres pour un message simple
)
```

## Exemple de template simple recommandé

**Nom dans Meta** : `simple_text_message`

**Catégorie** : UTILITY

**Message** :
```
Bonjour,

Ce message vous est envoyé via WhatsApp Business.

Cordialement,
Votre équipe
```

**Avantages** :
- ✅ Simple et générique
- ✅ Peut être utilisé pour n'importe quel contexte
- ✅ Pas de paramètres à gérer
- ✅ Facile à approuver par Meta

## Notes importantes

1. **Nom du template** : Doit être en minuscules, sans espaces (utilisez des underscores)
2. **Catégorie UTILITY** : Pour les messages transactionnels/informatifs (plus facile à approuver)
3. **Catégorie MARKETING** : Pour les messages promotionnels (plus strict)
4. **Approval** : Les templates UTILITY sont généralement approuvés plus rapidement
5. **Paramètres** : Utilisez `{{1}}`, `{{2}}`, etc. pour les variables

## Template d'exemple à créer dans Meta (RECOMMANDÉ)

Voici le template le plus simple que vous pouvez créer. Il vous permettra d'envoyer des messages texte à tout moment :

### Configuration dans Meta Business Suite

**Template Name** : `simple_text_message`

**Category** : **UTILITY** (important : plus facile à approuver)

**Language** : French (fr)

**Message Body** :
```
Bonjour,

Ceci est un message simple que vous pouvez envoyer à tout moment, même hors de la fenêtre de 24h.

Merci.
```

### Étapes détaillées

1. **Allez dans Meta Business Suite** → WhatsApp Manager → Message Templates
2. **Cliquez sur "Create Template"**
3. **Remplissez** :
   - Name: `simple_text_message`
   - Category: `UTILITY`
   - Language: `French (fr)`
   - Message: (copiez le message ci-dessus)
4. **Soumettez** et attendez l'approbation (généralement rapide pour UTILITY)
5. **Dans Odoo** : Allez dans Configuration → Cliquez sur "Synchroniser les templates"
6. **Utilisez** : WhatsApp > Envoyer un template → Sélectionnez "Message texte simple"

### Utilisation dans Odoo

Une fois synchronisé :

1. Allez dans **WhatsApp > Envoyer un template**
2. Sélectionnez **"Message texte simple"** (ou le nom que vous avez donné)
3. Entrez le numéro de téléphone
4. **Laissez le champ "Paramètres" VIDE** (ce template n'a pas de paramètres)
5. Cliquez sur **"Envoyer"**

✅ **Avantage** : Vous pouvez envoyer ce message même si le client ne vous a pas écrit dans les 24h !

## Template encore plus simple (minimal)

Si vous voulez le template le plus simple possible :

**Template Name** : `simple_message`

**Category** : UTILITY

**Message** :
```
Bonjour, ceci est un message simple.
```

C'est tout ! Pas de paramètres, message court, facile à approuver.

