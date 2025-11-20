# Guide d'utilisation de la fonction `send_text_to_partner`

## Vue d'ensemble

La fonction `send_text_to_partner` permet d'envoyer un message texte WhatsApp à un partenaire depuis **n'importe quel module Odoo**. Cette fonction est disponible dans le modèle `whatsapp.config`.

## Utilisation de base

### Depuis un autre module Python

```python
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MonModele(models.Model):
    _name = 'mon.modele'
    _description = 'Mon modèle personnalisé'
    
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    
    def action_envoyer_whatsapp(self):
        """Envoie un message WhatsApp au partenaire"""
        self.ensure_one()
        
        if not self.partner_id:
            raise ValidationError(_("Aucun partenaire sélectionné."))
        
        # Récupère la configuration WhatsApp active
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        
        if not config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        # Envoie le message
        try:
            result = config.send_text_to_partner(
                partner_id=self.partner_id.id,
                message_text="Bonjour, votre commande est prête !"
            )
            
            if result.get('success'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Succès'),
                        'message': _('Message WhatsApp envoyé avec succès'),
                        'type': 'success',
                    }
                }
        except ValidationError as e:
            raise ValidationError(_("Erreur : %s") % str(e))
```

### Exemple avec un bouton dans une vue

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_envoyer_notification_whatsapp(self):
        """Envoie une notification WhatsApp au client"""
        self.ensure_one()
        
        if not self.partner_id:
            raise ValidationError(_("Aucun partenaire associé à cette commande."))
        
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not config:
            raise ValidationError(_("Aucune configuration WhatsApp active trouvée."))
        
        message = f"Bonjour {self.partner_id.name},\n\nVotre commande {self.name} d'un montant de {self.amount_total:.2f} € est en préparation."
        
        result = config.send_text_to_partner(
            partner_id=self.partner_id.id,
            message_text=message
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Message envoyé'),
                'message': _('Notification WhatsApp envoyée au client'),
                'type': 'success',
            }
        }
```

## Paramètres de la fonction

### Signature

```python
@api.model
def send_text_to_partner(self, partner_id, message_text, preview_url=False, config_id=None):
```

### Paramètres

- **`partner_id`** (obligatoire) : 
  - ID du partenaire (int) ou objet partenaire (recordset)
  - Le partenaire doit avoir un numéro de téléphone (`phone` ou `mobile`)

- **`message_text`** (obligatoire) :
  - Texte du message à envoyer
  - String

- **`preview_url`** (optionnel, défaut: `False`) :
  - Si `True`, active la prévisualisation des liens dans le message
  - Boolean

- **`config_id`** (optionnel) :
  - ID de la configuration WhatsApp à utiliser
  - Si non spécifié, utilise automatiquement la configuration active
  - Integer

### Valeur de retour

La fonction retourne un dictionnaire avec :

```python
{
    'success': True/False,           # Indique si l'envoi a réussi
    'message_id': 'wamid.xxx',       # ID du message retourné par WhatsApp
    'message_record': recordset,     # Enregistrement whatsapp.message créé
    'error': None ou message d'erreur # Message d'erreur si échec
}
```

### Exceptions

La fonction peut lever une `ValidationError` dans les cas suivants :

- Partenaire introuvable
- Partenaire sans numéro de téléphone
- Aucune configuration WhatsApp active
- Erreur lors de l'envoi (numéro invalide, erreur API, etc.)

## Exemples d'utilisation avancés

### Exemple 1 : Envoi depuis un workflow automatique

```python
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def action_confirm(self):
        """Envoie une notification WhatsApp quand la livraison est confirmée"""
        res = super().action_confirm()
        
        if self.partner_id and (self.partner_id.phone or self.partner_id.mobile):
            config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
            if config:
                try:
                    message = f"Votre commande {self.origin} est en cours de livraison. Suivez votre colis sur notre site."
                    config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
                except:
                    # Ne bloque pas le workflow si l'envoi échoue
                    pass
        
        return res
```

### Exemple 2 : Envoi avec prévisualisation de lien

```python
def action_envoyer_offre_speciale(self):
    """Envoie une offre spéciale avec lien"""
    config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
    if config:
        message = "Découvrez notre nouvelle collection : https://example.com/collection"
        result = config.send_text_to_partner(
            partner_id=self.partner_id.id,
            message_text=message,
            preview_url=True  # Active la prévisualisation du lien
        )
```

### Exemple 3 : Envoi depuis un cron (planificateur)

```python
class MonCron(models.Model):
    _name = 'mon.cron'
    
    def action_envoyer_rappel_quotidien(self):
        """Envoie un rappel quotidien aux partenaires"""
        config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not config:
            return
        
        # Récupère tous les partenaires avec numéro de téléphone
        partners = self.env['res.partner'].search([
            '|', ('phone', '!=', False), ('mobile', '!=', False)
        ])
        
        for partner in partners:
            try:
                message = f"Bonjour {partner.name}, n'oubliez pas de consulter nos nouvelles offres !"
                config.send_text_to_partner(
                    partner_id=partner.id,
                    message_text=message
                )
            except Exception as e:
                # Log l'erreur mais continue avec les autres partenaires
                _logger.error(f"Erreur envoi WhatsApp à {partner.name}: {e}")
```

## Interface utilisateur

Un menu est également disponible dans l'interface Odoo :

**WhatsApp > Envoyer message au partenaire**

Cette interface permet d'envoyer un message à un partenaire via un formulaire, sans avoir à écrire du code Python.

## Notes importantes

1. **Fenêtre de 24h** : Pour envoyer un message texte simple (hors template), le client doit avoir envoyé un message dans les 24 dernières heures. Sinon, utilisez un template WhatsApp.

2. **Numéro de téléphone** : Le partenaire doit avoir un numéro de téléphone valide dans les champs `phone` ou `mobile`.

3. **Configuration active** : Une configuration WhatsApp doit être active pour que l'envoi fonctionne.

4. **Gestion des erreurs** : Toujours gérer les exceptions `ValidationError` lors de l'appel à cette fonction.

5. **Conversation automatique** : La fonction crée automatiquement une conversation WhatsApp si elle n'existe pas déjà, et lie le message envoyé à cette conversation.

## Support

Pour toute question ou problème, consultez la documentation du module ou contactez le support technique.

