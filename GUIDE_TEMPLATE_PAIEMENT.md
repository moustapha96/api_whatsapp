# Guide : Créer un Template WhatsApp avec Bouton URL pour les Paiements

## Étape 1 : Accéder à Meta Business Suite

1. Allez sur [business.facebook.com](https://business.facebook.com)
2. Connectez-vous avec votre compte Meta Business
3. Sélectionnez votre compte WhatsApp Business
4. Allez dans **Paramètres** > **Messagerie** > **Templates de messages**

## Étape 2 : Créer un Nouveau Template

1. Cliquez sur **"Créer un template"** ou **"Nouveau template"**
2. Sélectionnez **"Message texte"** comme type de template

## Étape 3 : Configurer le Template Wave

### Informations de base :
- **Nom du template** : `paiement_wave` (en minuscules, sans espaces)
- **Catégorie** : `UTILITY` (ou `MARKETING` si vous voulez plus de flexibilité)
- **Langue** : `Français (fr)` ou `fr_FR`

### Corps du message :
```
💳 Paiement Wave pour la facture {{1}}

Montant à payer : {{2}} {{3}}

Cliquez sur le bouton ci-dessous pour payer avec Wave.

──────────────────────────────
Équipe CCBM Shop
```

**Variables** :
- `{{1}}` = Numéro de facture (ex: FAC/2025/00018)
- `{{2}}` = Montant résiduel (ex: 1416)
- `{{3}}` = Symbole de la devise (ex: CFA)

### Bouton URL :
1. Cliquez sur **"Ajouter un bouton"**
2. Sélectionnez **"URL"** comme type de bouton
3. **Texte du bouton** : `Payer avec Wave` (maximum 20 caractères)
4. **URL dynamique** : `{{4}}` (sera remplacé par le lien de paiement Wave)

### Exemple de template final :
```
Nom : paiement_wave
Catégorie : UTILITY
Langue : fr

Corps :
💳 Paiement Wave pour la facture {{1}}

Montant à payer : {{2}} {{3}}

Cliquez sur le bouton ci-dessous pour payer avec Wave.

──────────────────────────────
Équipe CCBM Shop

Bouton 1 (URL) :
- Type : URL
- Texte : Payer avec Wave
- URL : {{4}}
```

## Étape 4 : Configurer le Template Orange Money

### Informations de base :
- **Nom du template** : `paiement_orange` (en minuscules, sans espaces)
- **Catégorie** : `UTILITY` (ou `MARKETING`)
- **Langue** : `Français (fr)` ou `fr_FR`

### Corps du message :
```
💳 Paiement Orange Money pour la facture {{1}}

Montant à payer : {{2}} {{3}}

Cliquez sur le bouton ci-dessous pour payer avec Orange Money.

──────────────────────────────
Équipe CCBM Shop
```

### Bouton URL :
1. Cliquez sur **"Ajouter un bouton"**
2. Sélectionnez **"URL"** comme type de bouton
3. **Texte du bouton** : `Payer Orange` (maximum 20 caractères)
4. **URL dynamique** : `{{4}}` (sera remplacé par le lien de paiement Orange Money)

## Étape 5 : Soumettre pour Approbation

1. Vérifiez que tous les champs sont corrects
2. Cliquez sur **"Soumettre"** ou **"Envoyer pour approbation"**
3. **Temps d'attente** : Généralement 24-48 heures, peut prendre jusqu'à 7 jours

## Étape 6 : Vérifier l'Approbation

1. Retournez dans **Templates de messages**
2. Vérifiez le statut de vos templates
3. Une fois **"Approuvé"**, vous pouvez les utiliser dans le code

## Notes importantes :

- ⚠️ **Les templates doivent être approuvés avant utilisation**
- ⚠️ **Les noms de templates sont sensibles à la casse** (paiement_wave ≠ Paiement_Wave)
- ⚠️ **Les variables {{1}}, {{2}}, etc. sont remplacées par vos valeurs**
- ⚠️ **Les boutons URL doivent pointer vers des URLs HTTPS valides**
- ⚠️ **Les textes de boutons sont limités à 20 caractères**

---

## ✅ Code Déjà Prêt !

Le code a été modifié pour utiliser automatiquement les templates `paiement_wave` et `paiement_orange` une fois qu'ils seront approuvés.

**Fonctionnement automatique** :
- Si le template est approuvé → Utilise le template avec bouton URL cliquable
- Si le template n'est pas disponible → Utilise un message texte avec lien cliquable (fallback)

**Aucune modification de code nécessaire** : Le système détecte automatiquement si les templates sont disponibles et les utilise en priorité.

## Test après Approbation

Une fois vos templates approuvés :

1. Testez en cliquant sur "Payer Wave" ou "Payer Orange" dans une facture
2. Vous devriez recevoir un message avec un **bouton cliquable** au lieu d'un lien en texte
3. Le bouton ouvrira directement la page de paiement

## Dépannage

Si les templates ne fonctionnent pas :

1. Vérifiez que les noms sont exactement : `paiement_wave` et `paiement_orange` (minuscules)
2. Vérifiez que le statut est "Approuvé" dans Meta Business Suite
3. Vérifiez les logs Odoo pour voir les erreurs éventuelles
4. Le système utilisera automatiquement le fallback (message texte) si le template échoue

