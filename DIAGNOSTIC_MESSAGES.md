# Diagnostic : Messages envoyés mais non reçus

## Causes principales

### 1. ⚠️ Fenêtre de 24 heures expirée (Code 131026)

**Problème** : Les messages texte ne peuvent être envoyés que dans les 24h après le dernier message du client.

**Solution** : 
- Utilisez un **template WhatsApp approuvé** pour envoyer des messages hors de la fenêtre de 24h
- Les templates doivent être approuvés par Meta avant utilisation
- Allez dans **WhatsApp > Templates** pour synchroniser vos templates

**Comment vérifier** :
- Regardez la date du dernier message entrant du client
- Si plus de 24h, vous devez utiliser un template

### 2. ⚠️ Numéro invalide ou non WhatsApp (Code 131047)

**Problème** : Le numéro n'est pas un numéro WhatsApp valide ou la personne n'a pas WhatsApp.

**Solutions** :
- Vérifiez que le numéro est correct (format international : +33612345678)
- Vérifiez que la personne a WhatsApp installé et actif
- Testez avec votre propre numéro d'abord

### 3. ⚠️ Numéro non autorisé en mode développement (Code 131031)

**Problème** : En mode développement/test, seuls les numéros de test sont autorisés.

**Solution** :
1. Allez dans Meta Business Suite
2. WhatsApp > API Setup > Phone numbers
3. Ajoutez le numéro dans la liste des numéros de test
4. Ou passez en mode production (nécessite vérification Meta)

### 4. ⚠️ Token d'accès invalide (Code 190)

**Problème** : Le token d'accès est expiré ou invalide.

**Solution** :
1. Allez dans Meta Business Suite
2. Régénérez votre access_token
3. Mettez à jour la configuration dans **WhatsApp > Configuration**

### 5. ⚠️ Format de numéro incorrect (Code 100)

**Problème** : Le format du numéro n'est pas valide.

**Solution** :
- Utilisez le format international : **+33612345678**
- Le numéro doit commencer par **+** suivi de l'indicatif pays
- Exemples valides : +33612345678, +212612345678, +12025551234

## Outils de diagnostic

### Bouton "Diagnostiquer les envois"

Dans la configuration WhatsApp, utilisez le bouton **"Diagnostiquer les envois"** pour :
- Vérifier les problèmes dans les messages récents
- Détecter les fenêtres de 24h expirées
- Identifier les numéros invalides
- Voir les erreurs de l'API

### Champ "Aide sur l'erreur"

Dans chaque message, un champ **"Diagnostic"** apparaît automatiquement avec :
- Le type d'erreur détecté
- La solution recommandée
- Des conseils spécifiques selon le code d'erreur

## Vérifications à faire

1. **Format du numéro** : Doit être au format international (+33612345678)
2. **Fenêtre de 24h** : Vérifiez la date du dernier message entrant
3. **Mode développement** : Vérifiez que le numéro est dans la liste de test
4. **Token d'accès** : Vérifiez qu'il n'est pas expiré
5. **Template** : Pour les messages hors 24h, utilisez un template approuvé

## Solutions rapides

### Pour envoyer un message texte immédiatement :
✅ Le client doit vous avoir envoyé un message dans les 24h

### Pour envoyer un message hors 24h :
✅ Utilisez un template WhatsApp approuvé
✅ Allez dans **WhatsApp > Envoyer un template**

### Pour tester :
✅ Utilisez votre propre numéro
✅ Vérifiez qu'il est dans la liste de test (mode dev)
✅ Envoyez-vous un message d'abord pour ouvrir la fenêtre de 24h

## Logs et débogage

Les réponses complètes de l'API sont stockées dans :
- **Onglet "Réponse API"** dans la vue du message
- **Champ "Statut WhatsApp brut"** pour les erreurs
- **Logs Odoo** pour les détails techniques

