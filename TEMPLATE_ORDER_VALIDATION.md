# Template WhatsApp : Validation de commande

## Template à créer dans Meta Business Suite

### Configuration

1. Allez dans **Meta Business Suite** → **WhatsApp Manager** → **Message Templates**
2. Cliquez sur **"Create Template"**
3. Remplissez les informations suivantes :

**Template Name** : `order_validation`

**Category** : `UTILITY`

**Language** : `French (fr)`

**Type** : `Interactive` → `Button`

### Message Body

Copiez-collez exactement ce texte :

```
Bonjour ,

Détails de votre commande :

- Numéro : {{1}}

- Montant : {{2}} F CFA

Souhaitez-vous valider cette commande ?
```

### Boutons

Configurez **2 boutons** :

**Bouton 1 - Valider** :
- **ID** : `btn_validate_order`
- **Titre** : `Valider`

**Bouton 2 - Rejeter** :
- **ID** : `btn_reject_order`
- **Titre** : `Rejeter`

### Paramètres

Le template utilise **2 paramètres** :

- **{{1}}** : Numéro de commande (ex: SO001, SO/2024/001)
- **{{2}}** : Montant en F CFA (ex: 15000, 250000)

Ces paramètres sont remplis automatiquement par Odoo lors de l'envoi.

### Exemple de message envoyé

Quand vous envoyez la validation depuis Odoo, le client recevra :

```
Bonjour ,

Détails de votre commande :

- Numéro : SO001

- Montant : 15000 F CFA

Souhaitez-vous valider cette commande ?

[Valider]  [Rejeter]
```

## Actions automatiques dans Odoo

Les actions de boutons sont **déjà configurées** dans Odoo :

- **btn_validate_order** : Valide la commande (état → "Confirmé")
- **btn_reject_order** : Rejette la commande (état → "Annulé")

## Utilisation

1. **Créez le template** dans Meta Business Suite avec le format ci-dessus
2. **Attendez l'approbation** (généralement rapide pour UTILITY)
3. **Synchronisez** dans Odoo : WhatsApp > Configuration → "Synchroniser les templates"
4. **Utilisez** : Ouvrez une commande de vente → Menu Action → "Envoyer validation WhatsApp"

## Important

- Le montant est envoyé **sans décimales** (ex: 15000 au lieu de 15000.00)
- Le format est **F CFA** (Franc CFA)
- Les boutons doivent avoir les IDs exacts : `btn_validate_order` et `btn_reject_order`

