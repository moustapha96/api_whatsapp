# whatsapp_business_api/models/account_move_whatsapp.py
# Ce fichier nécessite le module 'account' pour fonctionner
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import config
import logging
import base64

_logger = logging.getLogger(__name__)

# Hérite directement de account.move (le module account est dans les dépendances)
class AccountMove(models.Model):
    _inherit = 'account.move'

    x_whatsapp_residual_sent = fields.Boolean(
        string="Message montant résiduel WhatsApp envoyé",
        default=False,
        help="Indique si un message de montant résiduel a été envoyé via WhatsApp"
    )
    
    x_whatsapp_residual_sent_date = fields.Datetime(
        string="Date envoi message résiduel WhatsApp"
    )
    
    x_whatsapp_validation_sent = fields.Boolean(
        string="Validation facture WhatsApp envoyée",
        default=False,
        help="Indique si un message de validation de facture a été envoyé via WhatsApp"
    )
    
    x_whatsapp_validation_sent_date = fields.Datetime(
        string="Date envoi validation facture WhatsApp"
    )
    
    x_whatsapp_invoice_sent = fields.Boolean(
        string="Facture WhatsApp envoyée",
        default=False,
        help="Indique si la facture a été envoyée par WhatsApp"
    )
    
    x_whatsapp_invoice_sent_date = fields.Datetime(
        string="Date envoi facture WhatsApp"
    )

    def write(self, vals):
        """Surcharge write pour détecter les changements de amount_residual et envoyer un message"""
        # Sauvegarde l'ancien état et montant résiduel avant la modification
        old_state = {}
        old_residual = {}
        
        # Détecte les changements qui peuvent affecter le montant résiduel ou l'état
        if any(field in vals for field in ['line_ids', 'invoice_payment_state', 'payment_state', 'state']):
            for record in self:
                if record.move_type in ['out_invoice', 'out_refund']:
                    old_state[record.id] = record.state
                    old_residual[record.id] = record.amount_residual
        
        # Effectue la modification
        result = super().write(vals)
        
        # Traite chaque facture
        for record in self:
            if record.move_type in ['out_invoice', 'out_refund']:
                # Vérifie si la facture vient d'être validée (postée)
                old_state_value = old_state.get(record.id)
                new_state_value = record.state
                
                # Si la facture passe à l'état "posted" (validée), envoie la facture
                if (old_state_value != new_state_value and 
                    new_state_value == 'posted' and 
                    not record.x_whatsapp_invoice_sent):
                    try:
                        record._send_whatsapp_invoice()
                    except Exception as e:
                        _logger.warning("Erreur lors de l'envoi de la facture WhatsApp pour %s: %s", record.name, str(e))
                
                # Si le montant résiduel a changé, envoie un message
                old_residual_value = old_residual.get(record.id)
                new_residual_value = record.amount_residual
                
                # Envoie un message si le montant résiduel a changé et qu'il reste à payer
                if (old_residual_value is not None and 
                    abs(old_residual_value - new_residual_value) > 0.01 and 
                    new_residual_value > 0):
                    try:
                        record._send_whatsapp_residual_notification(old_residual_value, new_residual_value)
                    except Exception as e:
                        _logger.warning("Erreur lors de l'envoi du message WhatsApp de montant résiduel pour la facture %s: %s", record.name, str(e))
        
        return result

    def _send_whatsapp_residual_notification(self, old_residual, new_residual):
        """Envoie un message WhatsApp avec le montant résiduel (reste à payer)"""
        self.ensure_one()
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour le partenaire %s, message WhatsApp résiduel non envoyé", self.partner_id.name)
            return
        
        # Vérifie si le message a déjà été envoyé (évite les doublons si le montant n'a pas vraiment changé)
        if self.x_whatsapp_residual_sent and abs(old_residual - new_residual) < 0.01:
            return
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            # Ne log pas d'avertissement en mode test
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer le message de montant résiduel")
            return
        
        try:
            # Nettoie le numéro de téléphone
            phone = whatsapp_config._validate_phone_number(phone)
            
            # Prépare le message
            message = f"Bonjour {self.partner_id.name},\n\n"
            message += f"Facture : {self.name}\n"
            message += f"Montant total : {self.amount_total:.0f} F CFA\n"
            message += f"Montant restant à payer : {new_residual:.0f} F CFA\n\n"
            
            # Calcule le montant payé
            amount_paid = self.amount_total - new_residual
            if amount_paid > 0:
                message += f"Montant déjà payé : {amount_paid:.0f} F CFA\n\n"
            
            # Ajoute un message selon le montant restant
            if new_residual < self.amount_total:
                message += "Un paiement partiel a été enregistré. Il reste un montant à régler."
            else:
                message += "Rappel : Cette facture est en attente de paiement."
            
            # Ajoute un lien vers la facture si disponible
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
            if base_url:
                invoice_url = f"{base_url}/web#id={self.id}&model=account.move&view_type=form"
                message += f"\n\nConsulter la facture : {invoice_url}"
            
            # Envoie le message via WhatsApp
            result = whatsapp_config.send_text_to_partner(
                partner_id=self.partner_id.id,
                message_text=message
            )
            
            # Met à jour la facture pour indiquer qu'un message a été envoyé
            if result.get('success'):
                self.write({
                    'x_whatsapp_residual_sent': True,
                    'x_whatsapp_residual_sent_date': fields.Datetime.now()
                })
                _logger.info("Message WhatsApp de montant résiduel envoyé avec succès pour la facture %s (reste: %s)", self.name, new_residual)
            else:
                _logger.warning("Échec de l'envoi du message WhatsApp de montant résiduel pour la facture %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi du message WhatsApp de montant résiduel pour la facture %s", self.name)
            # Ne lève pas d'exception pour ne pas bloquer la modification de la facture
    
    def action_send_whatsapp_invoice(self):
        """Action pour envoyer la facture par WhatsApp (appelée depuis le bouton)"""
        self.ensure_one()
        
        # Vérifie que c'est une facture client
        if self.move_type not in ['out_invoice', 'out_refund']:
            raise ValidationError(_("Cette fonctionnalité est uniquement disponible pour les factures clients."))
        
        # Vérifie que la facture est validée
        if self.state != 'posted':
            raise ValidationError(_("La facture doit être validée avant de pouvoir l'envoyer par WhatsApp."))
        
        # Vérifie qu'il y a un partenaire
        if not self.partner_id:
            raise ValidationError(_("Aucun partenaire associé à cette facture."))
        
        # Vérifie qu'il y a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            raise ValidationError(_("Le partenaire %s n'a pas de numéro de téléphone.") % self.partner_id.name)
        
        # Vérifie si la facture a déjà été envoyée
        if self.x_whatsapp_invoice_sent:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Cette facture a déjà été envoyée par WhatsApp le %s.') % (
                        self.x_whatsapp_invoice_sent_date.strftime('%d/%m/%Y %H:%M') if self.x_whatsapp_invoice_sent_date else _('date inconnue')
                    ),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Envoie la facture
        try:
            self._send_whatsapp_invoice()
            
            # Retourne une notification de succès
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Facture envoyée par WhatsApp à %s') % self.partner_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise ValidationError(_("Erreur lors de l'envoi de la facture : %s") % str(e))
    
    def _mark_invoice_sent(self):
        """Marque la facture comme envoyée par WhatsApp (utilisé pour éviter les doublons)"""
        self.ensure_one()
        if not self.x_whatsapp_invoice_sent:
            self.sudo().write({
                'x_whatsapp_invoice_sent': True,
                'x_whatsapp_invoice_sent_date': fields.Datetime.now()
            })
            _logger.info("Facture %s marquée comme envoyée par WhatsApp", self.name)
    
    def _send_whatsapp_invoice(self):
        """Envoie la facture en PDF par WhatsApp lorsqu'elle est validée"""
        self.ensure_one()
        
        # Vérifie si la facture a déjà été envoyée (évite les doublons) - VÉRIFICATION EN PREMIER
        # Utilise sudo() pour vérifier même si l'utilisateur n'a pas les droits
        if self.sudo().x_whatsapp_invoice_sent:
            _logger.info("Facture %s déjà envoyée par WhatsApp, envoi ignoré", self.name)
            return
        
        # Vérifie qu'il y a un partenaire avec un numéro de téléphone
        if not self.partner_id:
            return
        
        # Vérifie si le partenaire a un numéro de téléphone
        phone = self.partner_id.phone or self.partner_id.mobile
        if not phone:
            _logger.info("Pas de numéro de téléphone pour le partenaire %s, facture WhatsApp non envoyée", self.partner_id.name)
            return
        
        # Récupère la configuration WhatsApp active
        whatsapp_config = self.env['whatsapp.config'].search([('is_active', '=', True)], limit=1)
        if not whatsapp_config:
            # Ne log pas d'avertissement en mode test
            is_test_mode = config.get('test_enable') or config.get('test_file') or self.env.context.get('test_mode')
            if not is_test_mode:
                _logger.warning("Aucune configuration WhatsApp active trouvée pour envoyer la facture")
            return
        
        try:
            # Nettoie le numéro de téléphone
            phone = whatsapp_config._validate_phone_number(phone)
            
            # Génère le PDF de la facture
            # Essaie plusieurs méthodes pour trouver le rapport
            report = None
            report_names = ['account.report_invoice', 'account.report_invoice_with_payments']
            
            for report_name in report_names:
                try:
                    report = self.env['ir.actions.report']._get_report_from_name(report_name)
                    if report and report.exists() and report.id:
                        break
                    else:
                        report = None
                except Exception as e:
                    _logger.debug("Erreur lors de la recherche du rapport %s: %s", report_name, str(e))
                    report = None
                    continue
            
            # Si pas trouvé, cherche directement dans la base
            if not report or not report.exists():
                try:
                    report = self.env['ir.actions.report'].search([
                        ('report_name', 'in', report_names),
                        ('model', '=', 'account.move')
                    ], limit=1)
                    # Vérifie que le rapport existe vraiment
                    if report and not report.exists():
                        report = None
                except Exception as e:
                    _logger.debug("Erreur lors de la recherche du rapport dans la base: %s", str(e))
                    report = None
            
            # Si toujours pas de rapport, essaie de générer directement ou envoie juste le message texte
            if not report or not report.exists():
                _logger.info("Rapport de facture non trouvé pour %s, envoi du message texte uniquement", self.name)
                # Envoie juste un message texte avec les détails (pas de PDF)
                message = f"Bonjour {self.partner_id.name},\n\n"
                message += f"Votre facture {self.name} a été validée.\n\n"
                message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                if self.invoice_date:
                    message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                message += "\nMerci de votre confiance !"
                
                result = whatsapp_config.send_text_to_partner(
                    partner_id=self.partner_id.id,
                    message_text=message
                )
                # Marque immédiatement comme envoyé si succès
                if isinstance(result, dict) and result.get('success'):
                    self._mark_invoice_sent()
                pdf_content = None
            else:
                # Génère le PDF avec le rapport trouvé
                try:
                    # Vérifie que le rapport existe toujours avant de l'utiliser
                    if not report.exists():
                        raise Exception("Le rapport n'existe plus")
                    
                    # _render_qweb_pdf sur un objet report attend un ID unique (int)
                    pdf_content, _ = report._render_qweb_pdf(self.id)
                except Exception as e:
                    _logger.warning("Erreur lors de la génération du PDF avec le rapport %s pour la facture %s: %s", 
                                  report.report_name if report else 'N/A', self.name, str(e))
                    # Essaie avec la méthode de classe en passant le nom du rapport
                    try:
                        if report and report.report_name:
                            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                                report.report_name,
                                self.id
                            )
                        else:
                            pdf_content = None
                    except Exception as e2:
                        _logger.warning("Erreur avec méthode de classe: %s", str(e2))
                        pdf_content = None
                
                if not pdf_content:
                    _logger.info("Impossible de générer le PDF pour la facture %s, envoi du message texte uniquement", self.name)
                    # Envoie juste un message texte avec les détails
                    message = f"Bonjour {self.partner_id.name},\n\n"
                    message += f"Votre facture {self.name} a été validée.\n\n"
                    message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                    if self.invoice_date:
                        message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                    message += "\nMerci de votre confiance !"
                    
                    result = whatsapp_config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
                    # Marque immédiatement comme envoyé si succès
                    if isinstance(result, dict) and result.get('success'):
                        self._mark_invoice_sent()
                    pdf_content = None
            
            # Si on a un PDF, continue avec le traitement
            if pdf_content:
                try:
                    # Crée un attachement temporaire
                    # pdf_content est déjà en bytes, on doit l'encoder en base64 pour Odoo
                    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                    attachment = self.env['ir.attachment'].create({
                        'name': f"{self.name}.pdf",
                        'type': 'binary',
                        'datas': pdf_base64,
                        'res_model': 'account.move',
                        'res_id': self.id,
                        'mimetype': 'application/pdf',
                        'public': True,  # Rend l'attachement public pour que WhatsApp puisse le télécharger
                    })
                    
                    # Génère une URL publique pour le PDF
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                    if base_url:
                        # Génère l'URL pour télécharger le PDF
                        # Odoo permet d'accéder aux attachements via /web/content/{id}
                        pdf_url = f"{base_url}/web/content/{attachment.id}?download=true"
                        
                        # Essaie d'utiliser un template WhatsApp avec bouton URL
                        # Le template doit être créé dans Meta Business Suite avec le nom "invoice_with_download"
                        template_name = "invoice_with_download"  # Nom du template dans Meta
                        
                        try:
                            # Prépare les paramètres du template
                            # Le template doit avoir :
                            # - Body avec paramètres : {{1}} = Nom partenaire, {{2}} = Numéro facture, {{3}} = Montant, {{4}} = Date
                            # - Un bouton URL (défini dans le template Meta, l'URL sera passée comme paramètre dynamique)
                            components = [
                                {
                                    "type": "body",
                                    "parameters": [
                                        {"type": "text", "text": self.partner_id.name or ""},  # {{1}}
                                        {"type": "text", "text": self.name or ""},  # {{2}}
                                        {"type": "text", "text": f"{self.amount_total:.0f} F CFA"},  # {{3}}
                                        {"type": "text", "text": self.invoice_date.strftime('%d/%m/%Y') if self.invoice_date else ""}  # {{4}}
                                    ]
                                },
                                {
                                    "type": "button",
                                    "sub_type": "url",
                                    "index": "0",  # Index du bouton (0 pour le premier bouton URL dans le template)
                                    "parameters": [
                                        {
                                            "type": "text",
                                            "text": pdf_url  # URL dynamique pour le bouton - sera insérée dans le bouton URL du template
                                        }
                                    ]
                                }
                            ]
                            
                            # Envoie le template avec le bouton
                            # Note: send_template_message peut lever une ValidationError si le template n'existe pas
                            result = whatsapp_config.send_template_message(
                                to_phone=phone,
                                template_name=template_name,
                                language_code="fr",
                                components=components
                            )
                            
                            # Si on arrive ici, le template a été envoyé avec succès
                            _logger.info("Template %s envoyé avec succès pour la facture %s", template_name, self.name)
                            # Marque immédiatement comme envoyé pour éviter les doublons
                            if isinstance(result, dict) and result.get('success'):
                                self._mark_invoice_sent()
                                
                        except ValidationError as ve:
                            # Le template n'existe pas ou n'est pas approuvé
                            error_msg = str(ve).lower()
                            _logger.warning("Template %s non trouvé ou erreur: %s. Envoi du PDF directement.", template_name, error_msg)
                            # Continue avec l'envoi du PDF directement (pas de raise, on continue le code)
                            result = None
                        except Exception as e:
                            _logger.warning("Impossible d'utiliser le template %s: %s. Envoi du PDF directement.", template_name, str(e))
                            # Continue avec l'envoi du PDF directement
                            result = None
                        
                        # Si le template n'a pas fonctionné, envoie le PDF directement
                        # Vérifie si result est None ou si c'est un dict avec success=False
                        template_success = False
                        if result:
                            if isinstance(result, dict):
                                template_success = result.get('success', False)
                            else:
                                # Si result n'est pas un dict, on considère que ça a réussi (ancien format)
                                template_success = True
                        
                        if not template_success:
                            try:
                                message = f"Bonjour {self.partner_id.name},\n\n"
                                message += f"Votre facture {self.name} a été validée.\n\n"
                                message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                                if self.invoice_date:
                                    message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                                message += "\nMerci de votre confiance !"
                                
                                _logger.info("Tentative d'envoi du PDF directement pour la facture %s avec URL: %s", self.name, pdf_url)
                                
                                # send_document_message retourne data (peut être None en cas d'erreur)
                                # ou un dict avec les données de réponse
                                result = whatsapp_config.send_document_message(
                                    to_phone=phone,
                                    document_link=pdf_url,
                                    filename=f"{self.name}.pdf",
                                    caption=message
                                )
                                
                                # Vérifie si l'envoi a réussi
                                # send_document_message retourne data qui peut être None ou un dict
                                if result is None or (isinstance(result, dict) and result.get('error')):
                                    _logger.warning("Échec envoi PDF, résultat: %s", result)
                                    # Continue avec le fallback texte
                                    raise Exception("Échec envoi PDF")
                                else:
                                    _logger.info("PDF envoyé avec succès pour la facture %s", self.name)
                                    # Convertit result en format dict avec success pour la suite
                                    if not isinstance(result, dict):
                                        result = {'success': True, 'data': result}
                                    else:
                                        result['success'] = True
                                    # Marque immédiatement comme envoyé pour éviter les doublons
                                    self._mark_invoice_sent()
                                    
                            except Exception as e2:
                                _logger.warning("Impossible d'envoyer le PDF, erreur: %s. Envoi du lien de téléchargement.", str(e2))
                                # Dernier fallback : message texte avec lien
                                message = f"Bonjour {self.partner_id.name},\n\n"
                                message += f"Votre facture {self.name} a été validée.\n\n"
                                message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                                if self.invoice_date:
                                    message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                                message += f"\nTélécharger la facture : {pdf_url}"
                                message += "\n\nMerci de votre confiance !"
                                
                                result = whatsapp_config.send_text_to_partner(
                                    partner_id=self.partner_id.id,
                                    message_text=message
                                )
                                # Marque immédiatement comme envoyé si succès
                                if isinstance(result, dict) and result.get('success'):
                                    self._mark_invoice_sent()
                    else:
                        # Pas d'URL de base, envoie juste le message texte
                        message = f"Bonjour {self.partner_id.name},\n\n"
                        message += f"Votre facture {self.name} a été validée.\n\n"
                        message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                        if self.invoice_date:
                            message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                        message += "\nMerci de votre confiance !"
                        
                        result = whatsapp_config.send_text_to_partner(
                            partner_id=self.partner_id.id,
                            message_text=message
                        )
                        # Marque immédiatement comme envoyé si succès
                        if isinstance(result, dict) and result.get('success'):
                            self._mark_invoice_sent()
                except Exception as e:
                    _logger.warning("Erreur lors de la création de l'attachement PDF: %s", str(e))
                    # En cas d'erreur, envoie juste le message texte
                    message = f"Bonjour {self.partner_id.name},\n\n"
                    message += f"Votre facture {self.name} a été validée.\n\n"
                    message += f"Montant total : {self.amount_total:.0f} F CFA\n"
                    if self.invoice_date:
                        message += f"Date : {self.invoice_date.strftime('%d/%m/%Y')}\n"
                    message += "\nMerci de votre confiance !"
                    
                    result = whatsapp_config.send_text_to_partner(
                        partner_id=self.partner_id.id,
                        message_text=message
                    )
                    # Marque immédiatement comme envoyé si succès
                    if isinstance(result, dict) and result.get('success'):
                        self._mark_invoice_sent()
            
            # Crée ou met à jour la conversation
            conversation = self.env['whatsapp.conversation'].search([
                ('phone', '=', phone),
                ('contact_id', '=', self.partner_id.id)
            ], limit=1)
            
            if not conversation:
                conversation = self.env['whatsapp.conversation'].create({
                    'name': f"{self.partner_id.name} - {phone}",
                    'phone': phone,
                    'contact_id': self.partner_id.id,
                    'contact_name': self.partner_id.name,
                })
            
            # Normalise result pour avoir toujours un dict avec success
            if not isinstance(result, dict):
                # Si result n'est pas un dict, on le convertit
                if result is None:
                    result = {'success': False, 'error': 'Aucun résultat retourné'}
                else:
                    # Si result contient des données (ancien format), on considère que c'est un succès
                    result = {'success': True, 'data': result}
            
            # Lie le message à la conversation
            if result.get('message_record') and conversation:
                result['message_record'].conversation_id = conversation.id
                result['message_record'].contact_id = self.partner_id.id
            
            # Vérification finale : si le message n'a pas encore été marqué comme envoyé et que l'envoi a réussi
            # (sécurité supplémentaire au cas où _mark_invoice_sent() n'aurait pas été appelé)
            if result.get('success') and not self.sudo().x_whatsapp_invoice_sent:
                self._mark_invoice_sent()
                _logger.info("Facture WhatsApp envoyée avec succès pour %s (marquage final)", self.name)
            elif not result.get('success'):
                _logger.warning("Échec de l'envoi de la facture WhatsApp pour %s: %s", self.name, result.get('error', 'Erreur inconnue'))
                # Ne marque pas comme envoyé si l'envoi a échoué, pour permettre une nouvelle tentative
                
        except Exception as e:
            _logger.exception("Erreur lors de l'envoi de la facture WhatsApp pour %s", self.name)
            # Ne lève pas d'exception pour ne pas bloquer la validation de la facture
