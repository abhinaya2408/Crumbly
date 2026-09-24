"""
bakery/views.py

All Django REST Framework API views for Crumbly, grouped into
sections:
  1. Authentication (student + bakery, separate everywhere)
  2. Student profile
  3. Orders (create / list / detail / status / cancel / reorder / payment / review)
  4. Bakery dashboard + order list (bakery-staff only)
  5. Pickup slots + closed dates
  6. Inventory
  7. Analytics
  8. Notifications

See README.md → "Authentication approach" for why the three
login/register endpoints are @csrf_exempt while everything else
enforces Django's normal CSRF protection.
"""

from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from .models import (
    CakeOrder,
    ClosedDate,
    InventoryItem,
    Notification,
    OrderStatusHistory,
    PickupSlot,
    Review,
)
from .permissions import IsBakeryMember, IsStudent
from .serializers import (
    BakeryMemberProfileSerializer,
    CakeOrderCreateSerializer,
    CakeOrderSerializer,
    ClosedDateSerializer,
    DashboardSerializer,
    InventoryItemSerializer,
    MeSerializer,
    NotificationSerializer,
    OrderCancelSerializer,
    OrderStatusUpdateSerializer,
    PaymentStatusUpdateSerializer,
    PickupSlotSerializer,
    ReorderPrefillSerializer,
    ReviewSerializer,
    StudentProfileSerializer,
    StudentProfileUpdateSerializer,
    StudentRegisterSerializer,
)


