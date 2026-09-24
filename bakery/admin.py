from django.contrib import admin

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


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("student_id", "user", "college_email", "phone", "department", "year")
    list_filter = ("department", "year")
    search_fields = ("student_id", "college_email", "user__first_name", "user__username")


@admin.register(BakeryMemberProfile)
class BakeryMemberProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "phone")
    search_fields = ("employee_id", "user__first_name", "user__username")


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("previous_status", "new_status", "changed_by", "note", "created_at")
    can_delete = False


@admin.register(CakeOrder)
class CakeOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "student",
        "flavor",
        "size",
        "cake_type",
        "status",
        "payment_status",
        "estimated_price",
        "required_date",
        "pickup_slot",
        "created_at",
    )
    list_filter = ("status", "payment_status", "flavor", "cake_type", "size", "required_date")
    search_fields = ("order_id", "student__student_id", "student__user__first_name")
    readonly_fields = ("order_id", "created_at", "updated_at")
    inlines = [OrderStatusHistoryInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("student", "order", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("student__student_id", "order__order_id")


@admin.register(PickupSlot)
class PickupSlotAdmin(admin.ModelAdmin):
    list_display = ("start_time", "end_time", "max_orders_per_day", "is_active")
    list_filter = ("is_active",)


@admin.register(ClosedDate)
class ClosedDateAdmin(admin.ModelAdmin):
    list_display = ("date", "reason")
    ordering = ("date",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity", "unit", "minimum_stock", "is_low_stock", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("name",)

    @admin.display(boolean=True, description="Low stock")
    def is_low_stock(self, obj):
        return obj.is_low_stock


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("order", "student", "overall_rating", "cake_quality_rating", "service_rating", "created_at")
    list_filter = ("overall_rating",)
    search_fields = ("order__order_id", "student__student_id")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "previous_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status",)
    search_fields = ("order__order_id",)
