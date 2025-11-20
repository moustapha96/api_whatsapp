# Instructions : Ajouter la vue pour les commandes de vente

## Problème

L'ID externe de la vue de formulaire des commandes de vente peut varier selon la version d'Odoo. 

## Solution

### Option 1 : Ajouter manuellement après installation

1. **Installez d'abord le module `sale`** si ce n'est pas déjà fait
2. **Mettez à jour le module `api_whatsapp`**
3. **Décommentez la ligne** dans `__manifest__.py` :
   ```python
   "views/sale_order_whatsapp_views.xml",
   ```
4. **Mettez à jour à nouveau** le module

### Option 2 : Vérifier l'ID externe correct

1. Activez le **mode développeur** dans Odoo
2. Allez dans **Paramètres techniques > Vues**
3. Recherchez la vue de formulaire des commandes de vente (`sale.order`)
4. Notez l'**ID externe** exact
5. Modifiez `views/sale_order_whatsapp_views.xml` avec le bon ID :
   ```xml
   <field name="inherit_id" ref="LE_BON_ID_ICI"/>
   ```

### Option 3 : IDs courants à essayer

Essayez ces IDs dans `views/sale_order_whatsapp_views.xml` :

- `sale.view_order_form`
- `sale.view_sales_order_form`
- `sale.sale_order_view_form`

### Option 4 : Créer la vue sans hériter

Si aucun ID ne fonctionne, vous pouvez créer un menu séparé :

```xml
<record id="action_send_order_validation" model="ir.actions.server">
    <field name="name">Envoyer validation WhatsApp</field>
    <field name="model_id" ref="sale.model_sale_order"/>
    <field name="binding_model_id" ref="sale.model_sale_order"/>
    <field name="binding_view_types">form</field>
    <field name="state">code</field>
    <field name="code">
action = records.action_send_order_validation_whatsapp()
    </field>
</record>
```

## Vérification

Une fois la vue ajoutée, vous devriez voir le bouton **"Envoyer validation WhatsApp"** dans :
- Le header des commandes de vente
- Les champs WhatsApp dans la vue de commande