def friendly_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler so every error response has
    a consistent, human-friendly shape:  {"detail": "..."} or
    {"errors": {...field errors...}}. Keeps Django tracebacks from
    ever reaching the browser (spec section "Error Handling").
    """
    response = exception_handler(exc, context)
    if response is None:
        # Something genuinely unexpected — never leak the traceback.
        return Response(
            {"detail": "Something went wrong. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        response.data = {"errors": response.data}
    elif isinstance(response.data, dict) and "detail" not in response.data:
        response.data = {"errors": response.data}

    defaults = {
        400: "Please check the information you entered.",
        401: "Please log in.",
        403: "You do not have permission to perform this action.",
        404: "The item you're looking for could not be found.",
        500: "Something went wrong. Please try again.",
    }
    if "detail" not in response.data and response.status_code in defaults:
        response.data["detail"] = defaults[response.status_code]

    return response


# ==========================================================
# 1. AUTHENTICATION
# ==========================================================
@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class StudentRegisterView(APIView):
    """POST /api/auth/student/register/ — public."""

    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        serializer = StudentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        login(request, profile.user)
        return Response(
            {
                "detail": "Account created! Welcome to Crumbly 🎂",
                "profile": MeSerializer({"role": "student", "user": profile.user}).data,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class StudentLoginView(APIView):
    """POST /api/auth/student/login/ — public. Rejects bakery accounts."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        if not email or not password:
            return Response({"detail": "Email and password are required."}, status=400)

        user = authenticate(request, username=email, password=password)
        if user is None or not hasattr(user, "student_profile"):
            return Response({"detail": "Incorrect email or password."}, status=401)

        login(request, user)
        first_name = user.first_name.split(" ")[0] if user.first_name else "there"
        return Response(
            {
                "detail": f"Welcome back, {first_name}! 🎂",
                "profile": MeSerializer({"role": "student", "user": user}).data,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class BakeryLoginView(APIView):
    """POST /api/auth/bakery/login/ — public. Rejects student accounts."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        if not email or not password:
            return Response({"detail": "Email and password are required."}, status=400)

        user = authenticate(request, username=email, password=password)
        if user is None or not hasattr(user, "bakery_profile"):
            return Response({"detail": "Incorrect email or password."}, status=401)

        login(request, user)
        return Response(
            {
                "detail": "Welcome back to the Crumbly dashboard!",
                "profile": MeSerializer({"role": "bakery", "user": user}).data,
            }
        )


class LogoutView(APIView):
    """POST /api/auth/student/logout/ and /api/auth/bakery/logout/ — shared implementation."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    """GET /api/auth/me/ — tells the frontend who is currently logged in (or 401)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if hasattr(request.user, "student_profile"):
            role = "student"
        elif hasattr(request.user, "bakery_profile"):
            role = "bakery"
        else:
            return Response({"detail": "Unknown account type."}, status=403)
        return Response(MeSerializer({"role": role, "user": request.user}).data)


# ==========================================================
# 2. STUDENT PROFILE
# ==========================================================
class StudentProfileView(APIView):
    """GET/PATCH /api/students/me/ — a student viewing/editing their own profile."""

    permission_classes = [IsStudent]

    def get(self, request):
        return Response(StudentProfileSerializer(request.user.student_profile).data)

    def patch(self, request):
        profile = request.user.student_profile
        serializer = StudentProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StudentProfileSerializer(profile).data)


# ==========================================================
# 3. ORDERS
# ==========================================================
class OrderCreateView(APIView):
    """POST /api/orders/ — student only. multipart/form-data."""

    permission_classes = [IsStudent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = CakeOrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        OrderStatusHistory.objects.create(
            order=order, previous_status="", new_status="PENDING", changed_by=request.user, note="Order placed."
        )
        output = CakeOrderSerializer(order, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class MyOrdersView(APIView):
    """GET /api/orders/my/ — student only, their own orders."""

    permission_classes = [IsStudent]

    def get(self, request):
        orders = CakeOrder.objects.filter(student=request.user.student_profile)
        return Response(CakeOrderSerializer(orders, many=True, context={"request": request}).data)


class OrderDetailView(APIView):
    """
    GET /api/orders/<order_id>/
    A student may only view their OWN order. A bakery member may view
    any order (needed to fulfil it).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = _get_order_or_404(order_id)
        if hasattr(request.user, "student_profile"):
            if order.student_id != request.user.student_profile.id:
                return Response({"detail": "This order doesn't belong to your account."}, status=403)
        elif not hasattr(request.user, "bakery_profile"):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)

        return Response(CakeOrderSerializer(order, context={"request": request}).data)


class OrderStatusUpdateView(APIView):
    """PATCH /api/orders/<order_id>/status/ — bakery only. Optional `reason` (required for REJECTED)."""

    permission_classes = [IsBakeryMember]

    def patch(self, request, order_id):
        order = _get_order_or_404(order_id)
        serializer = OrderStatusUpdateSerializer(data=request.data, context={"order": order})
        serializer.is_valid(raise_exception=True)

        previous_status = order.status
        new_status = serializer.validated_data["status"]
        reason = serializer.validated_data.get("reason", "")

        order.status = new_status
        if new_status == "REJECTED":
            order.rejection_reason = reason
        order.save()  # bakery/signals.py creates the Notification automatically

        OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=request.user,
            note=reason,
        )

        return Response(CakeOrderSerializer(order, context={"request": request}).data)


class OrderCancelView(APIView):
    """POST /api/orders/<order_id>/cancel/ — student only, must own the order."""

    permission_classes = [IsStudent]

    def post(self, request, order_id):
        order = _get_order_or_404(order_id)
        if order.student_id != request.user.student_profile.id:
            return Response({"detail": "This order doesn't belong to your account."}, status=403)

        serializer = OrderCancelSerializer(data=request.data, context={"order": order})
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        previous_status = order.status
        order.status = "CANCELLED"
        order.cancellation_reason = reason
        order.save()  # triggers the ORDER_CANCELLED notification via signals.py

        OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status="CANCELLED",
            changed_by=request.user,
            note=reason,
        )

        return Response(CakeOrderSerializer(order, context={"request": request}).data)


class OrderReorderView(APIView):
    """
    POST /api/orders/<order_id>/reorder/ — student only, must own the
    order, and the order must be in a final state (completed/collected/
    rejected/cancelled). Returns the previous cake configuration for
    the frontend to pre-fill the customize page with — this does NOT
    create a new order by itself; the student still reviews it, picks
    a new pickup date/slot, and submits normally.
    """

    permission_classes = [IsStudent]

    def post(self, request, order_id):
        order = _get_order_or_404(order_id)
        if order.student_id != request.user.student_profile.id:
            return Response({"detail": "This order doesn't belong to your account."}, status=403)

        from .serializers import REORDERABLE_STATUSES

        if order.status not in REORDERABLE_STATUSES:
            return Response(
                {"detail": "Only completed, collected, rejected, or cancelled orders can be reordered."},
                status=400,
            )

        return Response(ReorderPrefillSerializer(order).data)


class OrderPaymentUpdateView(APIView):
    """PATCH /api/orders/<order_id>/payment/ — bakery only. Marks an order paid/failed/refunded."""

    permission_classes = [IsBakeryMember]

    def patch(self, request, order_id):
        order = _get_order_or_404(order_id)
        serializer = PaymentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.payment_status = serializer.validated_data["payment_status"]
        order.save(update_fields=["payment_status", "updated_at"])
        return Response(CakeOrderSerializer(order, context={"request": request}).data)


class OrderReviewView(APIView):
    """
    GET  /api/orders/<order_id>/review/ — the order's review, if any.
    POST /api/orders/<order_id>/review/ — student only, must own the
         order, and the order must be COMPLETED with no existing review.
    """

    permission_classes = [IsStudent]

    def get(self, request, order_id):
        order = _get_order_or_404(order_id)
        if order.student_id != request.user.student_profile.id:
            return Response({"detail": "This order doesn't belong to your account."}, status=403)
        if not hasattr(order, "review"):
            return Response({"detail": "No review yet for this order."}, status=404)
        return Response(ReviewSerializer(order.review).data)

    def post(self, request, order_id):
        order = _get_order_or_404(order_id)
        if order.student_id != request.user.student_profile.id:
            return Response({"detail": "This order doesn't belong to your account."}, status=403)

        serializer = ReviewSerializer(data=request.data, context={"order": order})
        serializer.is_valid(raise_exception=True)
        review = serializer.save(order=order, student=request.user.student_profile)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


def _get_order_or_404(order_id):
    return get_object_or_404(CakeOrder, order_id=order_id)


# ==========================================================
# 4. BAKERY DASHBOARD
# ==========================================================
class BakeryDashboardView(APIView):
    """GET /api/bakery/dashboard/ — bakery only. Real counts, never hardcoded."""

    permission_classes = [IsBakeryMember]

    def get(self, request):
        orders = CakeOrder.objects.all()
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        def revenue_since(start_date):
            total = orders.filter(
                created_at__date__gte=start_date, status__in=["COMPLETED", "COLLECTED"]
            ).aggregate(total=Sum("estimated_price"))["total"]
            return total or 0

        low_stock_count = sum(1 for item in InventoryItem.objects.filter(is_active=True) if item.is_low_stock)

        counts = {
            "today_orders": orders.filter(created_at__date=today).count(),
            "pending": orders.filter(status="PENDING").count(),
            "accepted": orders.filter(status="ACCEPTED").count(),
            "preparing": orders.filter(status="PREPARING").count(),
            "ready": orders.filter(status="READY").count(),
            "collected": orders.filter(status="COLLECTED").count(),
            "completed": orders.filter(status="COMPLETED").count(),
            "rejected": orders.filter(status="REJECTED").count(),
            "cancelled": orders.filter(status="CANCELLED").count(),
            "total": orders.count(),
            "revenue_today": revenue_since(today),
            "revenue_week": revenue_since(week_start),
            "revenue_month": revenue_since(month_start),
            "low_stock_count": low_stock_count,
        }
        return Response(DashboardSerializer(counts).data)


class BakeryOrdersListView(APIView):
    """
    GET /api/bakery/orders/ — bakery only.
    Optional: ?status=PENDING  ?search=CRB-1024 (or a student name)
              ?date=YYYY-MM-DD  ?sort=newest|oldest|pickup_time
    """

    permission_classes = [IsBakeryMember]

    def get(self, request):
        orders = CakeOrder.objects.select_related("student", "student__user").all()

        status_filter = request.query_params.get("status")
        if status_filter:
            orders = orders.filter(status=status_filter.upper())

        search = request.query_params.get("search")
        if search:
            orders = orders.filter(
                Q(order_id__icontains=search)
                | Q(student__user__first_name__icontains=search)
                | Q(student__student_id__icontains=search)
            )

        date_filter = request.query_params.get("date")
        if date_filter:
            orders = orders.filter(required_date=date_filter)

        sort = request.query_params.get("sort")
        if sort == "oldest":
            orders = orders.order_by("created_at")
        elif sort == "pickup_time":
            orders = orders.order_by("required_date", "required_time")
        else:
            orders = orders.order_by("-created_at")

        return Response(CakeOrderSerializer(orders, many=True, context={"request": request}).data)


# ==========================================================
# 5. PICKUP SLOTS + CLOSED DATES
# ==========================================================
class PickupSlotListCreateView(APIView):
    """GET (any authenticated) / POST (bakery only) /api/bakery/pickup-slots/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsBakeryMember()]
        return [IsAuthenticated()]

    def get(self, request):
        slots = PickupSlot.objects.all()
        return Response(PickupSlotSerializer(slots, many=True).data)

    def post(self, request):
        serializer = PickupSlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot = serializer.save()
        return Response(PickupSlotSerializer(slot).data, status=status.HTTP_201_CREATED)


class PickupSlotDetailView(APIView):
    """PATCH/DELETE /api/bakery/pickup-slots/<id>/ — bakery only."""

    permission_classes = [IsBakeryMember]

    def patch(self, request, pk):
        slot = get_object_or_404(PickupSlot, pk=pk)
        serializer = PickupSlotSerializer(slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        slot = get_object_or_404(PickupSlot, pk=pk)
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClosedDateListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsBakeryMember()]
        return [IsAuthenticated()]

    def get(self, request):
        closed_dates = ClosedDate.objects.filter(date__gte=date.today())
        return Response(ClosedDateSerializer(closed_dates, many=True).data)

    def post(self, request):
        serializer = ClosedDateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        closed = serializer.save()
        return Response(ClosedDateSerializer(closed).data, status=status.HTTP_201_CREATED)


class ClosedDateDetailView(APIView):
    permission_classes = [IsBakeryMember]

    def delete(self, request, pk):
        closed = get_object_or_404(ClosedDate, pk=pk)
        closed.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PickupSlotAvailabilityView(APIView):
    """GET /api/pickup-slots/available/?date=YYYY-MM-DD — student only."""

    permission_classes = [IsStudent]

    def get(self, request):
        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"detail": "A ?date=YYYY-MM-DD query parameter is required."}, status=400)
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        if target_date < date.today():
            return Response({"detail": "Please choose a date that is today or later."}, status=400)

        if ClosedDate.objects.filter(date=target_date).exists():
            return Response([])  # bakery closed that day — no slots available

        slots = PickupSlot.objects.filter(is_active=True)
        data = [
            {
                "id": slot.id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "label": f"{slot.start_time.strftime('%I:%M %p')} – {slot.end_time.strftime('%I:%M %p')}",
                "remaining": slot.remaining_capacity_for_date(target_date),
            }
            for slot in slots
        ]
        return Response([s for s in data if s["remaining"] > 0])


