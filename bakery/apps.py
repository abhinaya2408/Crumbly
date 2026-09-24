from django.apps import AppConfig


class BakeryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bakery"
    verbose_name = "Crumbly College Bakery"

    def ready(self):
        # Registers the post_save signal that creates Notifications
        # whenever an order's status changes. Importing here (rather
        # than at module load time) avoids circular-import issues.
        import bakery.signals  # noqa: F401
