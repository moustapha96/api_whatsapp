# Templates à créer dans WhatsApp Business Manager

Si la création via l’API échoue, créez ces templates **à la main** dans WhatsApp Manager, puis utilisez **« Synchroniser depuis WhatsApp »** dans Odoo pour les récupérer.

**Lien :** https://business.facebook.com/latest/whatsapp_manager/message_templates  

**Étapes :** WhatsApp Manager → Message Templates → **Create template**.

---

## Règles à respecter

- **Nom du template** : uniquement minuscules, chiffres et underscores (ex. `invoice_message`).
- **Langue** : French (ou celle affichée équivalente, ex. `fr` / `fr_FR`).
- **Catégorie** : **Utility** pour tous ces templates.
- **Corps** : copier-coller le texte ci-dessous tel quel (y compris `{{1}}`, `{{2}}` si présents).

---

## 1. invoice_message (pour les factures)

- **Nom :** `invoice_message`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Message : {{1}}
  ```
- **Variables :** 1 variable (texte). Exemple : `Votre facture FAC/2026/00001 est disponible.`

---

## 2. simple_text_message

- **Nom :** `simple_text_message`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Bonjour, ceci est un message simple que vous pouvez envoyer à tout moment. Merci.
  ```
- **Variables :** Aucune

---

## 3. welcome_message

- **Nom :** `welcome_message`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Bonjour et bienvenue ! Nous sommes à votre disposition.
  ```
- **Variables :** Aucune

---

## 4. simple_notification

- **Nom :** `simple_notification`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Notification : vous avez un nouveau message.
  ```
- **Variables :** Aucune

---

## 5. message_with_params

- **Nom :** `message_with_params`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Bonjour {{1}}, votre commande {{2}} est prête.
  ```
- **Variables :** 2 variables (texte). Exemples : `Jean` et `CMD-2026-001`

---

## 6. order_confirmation

- **Nom :** `order_confirmation`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Votre commande a été enregistrée. Merci pour votre confiance.
  ```
- **Variables :** Aucune

---

## 7. appointment_reminder

- **Nom :** `appointment_reminder`
- **Langue :** French
- **Catégorie :** Utility
- **Corps (Body) :**
  ```
  Rappel : vous avez un rendez-vous prévu. Merci de confirmer votre présence.
  ```
- **Variables :** Aucune

---

## Après création

1. Soumettez chaque template (souvent validation automatique pour Utility).
2. Dans Odoo : **Paramètres WhatsApp** → **Synchroniser depuis WhatsApp** pour importer les templates et leurs statuts.
