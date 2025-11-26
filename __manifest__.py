# whatsapp_business_api/__manifest__.py
{
    "name": "WhatsApp b-2-b",
    "version": "16.0.1.0.0",
    "summary": "Intégration API WhatsApp b-2-b",
    "description": """
        Module complet pour intégrer l'API WhatsApp Business Cloud à Odoo :
        - Configuration du compte
        - Envoi de messages (texte)
        - Webhook de réception de messages / statuts
        - Journalisation des messages
        - Templates WhatsApp
    """,
    "category": "CCBM",
    "author": "Al Hussein",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "sale", "account"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/whatsapp_button_action_examples.xml",
        "data/whatsapp_template_examples.xml",
        "data/whatsapp_order_validation_actions.xml",
        "data/whatsapp_order_validation_actions_v2.xml",
        "data/whatsapp_order_details_actions.xml",
        "data/whatsapp_order_download_action.xml",
        "data/whatsapp_invoice_validation_actions.xml",
        "data/whatsapp_invoice_download_action.xml",
        "data/whatsapp_invoice_payment_actions.xml",
        "data/whatsapp_send_all_invoices_action.xml",
        "data/whatsapp_cron_data.xml",
        "data/whatsapp_next_invoice_action.xml",
        "data/whatsapp_greeting_menu_action.xml",
        "data/whatsapp_greeting_menu_buttons_action.xml",
        "views/whatsapp_config_views.xml",
        "views/whatsapp_send_message_views.xml",
        "views/whatsapp_send_partner_message_views.xml",
        "views/res_partner_whatsapp_views.xml",
        "views/account_move_whatsapp_views.xml",
        "views/whatsapp_conversation_views.xml",
        "views/whatsapp_message_views.xml",
        "views/whatsapp_template_views.xml",
        "views/whatsapp_button_action_views.xml",
        "views/whatsapp_interactive_scenario_views.xml",
        "views/sale_order_whatsapp_views.xml",  # Décommenter après vérification que le module sale est installé
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
