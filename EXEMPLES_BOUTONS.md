# Guide d'utilisation des boutons interactifs WhatsApp

## Vue d'ensemble

Ce système permet d'envoyer des messages WhatsApp avec des boutons interactifs et d'exécuter automatiquement des actions lorsque les clients cliquent sur ces boutons.

## Fonctionnement

1. **Créer des actions de boutons** : Définissez les actions à exécuter pour chaque ID de bouton
2. **Envoyer un message avec boutons** : Utilisez le wizard pour envoyer un message avec jusqu'à 3 boutons
3. **Réception automatique** : Quand le client clique, l'action associée est exécutée automatiquement

## Exemples d'utilisation

### Exemple 1 : Confirmation simple (Oui/Non)

**Étape 1 : Créer les actions**

1. Allez dans **WhatsApp > Actions de boutons**
2. Créez deux actions :

**Action pour "Oui" (btn_yes)** :
- Nom : Confirmation Oui
- ID du bouton : `btn_yes`
- Type d'action : Envoyer un message
- Message à envoyer : "Merci pour votre confirmation ! Nous avons bien reçu votre réponse positive."

**Action pour "Non" (btn_no)** :
- Nom : Refus Non
- ID du bouton : `btn_no`
- Type d'action : Envoyer un message
- Message à envoyer : "Nous avons bien reçu votre réponse. N'hésitez pas à nous contacter si vous changez d'avis."

**Étape 2 : Envoyer le message**

1. Allez dans **WhatsApp > Envoyer un message avec boutons**
2. Remplissez :
   - Numéro : +33612345678
   - Message : "Souhaitez-vous confirmer votre commande ?"
   - Bouton 1 : ID = `btn_yes`, Titre = "Oui"
   - Bouton 2 : ID = `btn_no`, Titre = "Non"

**Résultat** : Le client reçoit le message avec 2 boutons. Quand il clique :
- Sur "Oui" → Reçoit automatiquement le message de confirmation
- Sur "Non" → Reçoit automatiquement le message de refus

### Exemple 2 : Mise à jour de contact

**Action personnalisée (btn_status)** :
- Nom : Mise à jour statut
- ID du bouton : `btn_status`
- Type d'action : Code Python
- Code Python :
```python
if contact:
    contact.write({
        'comment': f"Statut confirmé via WhatsApp le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    })
    if message.config_id:
        message.config_id.send_text_message(
            contact.phone or message.phone,
            "Votre statut a été mis à jour avec succès !"
        )
```

### Exemple 3 : Création de ticket (si module helpdesk installé)

**Action (btn_support)** :
- Nom : Créer ticket support
- ID du bouton : `btn_support`
- Type d'action : Créer un ticket
- (Le système créera automatiquement un ticket avec les informations du message)

## Types d'actions disponibles

1. **Envoyer un message** : Envoie automatiquement un message après le clic
2. **Mettre à jour le contact** : Met à jour un champ du contact
3. **Créer un ticket** : Crée un ticket helpdesk (si module installé)
4. **Mettre à jour le statut** : Alias pour mettre à jour le contact
5. **Code Python personnalisé** : Exécute du code Python avec accès à :
   - `env` : Environnement Odoo
   - `message` : Message WhatsApp reçu
   - `contact` : Contact associé (si trouvé)
   - `button_id` : ID du bouton cliqué

## Structure des boutons dans l'API

Les boutons doivent respecter le format de l'API Meta :

```python
buttons = [
    {
        "type": "reply",
        "reply": {
            "id": "btn_yes",      # ID utilisé pour identifier l'action
            "title": "Oui"        # Texte affiché sur le bouton
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

## Limitations

- Maximum 3 boutons par message
- Les titres de boutons sont limités à 20 caractères
- Les IDs de boutons doivent être uniques et correspondre aux actions définies

## Conseils

1. Utilisez des IDs de boutons descriptifs : `btn_yes`, `btn_no`, `btn_contact`, etc.
2. Testez toujours les actions avant de les utiliser en production
3. Les actions sont exécutées dans l'ordre de leur séquence
4. Plusieurs actions peuvent être associées au même bouton