# ==========================================================
# 6. INVENTORY
# ==========================================================
class InventoryListCreateView(APIView):
    """GET/POST /api/bakery/inventory/ — bakery only."""

    permission_classes = [IsBakeryMember]

    def get(self, request):
        items = InventoryItem.objects.all()
        low_only = request.query_params.get("low_stock")
        if low_only == "true":
            items = [i for i in items if i.is_low_stock]
        return Response(InventoryItemSerializer(items, many=True).data)

    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InventoryDetailView(APIView):
    """GET/PATCH/DELETE /api/bakery/inventory/<id>/ — bakery only."""

    permission_classes = [IsBakeryMember]

    def get(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        return Response(InventoryItemSerializer(item).data)

    def patch(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        serializer = InventoryItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==========================================================
# 7. ANALYTICS
# ==========================================================
class AnalyticsView(APIView):
    """GET /api/bakery/analytics/ — bakery only."""

    permission_classes = [IsBakeryMember]

    def get(self, request):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        orders = CakeOrder.objects.all()

        def revenue_since(start_date):
            total = orders.filter(
                created_at__date__gte=start_date, status__in=["COMPLETED", "COLLECTED"]
            ).aggregate(total=Sum("estimated_price"))["total"]
            return total or 0

        orders_per_day = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            orders_per_day.append({"date": day.isoformat(), "count": orders.filter(created_at__date=day).count()})

        def counted(field):
            return list(
                orders.exclude(status__in=["CANCELLED", "REJECTED"])
                .values(field)
                .annotate(count=Count("id"))
                .order_by("-count")
            )

        decoration_counts = {}
        for decos in orders.exclude(status__in=["CANCELLED", "REJECTED"]).values_list("decorations", flat=True):
            for d in decos or []:
                decoration_counts[d] = decoration_counts.get(d, 0) + 1
        popular_decorations = sorted(
            [{"decorations": k, "count": v} for k, v in decoration_counts.items()],
            key=lambda x: -x["count"],
        )

        reviews_qs = Review.objects.all()
        review_count = reviews_qs.count()
        avg_rating = reviews_qs.aggregate(avg=Avg("overall_rating"))["avg"]
        average_rating = round(avg_rating, 2) if avg_rating is not None else None

        data = {
            "orders_today": orders.filter(created_at__date=today).count(),
            "orders_week": orders.filter(created_at__date__gte=week_start).count(),
            "orders_month": orders.filter(created_at__date__gte=month_start).count(),
            "completed_orders": orders.filter(status__in=["COMPLETED", "COLLECTED"]).count(),
            "rejected_orders": orders.filter(status="REJECTED").count(),
            "cancelled_orders": orders.filter(status="CANCELLED").count(),
            "revenue_today": revenue_since(today),
            "revenue_week": revenue_since(week_start),
            "revenue_month": revenue_since(month_start),
            "popular_flavors": counted("flavor"),
            "popular_sizes": counted("size"),
            "egg_vs_eggless": counted("cake_type"),
            "popular_creams": counted("cream"),
            "popular_decorations": popular_decorations,
            "orders_per_day": orders_per_day,
            "status_distribution": counted("status"),
            "average_rating": average_rating,
            "review_count": review_count,
            "recent_reviews": ReviewSerializer(reviews_qs[:5], many=True).data,
        }
        return Response(data)


# ==========================================================
# 8. NOTIFICATIONS
# ==========================================================
class NotificationsListView(APIView):
    """GET /api/notifications/ — student only, their own notifications."""

    permission_classes = [IsStudent]

    def get(self, request):
        notifications = Notification.objects.filter(student=request.user.student_profile)
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationReadView(APIView):
    """PATCH /api/notifications/<id>/read/ — student only, must own the notification."""

    permission_classes = [IsStudent]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, student=request.user.student_profile)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    """POST /api/notifications/read-all/ — student only."""

    permission_classes = [IsStudent]

    def post(self, request):
        Notification.objects.filter(student=request.user.student_profile, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})
