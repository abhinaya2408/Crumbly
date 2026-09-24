from django.urls import path

from . import views

urlpatterns = [
    # ---- Auth ----
    path("auth/student/register/", views.StudentRegisterView.as_view()),
    path("auth/student/login/", views.StudentLoginView.as_view()),
    path("auth/student/logout/", views.LogoutView.as_view()),
    path("auth/bakery/login/", views.BakeryLoginView.as_view()),
    path("auth/bakery/logout/", views.LogoutView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    # ---- Student profile ----
    path("students/me/", views.StudentProfileView.as_view()),
    # ---- Orders ----
    path("orders/", views.OrderCreateView.as_view()),
    path("orders/my/", views.MyOrdersView.as_view()),
    path("orders/<str:order_id>/", views.OrderDetailView.as_view()),
    path("orders/<str:order_id>/status/", views.OrderStatusUpdateView.as_view()),
    path("orders/<str:order_id>/cancel/", views.OrderCancelView.as_view()),
    path("orders/<str:order_id>/reorder/", views.OrderReorderView.as_view()),
    path("orders/<str:order_id>/payment/", views.OrderPaymentUpdateView.as_view()),
    path("orders/<str:order_id>/review/", views.OrderReviewView.as_view()),
    # ---- Pickup slots (student availability check) ----
    path("pickup-slots/available/", views.PickupSlotAvailabilityView.as_view()),
    # ---- Bakery ----
    path("bakery/dashboard/", views.BakeryDashboardView.as_view()),
    path("bakery/orders/", views.BakeryOrdersListView.as_view()),
    path("bakery/pickup-slots/", views.PickupSlotListCreateView.as_view()),
    path("bakery/pickup-slots/<int:pk>/", views.PickupSlotDetailView.as_view()),
    path("bakery/closed-dates/", views.ClosedDateListCreateView.as_view()),
    path("bakery/closed-dates/<int:pk>/", views.ClosedDateDetailView.as_view()),
    path("bakery/inventory/", views.InventoryListCreateView.as_view()),
    path("bakery/inventory/<int:pk>/", views.InventoryDetailView.as_view()),
    path("bakery/analytics/", views.AnalyticsView.as_view()),
    # ---- Notifications ----
    path("notifications/", views.NotificationsListView.as_view()),
    path("notifications/<int:pk>/read/", views.NotificationReadView.as_view()),
    path("notifications/read-all/", views.NotificationReadAllView.as_view()),
]
