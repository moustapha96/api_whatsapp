# Ce que vous pouvez faire avec ce module

## ✅ Ce que le module PEUT faire

### 1. Envoyer des templates WhatsApp (après création dans Meta)

**OUI**, vous pouvez envoyer des templates depuis Odoo, **MAIS** :

- ✅ Les templates doivent être **créés et approuvés** dans Meta Business Suite d'abord
- ✅ Une fois approuvés, vous pouvez les **synchroniser** dans Odoo
- ✅ Vous pouvez ensuite les **envoyer** depuis Odoo avec des paramètres dynamiques

**Types de templates supportés** :
- ✅ Templates texte (avec paramètres)
- ✅ Templates avec header (texte, image, vidéo, document)
- ✅ Templates avec boutons interactifs
- ✅ Templates avec listes déroulantes

### 2. Envoyer des messages directs (sujets à fenêtre de 24h)

**OUI**, vous pouvez envoyer directement :
- ✅ Messages texte simples
- ✅ Images
- ✅ Vidéos
- ✅ Documents
- ✅ Audio
- ✅ Localisation
- ✅ Messages avec boutons interactifs

**⚠️ Limitation** : Ces messages ne fonctionnent que si le client vous a écrit dans les 24h.

---

## ❌ Ce que le module NE PEUT PAS faire

### 1. Créer des templates directement depuis Odoo

**NON**, vous **NE POUVEZ PAS** créer des templates depuis Odoo.

**Pourquoi ?**
- WhatsApp/Meta exige que tous les templates soient créés et validés dans Meta Business Suite
- C'est une exigence de sécurité et de conformité de WhatsApp
- Les templates doivent être approuvés manuellement par Meta

**Où créer les templates ?**
- Meta Business Suite → WhatsApp Manager → Message Templates
- Voir le guide : `GUIDE_CREATION_TEMPLATES.md`

### 2. Valider automatiquement les templates

**NON**, la validation est faite par Meta, pas par Odoo.

---

## 🔄 Processus complet

### Étape 1 : Créer le template dans Meta Business Suite

1. Allez sur [business.facebook.com](https://business.facebook.com)
2. WhatsApp Manager → Message Templates → Create Template
3. Remplissez les informations (nom, catégorie, langue, contenu)
4. Soumettez pour validation
5. Attendez l'approbation (quelques heures à quelques jours)

### Étape 2 : Synchroniser dans Odoo

1. Dans Odoo : **WhatsApp > Configuration**
2. Cliquez sur **"Synchroniser les templates"**
3. Les templates approuvés apparaissent dans **WhatsApp > Templates**

### Étape 3 : Utiliser le template dans Odoo

**Via l'interface** :
1. **WhatsApp > Envoyer un template**
2. Sélectionnez votre template
3. Remplissez les paramètres si nécessaire
4. Envoyez

**Via code Python** :
```python
config = env['whatsapp.config'].get_active_config()

# Template simple
config.send_template_message(
    to_phone="+33612345678",
    template_name="simple_text_message",
    language_code="fr"
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
                {"type": "text", "text": "CMD-2024-001"}
            ]
        }
    ]
)

# Template avec header image et paramètres
config.send_template_message(
    to_phone="+33612345678",
    template_name="send_invoice",
    language_code="fr",
    components=[
        {
            "type": "header",
            "parameters": [
                {
                    "type": "image",
                    "image": {
                        "link": "https://example.com/invoice.jpg"
                    }
                }
            ]
        },
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": "Jean Dupont"},
                {"type": "text", "text": "150.00"}
            ]
        }
    ]
)
```

---

## 📋 Résumé

| Action | Possible depuis Odoo ? | Où le faire ? |
|--------|------------------------|---------------|
| Créer un template | ❌ NON | Meta Business Suite |
| Valider un template | ❌ NON | Meta (automatique) |
| Synchroniser les templates | ✅ OUI | Odoo (Configuration) |
| Envoyer un template | ✅ OUI | Odoo (Interface ou code) |
| Envoyer message texte direct | ✅ OUI | Odoo (sujet à 24h) |
| Envoyer image/vidéo directe | ✅ OUI | Odoo (sujet à 24h) |

---

## 💡 Recommandation

**Pour envoyer des messages hors de la fenêtre de 24h** :

1. ✅ Créez des templates dans Meta Business Suite
2. ✅ Attendez leur approbation
3. ✅ Synchronisez-les dans Odoo
4. ✅ Utilisez-les depuis Odoo

**Pour des messages urgents dans la fenêtre de 24h** :

1. ✅ Utilisez directement les messages texte/image/vidéo depuis Odoo
2. ✅ Pas besoin de template

---

## 🎯 Conclusion

**Le module permet d'ENVOYER des templates**, mais **PAS de les CRÉER**.

La création doit se faire dans Meta Business Suite (exigence WhatsApp/Meta).

Une fois créés et approuvés, vous pouvez les utiliser librement depuis Odoo ! 🚀

