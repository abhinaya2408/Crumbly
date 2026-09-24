from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models


# ==========================================================
# Profiles
# ==========================================================
class StudentProfile(models.Model):
    """Extra, student-only fields attached to a Django User."""

    YEAR_CHOICES = [
        ("1", "1st Year"),
        ("2", "2nd Year"),
        ("3", "3rd Year"),
        ("4", "4th Year"),
        ("PG", "Postgraduate"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    student_id = models.CharField(max_length=40, unique=True)
    phone = models.CharField(max_length=15)
    college_email = models.EmailField(unique=True)
    department = models.CharField(max_length=80, blank=True)
    year = models.CharField(max_length=2, choices=YEAR_CHOICES, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.student_id})"


class BakeryMemberProfile(models.Model):
    """Extra, bakery-staff-only fields attached to a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="bakery_profile")
    phone = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=40, unique=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"


# ==========================================================
# Pickup slots
# ==========================================================
class PickupSlot(models.Model):
    """
    A recurring daily pickup-time template (e.g. every day, 10:00–10:30,
    up to 3 orders). Availability for a specific date is computed by
    counting how many CakeOrders already use this slot on that date
    (see PickupSlot.remaining_capacity_for_date below).
    """

    start_time = models.TimeField()
    end_time = models.TimeField()
    max_orders_per_day = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.start_time.strftime('%I:%M %p')} – {self.end_time.strftime('%I:%M %p')} ({self.max_orders_per_day} slots)"

    def booked_count_for_date(self, date):
        return self.orders.filter(
            required_date=date
        ).exclude(status__in=["REJECTED", "CANCELLED"]).count()

    def remaining_capacity_for_date(self, date):
        return max(self.max_orders_per_day - self.booked_count_for_date(date), 0)


class ClosedDate(models.Model):
    """A date the bakery is closed (holiday, exam break, etc.) — no pickups allowed."""

    date = models.DateField(unique=True)
    reason = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} ({self.reason or 'Closed'})"


# ==========================================================
# Cake order
# ==========================================================
def validate_reference_image_size(file):
    max_bytes = 2 * 1024 * 1024
    if file.size > max_bytes:
        from django.core.exceptions import ValidationError

        raise ValidationError("Please upload an image smaller than 2 MB.")


class CakeOrder(models.Model):
    FLAVOR_CHOICES = [
        ("Chocolate", "Chocolate"),
        ("Vanilla", "Vanilla"),
        ("Red Velvet", "Red Velvet"),
        ("Black Forest", "Black Forest"),
        ("Butterscotch", "Butterscotch"),
        ("Strawberry", "Strawberry"),
    ]
    SIZE_CHOICES = [
        ("500g", "500g"),
        ("1 Kg", "1 Kg"),
        ("1.5 Kg", "1.5 Kg"),
        ("2 Kg", "2 Kg"),
    ]
    CAKE_TYPE_CHOICES = [
        ("EGG", "Egg"),
        ("EGGLESS", "Eggless"),
    ]
    CREAM_CHOICES = [
        ("Chocolate", "Chocolate"),
        ("Vanilla", "Vanilla"),
        ("Strawberry", "Strawberry"),
        ("Butterscotch", "Butterscotch"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("PREPARING", "Preparing"),
        ("READY", "Ready"),
        ("COLLECTED", "Collected"),
        ("COMPLETED", "Completed"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    # NOTE: there is intentionally NO "shape" field anywhere in this
    # project — cake shape customization was removed per spec.
    order_id = models.CharField(max_length=20, unique=True, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="orders")

    flavor = models.CharField(max_length=30, choices=FLAVOR_CHOICES)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    cake_type = models.CharField(max_length=10, choices=CAKE_TYPE_CHOICES)
    cream = models.CharField(max_length=30, choices=CREAM_CHOICES)
    decorations = models.JSONField(default=list, blank=True)

    cake_message = models.CharField(max_length=50, blank=True)
    special_instructions = models.TextField(blank=True)

    reference_image = models.ImageField(
        upload_to="cake-references/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_reference_image_size,
        ],
    )

    pickup_slot = models.ForeignKey(
        PickupSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    required_date = models.DateField()
    # Denormalized copy of pickup_slot.start_time at the moment of booking,
    # so the order keeps its original pickup time even if the slot
    # template is edited/deleted later.
    required_time = models.TimeField()

    estimated_price = models.PositiveIntegerField()

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default="PENDING")

    rejection_reason = models.CharField(max_length=200, blank=True)
    cancellation_reason = models.CharField(max_length=200, blank=True)

    # Set when this order was created via "Reorder" from a previous one —
    # purely informational, doesn't affect behaviour.
    reordered_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reorders"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_id} — {self.student} ({self.status})"


class OrderStatusHistory(models.Model):
    """A full audit trail of every status change on an order."""

    order = models.ForeignKey(CakeOrder, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=12, blank=True)
    new_status = models.CharField(max_length=12)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Order status histories"

    def __str__(self):
        return f"{self.order.order_id}: {self.previous_status or '—'} → {self.new_status}"


# ==========================================================
# Notifications
# ==========================================================
class Notification(models.Model):
    TYPE_CHOICES = [
        ("ORDER_PLACED", "Order Placed"),
        ("ORDER_ACCEPTED", "Order Accepted"),
        ("ORDER_REJECTED", "Order Rejected"),
        ("ORDER_PREPARING", "Order Preparing"),
        ("ORDER_READY", "Order Ready"),
        ("ORDER_COLLECTED", "Order Collected"),
        ("ORDER_CANCELLED", "Order Cancelled"),
        ("PICKUP_REMINDER", "Pickup Reminder"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="notifications")
    order = models.ForeignKey(CakeOrder, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} → {self.student} ({self.order.order_id})"


# ==========================================================
# Inventory
# ==========================================================
class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ("CREAM", "Cream"),
        ("FLAVOR_BASE", "Flavor / Base"),
        ("DECORATION", "Decoration"),
        ("PACKAGING", "Packaging"),
        ("OTHER", "Other"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default="OTHER")
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")
    minimum_stock = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity < self.minimum_stock


# ==========================================================
# Reviews
# ==========================================================
class Review(models.Model):
    order = models.OneToOneField(CakeOrder, on_delete=models.CASCADE, related_name="review")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="reviews")

    overall_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    cake_quality_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    service_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for {self.order.order_id} — {self.overall_rating}★"
