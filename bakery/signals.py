"""
Whenever a CakeOrder's status changes, automatically create a
Notification for the student who placed it. This fires no matter
which code path changed the status — the bakery status-update view,
the student cancel view, or even the Django admin — since it's a
model-level signal, not view-level logic.

We use a pre_save + post_save pair:
  * pre_save remembers what the status was BEFORE this save (by
    re-reading the row from the database), stashed on the instance.
  * post_save compares that to the new status and, if it changed,
    creates the matching Notification.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import CakeOrder, Notification

STATUS_MESSAGES = {
    "ACCEPTED": lambda order_id: f"🎂 Your Crumbly order {order_id} has been accepted.",
    "PREPARING": lambda order_id: f"👩‍🍳 Your cake order {order_id} is now being prepared.",
    "READY": lambda order_id: f"🎂 Your cake order {order_id} is ready for collection!",
    "COLLECTED": lambda order_id: f"Your order {order_id} has been collected. Thank you for choosing Crumbly!",
    "COMPLETED": lambda order_id: f"Your order {order_id} is complete. We'd love to hear how it went — leave a review!",
    "REJECTED": lambda order_id: f"Unfortunately, your cake order {order_id} could not be accepted.",
    "CANCELLED": lambda order_id: f"Your cake order {order_id} has been cancelled.",
}

STATUS_NOTIFICATION_TYPE = {
    "ACCEPTED": "ORDER_ACCEPTED",
    "PREPARING": "ORDER_PREPARING",
    "READY": "ORDER_READY",
    "COLLECTED": "ORDER_COLLECTED",
    "COMPLETED": "ORDER_COLLECTED",
    "REJECTED": "ORDER_REJECTED",
    "CANCELLED": "ORDER_CANCELLED",
}


@receiver(pre_save, sender=CakeOrder)
def _remember_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = CakeOrder.objects.only("status").get(pk=instance.pk).status
        except CakeOrder.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=CakeOrder)
def _create_status_notification(sender, instance, created, **kwargs):
    if created:
        # A fresh order still gets an "order placed" confirmation.
        Notification.objects.create(
            student=instance.student,
            order=instance,
            message=f"🎂 Your order {instance.order_id} has been placed and is awaiting confirmation.",
            notification_type="ORDER_PLACED",
        )
        return

    previous_status = getattr(instance, "_previous_status", None)
    if previous_status == instance.status:
        return  # status didn't actually change, nothing to notify

    message_fn = STATUS_MESSAGES.get(instance.status)
    if not message_fn:
        return

    Notification.objects.create(
        student=instance.student,
        order=instance,
        message=message_fn(instance.order_id),
        notification_type=STATUS_NOTIFICATION_TYPE.get(instance.status, "ORDER_ACCEPTED"),
    )
