import json
from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    BakeryMemberProfile,
    CakeOrder,
    ClosedDate,
    InventoryItem,
    Notification,
    OrderStatusHistory,
    PickupSlot,
    Review,
    StudentProfile,
)
from .pricing import DECORATION_PRICES, calculate_price


# ==========================================================
# Auth / profile serializers
# ==========================================================
class StudentRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    student_id = serializers.CharField(max_length=40)
    email = serializers.EmailField()
    phone = serializers.RegexField(r"^\d{10}$", error_messages={"invalid": "Enter a valid 10-digit phone number."})
    password = serializers.CharField(write_only=True)
    department = serializers.CharField(max_length=80, required=False, allow_blank=True)
    year = serializers.ChoiceField(choices=StudentProfile.YEAR_CHOICES, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        domain = settings.COLLEGE_EMAIL_DOMAIN.lower()
        if not value.endswith(domain):
            raise serializers.ValidationError("Please use your official college email address.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_student_id(self, value):
        value = value.strip()
        if StudentProfile.objects.filter(student_id__iexact=value).exists():
            raise serializers.ValidationError("This Student ID is already registered.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        # Django's User.username is unique — the college email doubles
        # nicely as the username since it is already guaranteed unique.
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            first_name=validated_data["name"].strip(),
        )
        profile = StudentProfile.objects.create(
            user=user,
            student_id=validated_data["student_id"].strip(),
            phone=validated_data["phone"],
            college_email=email,
            department=validated_data.get("department", "").strip(),
            year=validated_data.get("year", ""),
        )
        return profile


class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.first_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["student_id", "full_name", "email", "phone", "department", "year"]


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Students may only edit a small set of non-sensitive fields.
    student_id / college_email / the linked User account are NOT
    editable here — changing those would need an admin/support flow.
    """

    class Meta:
        model = StudentProfile
        fields = ["phone", "department", "year"]

    def validate_phone(self, value):
        import re

        if not re.match(r"^\d{10}$", value):
            raise serializers.ValidationError("Enter a valid 10-digit phone number.")
        return value


class BakeryMemberProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.first_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = BakeryMemberProfile
        fields = ["employee_id", "full_name", "email", "phone"]


class MeSerializer(serializers.Serializer):
    """Returned by GET /api/auth/me/ — tells the frontend who is logged in and in what role."""

    role = serializers.CharField()
    profile = serializers.SerializerMethodField()

    def get_profile(self, obj):
        user = obj["user"]
        if obj["role"] == "student":
            return StudentProfileSerializer(user.student_profile).data
        return BakeryMemberProfileSerializer(user.bakery_profile).data


# ==========================================================
# Pickup slots
# ==========================================================
class PickupSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupSlot
        fields = ["id", "start_time", "end_time", "max_orders_per_day", "is_active"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError("End time must be after start time.")
        return attrs


class ClosedDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClosedDate
        fields = ["id", "date", "reason"]


# ==========================================================
# Cake order serializers
# ==========================================================
class CakeOrderCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST /api/orders/. Accepts multipart/form-data because a
    reference image file may be attached alongside the text fields.

    `decorations` arrives as a JSON-encoded string (e.g. '["Sprinkles",
    "Fresh Flowers"]') because that's how the frontend's FormData sends
    a list of values, then gets parsed back into a real list here.

    `pickup_slot` is the numeric ID of a PickupSlot — availability for
    the chosen `required_date` is re-checked here server-side (never
    trust the frontend's idea of what's still bookable).
    """

    decorations = serializers.CharField(required=False, allow_blank=True, write_only=True)
    pickup_slot = serializers.PrimaryKeyRelatedField(queryset=PickupSlot.objects.filter(is_active=True))
    reordered_from = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = CakeOrder
        fields = [
            "flavor",
            "size",
            "cake_type",
            "cream",
            "decorations",
            "cake_message",
            "special_instructions",
            "reference_image",
            "pickup_slot",
            "required_date",
            "reordered_from",
        ]

    def validate_decorations(self, value):
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            # also accept a plain comma-separated string as a fallback
            parsed = [d.strip() for d in value.split(",") if d.strip()]
        if not isinstance(parsed, list):
            raise serializers.ValidationError("Decorations must be a list.")
        invalid = [d for d in parsed if d not in DECORATION_PRICES]
        if invalid:
            raise serializers.ValidationError(f"Unknown decoration(s): {', '.join(invalid)}")
        return parsed

    def validate_required_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Please choose a date that is today or later.")
        if ClosedDate.objects.filter(date=value).exists():
            raise serializers.ValidationError("The bakery is closed on this date. Please choose another date.")
        return value

    def validate_reference_image(self, value):
        if value is None:
            return value
        allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
        content_type = getattr(value, "content_type", "")
        if content_type not in allowed_types:
            raise serializers.ValidationError("Only JPG, PNG, or WEBP images are allowed.")
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Please upload an image smaller than 2 MB.")
        return value

    def validate_reordered_from(self, value):
        if not value:
            return None
        try:
            return CakeOrder.objects.get(order_id=value, student=self.context["request"].user.student_profile)
        except CakeOrder.DoesNotExist:
            raise serializers.ValidationError("Original order not found.")

    def validate(self, attrs):
        # Cross-field check: does the chosen slot still have room on the chosen date?
        slot = attrs.get("pickup_slot")
        required_date = attrs.get("required_date")
        if slot and required_date:
            if slot.remaining_capacity_for_date(required_date) <= 0:
                raise serializers.ValidationError(
                    {"pickup_slot": "This pickup slot is fully booked for the selected date. Please choose another."}
                )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        student_profile = request.user.student_profile

        decorations = validated_data.pop("decorations", [])
        reordered_from = validated_data.pop("reordered_from", None)
        slot = validated_data["pickup_slot"]

        price = calculate_price(
            flavor=validated_data["flavor"],
            size=validated_data["size"],
            decorations=decorations,
        )

        order = CakeOrder.objects.create(
            student=student_profile,
            order_id=_generate_order_id(),
            decorations=decorations,
            estimated_price=price,
            required_time=slot.start_time,
            reordered_from=reordered_from,
            **validated_data,
        )
        return order


def _generate_order_id():
    """Generates a human-friendly, unique order ID like CRB-1024."""
    last = CakeOrder.objects.order_by("-id").first()
    next_number = 1024
    if last:
        try:
            next_number = int(last.order_id.replace("CRB-", "")) + 1
        except ValueError:
            next_number = CakeOrder.objects.count() + 1024
    candidate = f"CRB-{next_number}"
    # Extremely unlikely, but guard against a collision anyway.
    while CakeOrder.objects.filter(order_id=candidate).exists():
        next_number += 1
        candidate = f"CRB-{next_number}"
    return candidate


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = ["previous_status", "new_status", "changed_by_name", "note", "created_at"]

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return "System"
        if hasattr(obj.changed_by, "bakery_profile"):
            return obj.changed_by.first_name or "Bakery Team"
        return obj.changed_by.first_name or obj.changed_by.username


class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.first_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "student_name",
            "overall_rating",
            "cake_quality_rating",
            "service_rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "student_name", "created_at"]

    def validate(self, attrs):
        order = self.context["order"]
        if order.status != "COMPLETED":
            raise serializers.ValidationError("You can only review an order after it's been completed.")
        if hasattr(order, "review"):
            raise serializers.ValidationError("This order has already been reviewed.")
        return attrs


class CakeOrderSerializer(serializers.ModelSerializer):
    """Full, read-only representation of an order — used everywhere an
    order is displayed (my orders, order details, bakery dashboard)."""

    student_name = serializers.CharField(source="student.user.first_name", read_only=True)
    student_id_display = serializers.CharField(source="student.student_id", read_only=True)
    student_email = serializers.CharField(source="student.college_email", read_only=True)
    student_phone = serializers.CharField(source="student.phone", read_only=True)
    reference_image = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    pickup_slot_label = serializers.SerializerMethodField()
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    review = ReviewSerializer(read_only=True)
    can_cancel = serializers.SerializerMethodField()
    can_reorder = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    reordered_from = serializers.CharField(source="reordered_from.order_id", read_only=True, default=None)

    class Meta:
        model = CakeOrder
        fields = [
            "order_id",
            "student_name",
            "student_id_display",
            "student_email",
            "student_phone",
            "flavor",
            "size",
            "cake_type",
            "cream",
            "decorations",
            "cake_message",
            "special_instructions",
            "reference_image",
            "pickup_slot",
            "pickup_slot_label",
            "required_date",
            "required_time",
            "estimated_price",
            "status",
            "status_label",
            "payment_status",
            "rejection_reason",
            "cancellation_reason",
            "reordered_from",
            "status_history",
            "review",
            "can_cancel",
            "can_reorder",
            "can_review",
            "created_at",
            "updated_at",
        ]

    def get_reference_image(self, obj):
        if not obj.reference_image:
            return None
        request = self.context.get("request")
        url = obj.reference_image.url
        return request.build_absolute_uri(url) if request else url

    def get_status_label(self, obj):
        return dict(CakeOrder.STATUS_CHOICES).get(obj.status, obj.status)

    def get_pickup_slot_label(self, obj):
        if not obj.pickup_slot:
            return None
        return f"{obj.pickup_slot.start_time.strftime('%I:%M %p')} – {obj.pickup_slot.end_time.strftime('%I:%M %p')}"

    def get_can_cancel(self, obj):
        return obj.status in CANCELLABLE_STATUSES

    def get_can_reorder(self, obj):
        return obj.status in REORDERABLE_STATUSES

    def get_can_review(self, obj):
        return obj.status == "COMPLETED" and not hasattr(obj, "review")


CANCELLABLE_STATUSES = {"PENDING", "ACCEPTED"}
REORDERABLE_STATUSES = {"COMPLETED", "COLLECTED", "REJECTED", "CANCELLED"}


class ReorderPrefillSerializer(serializers.ModelSerializer):
    """Returned by POST /api/orders/<order_id>/reorder/ — the previous
    order's cake configuration, for the frontend to pre-fill the
    customize page with (the student still reviews/changes it and
    submits a brand-new order through the normal create flow)."""

    class Meta:
        model = CakeOrder
        fields = [
            "order_id",
            "flavor",
            "size",
            "cake_type",
            "cream",
            "decorations",
            "cake_message",
            "special_instructions",
        ]


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=CakeOrder.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)

    # Only these forward transitions are allowed — mirrors the
    # bakery dashboard's action buttons exactly.
    ALLOWED_TRANSITIONS = {
        "PENDING": {"ACCEPTED", "REJECTED"},
        "ACCEPTED": {"PREPARING"},
        "PREPARING": {"READY"},
        "READY": {"COLLECTED"},
        "COLLECTED": {"COMPLETED"},
    }

    def validate(self, attrs):
        order = self.context["order"]
        new_status = attrs["status"]
        allowed = self.ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise serializers.ValidationError(
                f"Cannot move an order from '{order.status}' to '{new_status}'."
            )
        if new_status == "REJECTED" and not attrs.get("reason"):
            raise serializers.ValidationError({"reason": "Please provide a reason for rejecting this order."})
        return attrs


class OrderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)

    def validate(self, attrs):
        order = self.context["order"]
        if order.status not in CANCELLABLE_STATUSES:
            raise serializers.ValidationError(
                f"Orders can only be cancelled while they're Pending or Accepted (this order is {order.status.title()})."
            )
        return attrs


class PaymentStatusUpdateSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(choices=CakeOrder.PAYMENT_STATUS_CHOICES)


# ==========================================================
# Notifications
# ==========================================================
class NotificationSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source="order.order_id", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "order_id", "message", "notification_type", "is_read", "created_at"]


# ==========================================================
# Bakery dashboard
# ==========================================================
class DashboardSerializer(serializers.Serializer):
    today_orders = serializers.IntegerField()
    pending = serializers.IntegerField()
    accepted = serializers.IntegerField()
    preparing = serializers.IntegerField()
    ready = serializers.IntegerField()
    collected = serializers.IntegerField()
    completed = serializers.IntegerField()
    rejected = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    total = serializers.IntegerField()
    revenue_today = serializers.IntegerField()
    revenue_week = serializers.IntegerField()
    revenue_month = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()


# ==========================================================
# Inventory
# ==========================================================
class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "category",
            "quantity",
            "unit",
            "minimum_stock",
            "is_active",
            "is_low_stock",
            "updated_at",
        ]
