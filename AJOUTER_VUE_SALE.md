# Comment ajouter la vue pour les commandes de vente

## Problème

L'ID externe de la vue peut varier selon votre installation Odoo. Pour éviter les erreurs, la vue est commentée dans le manifest.

## Solution : Ajouter manuellement

### Étape 1 : Vérifier que le module sale est installé

1. Allez dans **Applications**
2. Recherchez **"Ventes"** ou **"Sale"**
3. Vérifiez qu'il est **installé**

### Étape 2 : Trouver le bon ID externe

1. Activez le **mode développeur** (Paramètres → Activer le mode développeur)
2. Allez dans **Paramètres techniques → Vues**
3. Recherchez une vue de type **Formulaire** pour le modèle **sale.order**
4. Notez l'**ID externe** (ex: `sale.view_order_form`, `sale.sale_order_view_form`, etc.)

### Étape 3 : Modifier la vue

1. Ouvrez `views/sale_order_whatsapp_views.xml`
2. Remplacez l'ID dans la ligne :
   ```xml
   <field name="model_id" ref="LE_BON_ID_ICI"/>
   <field name="binding_model_id" ref="LE_BON_ID_ICI"/>
   ```
   Par exemple :
   ```xml
   <field name="model_id" ref="sale.model_sale_order"/>
   <field name="binding_model_id" ref="sale.model_sale_order"/>
   ```

### Étape 4 : Activer la vue

1. Ouvrez `__manifest__.py`
2. Décommentez la ligne :
   ```python
   "views/sale_order_whatsapp_views.xml",
   ```
3. Mettez à jour le module

## Alternative : Utiliser directement la méthode

Même sans la vue, vous pouvez utiliser la méthode directement :

1. Ouvrez une commande de vente
2. Allez dans **Paramètres techniques → Actions serveur**
3. Créez une nouvelle action :
   - **Nom** : Envoyer validation WhatsApp
   - **Modèle** : Commande de vente
   - **Type d'action** : Code Python
   - **Code** :
   ```python
   action = records.action_send_order_validation_whatsapp()
   ```
4. L'action apparaîtra dans le menu **Action** de la vue formulaire

## Vérification

Une fois ajouté, vous devriez voir :
- Un bouton **"Envoyer validation WhatsApp"** dans le menu Action des commandes
- Ou directement dans le header si vous utilisez l'héritage de vue

