import uuid
import logging
from django.db import transaction
from django.template import Template, Context
from notification.models import NotificationTemplate, UserContactProjection, NotificationLog, ProcessedEvent
from notification.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class NotificationManager:
    @staticmethod
    def process_event(event_id: str, routing_key: str, payload: dict, correlation_id: str = None):
        # 1. Inbox Pattern Check
        if ProcessedEvent.objects.filter(event_id=event_id).exists():
            logger.info(f"Event {event_id} already processed. Ignoring.")
            return
            
        with transaction.atomic():
            ProcessedEvent.objects.create(event_id=event_id)
            
            user_id = payload.get('user_id')
            if not user_id:
                # Some events might not have user_id at the root, depending on previous services
                # In a robust system, we ensure all domain events carry user_id if they trigger notifications.
                logger.warning(f"No user_id in payload for event {event_id}. Cannot send notification.")
                return

            # 2. Get User Projection
            user = UserContactProjection.objects.filter(user_id=user_id).first()
            if not user:
                logger.warning(f"No contact projection found for user {user_id}. Skipping.")
                return
                
            locale = payload.get('locale', 'vi')
            
            # 3. Find active templates for this event type
            templates = NotificationTemplate.objects.filter(
                event_type=routing_key,
                locale=locale,
                is_active=True
            )
            
            if not templates.exists():
                logger.info(f"No active templates found for {routing_key} ({locale}).")
                return
                
            # 4. Check user preferences and dispatch
            user_prefs = user.preferences.get(routing_key, {})
            
            for template in templates:
                channel = template.channel.upper()
                
                # Default to True if preference not explicitly set, 
                # except for PUSH which might require a token.
                channel_lower = channel.lower()
                is_enabled = user_prefs.get(channel_lower, True)
                
                if not is_enabled:
                    logger.info(f"User {user_id} opted out of {channel} for {routing_key}.")
                    continue
                    
                recipient = None
                if channel == 'EMAIL':
                    recipient = user.email
                elif channel == 'SMS':
                    recipient = user.phone
                elif channel == 'PUSH':
                    recipient = user.push_token
                    
                if not recipient:
                    logger.warning(f"User {user_id} missing contact info for {channel}.")
                    continue
                    
                # 5. Render Templates
                ctx = Context(payload)
                try:
                    subject = ''
                    if template.subject_template:
                        subject = Template(template.subject_template).render(ctx)
                    body = Template(template.body_template).render(ctx)
                except Exception as e:
                    logger.error(f"Template rendering failed for {template.id}: {e}")
                    continue
                
                # 6. Log as QUEUED
                log = NotificationLog.objects.create(
                    recipient=recipient,
                    channel=channel,
                    event_id=event_id,
                    correlation_id=correlation_id or event_id,
                    subject=subject,
                    body=body,
                    payload_snapshot=payload,
                    template_version=template.template_version,
                    provider_used='PENDING',
                    status='QUEUED'
                )
                
                # 7. Dispatch
                NotificationManager._dispatch(log)

    @staticmethod
    def _dispatch(log: NotificationLog):
        log.status = 'PROCESSING'
        log.save(update_fields=['status'])
        
        try:
            provider = ProviderFactory.get_provider(log.channel)
            log.provider_used = provider.__class__.__name__
            
            result = provider.send(log.recipient, log.subject, log.body)
            
            if result['status'] == 'SENT':
                log.status = 'SENT'
            else:
                log.status = 'FAILED'
                log.error_message = result.get('error_message')
                
        except Exception as e:
            log.status = 'FAILED'
            log.error_message = str(e)
            
        log.save()
        
        # If failed, retry worker will pick it up later
        if log.status == 'FAILED':
            # We don't instantly retry here, let the cron worker handle backoff
            log.status = 'RETRYING'
            log.save(update_fields=['status'])

    @staticmethod
    @transaction.atomic
    def process_user_event(routing_key: str, payload: dict):
        # Build local projection
        user_id = payload.get('user_id') or payload.get('id')
        if not user_id:
            return
            
        projection, _ = UserContactProjection.objects.get_or_create(user_id=user_id)
        
        if 'email' in payload:
            projection.email = payload['email']
        if 'phone' in payload:
            projection.phone = payload['phone']
        if 'push_token' in payload:
            projection.push_token = payload['push_token']
        if 'preferences' in payload:
            projection.preferences = payload['preferences']
            
        projection.save()
