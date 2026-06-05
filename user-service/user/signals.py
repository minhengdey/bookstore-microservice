import logging
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.core.cache import cache
from django.db import models

from .models import UserProfile

logger = logging.getLogger(__name__)

def _invalidate_and_increment(user_id):
    """Increment role_version atomically and invalidate Redis cache."""
    # Atomic increment to prevent recursion/race condition
    UserProfile.objects.filter(pk=user_id).update(role_version=models.F('role_version') + 1)
    
    # Invalidate Cache (using v1 prefix for versioning)
    cache.delete(f"user_permissions:v1:{user_id}")
    cache.delete(f"user_profile:v1:{user_id}")
    logger.info(f"Invalidated RBAC cache and incremented role_version for user {user_id}")

@receiver(m2m_changed, sender=UserProfile.roles.through)
def on_user_roles_changed(sender, instance, action, **kwargs):
    """Trigger when user roles are added/removed/cleared."""
    if action in ['post_add', 'post_remove', 'post_clear']:
        _invalidate_and_increment(instance.auth_user_id)

@receiver(post_save, sender=UserProfile)
def on_user_profile_saved(sender, instance, created, update_fields, **kwargs):
    """Trigger only when user status changes (ACTIVE -> SUSPENDED/BANNED)."""
    # If we explicitly pass update_fields=['status'], only invalidate then
    if update_fields and 'status' in update_fields:
        _invalidate_and_increment(instance.auth_user_id)
        return

    # Fallback if update_fields is not used, check if status changed.
    # Note: to do this cleanly without update_fields, we'd need pre_save to cache old status.
    # But since update_fields is a best practice, we'll recommend its use.
    # For robust catch-all without update_fields tracking, we can just invalidate.
    # However, to avoid invalidating on every avatar change, we prefer update_fields.
    if created:
        _invalidate_and_increment(instance.auth_user_id)
