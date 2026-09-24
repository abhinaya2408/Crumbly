"""
Basic tests for Crumbly's critical workflows. Run with:

    python manage.py test

These intentionally stay at the "does the important behaviour work
and are permissions enforced" level rather than covering every
possible edge case — enough to catch a regression before it reaches
a real student or bakery member.
"""

from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from bakery.models import BakeryMemberProfile, CakeOrder, PickupSlot, StudentProfile


class BaseTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.slot = PickupSlot.objects.create(start_time=time(10, 0), end_time=time(10, 30), max_orders_per_day=2)

        self.student_user = User.objects.create_user(
            username="alice@yourcollege.edu", email="alice@yourcollege.edu", password="Passw0rd!", first_name="Alice"
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, student_id="STU001", phone="9876543210", college_email="alice@yourcollege.edu"
        )

        self.other_student_user = User.objects.create_user(
            username="bob@yourcollege.edu", email="bob@yourcollege.edu", password="Passw0rd!", first_name="Bob"
        )
        self.other_student = StudentProfile.objects.create(
            user=self.other_student_user, student_id="STU002", phone="9876543211", college_email="bob@yourcollege.edu"
        )

        self.bakery_user = User.objects.create_user(
            username="owner@crumbly.local", email="owner@crumbly.local", password="Passw0rd!", first_name="Owner"
        )
        self.bakery_member = BakeryMemberProfile.objects.create(
            user=self.bakery_user, phone="9000000000", employee_id="EMP001"
        )

    def login_student(self):
        self.client.post("/api/auth/student/login/", {"email": "alice@yourcollege.edu", "password": "Passw0rd!"}, format="json")

    def login_other_student(self):
        self.client.post("/api/auth/student/login/", {"email": "bob@yourcollege.edu", "password": "Passw0rd!"}, format="json")

    def login_bakery(self):
        self.client.post("/api/auth/bakery/login/", {"email": "owner@crumbly.local", "password": "Passw0rd!"}, format="json")

    def create_order(self, **overrides):
        student = overrides.pop("student", self.student)
        defaults = dict(
            order_id="CRB-9001",
            student=student,
            flavor="Chocolate",
            size="1 Kg",
            cake_type="EGGLESS",
            cream="Chocolate",
            decorations=[],
            pickup_slot=self.slot,
            required_date=date.today() + timedelta(days=1),
            required_time=self.slot.start_time,
            estimated_price=550,
        )
        defaults.update(overrides)
        return CakeOrder.objects.create(**defaults)


class AuthenticationTests(BaseTestCase):
    def test_student_registration_requires_college_email(self):
        response = self.client.post(
            "/api/auth/student/register/",
            {
                "name": "Charlie",
                "student_id": "STU003",
                "email": "charlie@gmail.com",
                "phone": "9876543212",
                "password": "Str0ngPassw0rd!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_student_registration_success(self):
        response = self.client.post(
            "/api/auth/student/register/",
            {
                "name": "Charlie",
                "student_id": "STU003",
                "email": "charlie@yourcollege.edu",
                "phone": "9876543212",
                "password": "Str0ngPassw0rd!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StudentProfile.objects.filter(student_id="STU003").exists())

    def test_student_login_success(self):
        response = self.client.post(
            "/api/auth/student/login/", {"email": "alice@yourcollege.edu", "password": "Passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_login_via_bakery_endpoint(self):
        response = self.client.post(
            "/api/auth/bakery/login/", {"email": "alice@yourcollege.edu", "password": "Passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_bakery_login_success(self):
        response = self.client.post(
            "/api/auth/bakery/login/", {"email": "owner@crumbly.local", "password": "Passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 200)


class OrderPermissionTests(BaseTestCase):
    def test_student_cannot_view_another_students_order(self):
        order = self.create_order(student=self.other_student)
        self.login_student()
        response = self.client.get(f"/api/orders/{order.order_id}/")
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_bakery_dashboard(self):
        self.login_student()
        response = self.client.get("/api/bakery/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_bakery_cannot_access_student_my_orders(self):
        self.login_bakery()
        response = self.client.get("/api/orders/my/")
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_change_order_status(self):
        order = self.create_order()
        self.login_student()
        response = self.client.patch(f"/api/orders/{order.order_id}/status/", {"status": "READY"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_access_orders(self):
        response = self.client.get("/api/orders/my/")
        self.assertEqual(response.status_code, 401)


class OrderWorkflowTests(BaseTestCase):
    def test_bakery_cannot_skip_status_steps(self):
        order = self.create_order(status="PENDING")
        self.login_bakery()
        response = self.client.patch(f"/api/orders/{order.order_id}/status/", {"status": "READY"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_bakery_can_accept_then_prepare(self):
        order = self.create_order(status="PENDING")
        self.login_bakery()
        r1 = self.client.patch(f"/api/orders/{order.order_id}/status/", {"status": "ACCEPTED"}, format="json")
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.patch(f"/api/orders/{order.order_id}/status/", {"status": "PREPARING"}, format="json")
        self.assertEqual(r2.status_code, 200)

    def test_rejecting_requires_a_reason(self):
        order = self.create_order(status="PENDING")
        self.login_bakery()
        response = self.client.patch(f"/api/orders/{order.order_id}/status/", {"status": "REJECTED"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_status_change_creates_notification(self):
        order = self.create_order(status="PENDING")
        self.login_bakery()
        self.client.patch(f"/api/orders/{order.order_id}/status/", {"status": "ACCEPTED"}, format="json")
        self.assertTrue(order.notifications.filter(notification_type="ORDER_ACCEPTED").exists())

    def test_student_can_cancel_pending_order(self):
        order = self.create_order(status="PENDING")
        self.login_student()
        response = self.client.post(f"/api/orders/{order.order_id}/cancel/", {"reason": "Changed my mind"}, format="json")
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELLED")

    def test_student_cannot_cancel_order_in_preparing(self):
        order = self.create_order(status="PREPARING")
        self.login_student()
        response = self.client.post(f"/api/orders/{order.order_id}/cancel/", format="json")
        self.assertEqual(response.status_code, 400)

    def test_reorder_only_allowed_for_final_states(self):
        active_order = self.create_order(status="PENDING")
        self.login_student()
        response = self.client.post(f"/api/orders/{active_order.order_id}/reorder/")
        self.assertEqual(response.status_code, 400)

    def test_pickup_slot_fully_booked_is_rejected_on_create(self):
        # slot capacity is 2 — fill it, then a 3rd booking for the same date must fail
        target_date = date.today() + timedelta(days=1)
        self.create_order(order_id="CRB-9101", required_date=target_date)
        self.create_order(order_id="CRB-9102", required_date=target_date, student=self.other_student)

        self.login_student()
        response = self.client.post(
            "/api/orders/",
            {
                "flavor": "Vanilla",
                "size": "500g",
                "cake_type": "EGG",
                "cream": "Vanilla",
                "decorations": "[]",
                "pickup_slot": self.slot.id,
                "required_date": target_date.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 400)


class ReviewTests(BaseTestCase):
    def test_cannot_review_non_completed_order(self):
        order = self.create_order(status="PENDING")
        self.login_student()
        response = self.client.post(
            f"/api/orders/{order.order_id}/review/",
            {"overall_rating": 5, "cake_quality_rating": 5, "service_rating": 5, "comment": "Great!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_can_review_completed_order(self):
        order = self.create_order(status="COMPLETED")
        self.login_student()
        response = self.client.post(
            f"/api/orders/{order.order_id}/review/",
            {"overall_rating": 5, "cake_quality_rating": 4, "service_rating": 5, "comment": "Loved it!"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_cannot_review_same_order_twice(self):
        order = self.create_order(status="COMPLETED")
        self.login_student()
        self.client.post(
            f"/api/orders/{order.order_id}/review/",
            {"overall_rating": 5, "cake_quality_rating": 4, "service_rating": 5, "comment": "Loved it!"},
            format="json",
        )
        response = self.client.post(
            f"/api/orders/{order.order_id}/review/",
            {"overall_rating": 3, "cake_quality_rating": 3, "service_rating": 3, "comment": "Again"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class InventoryPermissionTests(BaseTestCase):
    def test_student_cannot_access_inventory(self):
        self.login_student()
        response = self.client.get("/api/bakery/inventory/")
        self.assertEqual(response.status_code, 403)

    def test_bakery_can_create_inventory_item(self):
        self.login_bakery()
        response = self.client.post(
            "/api/bakery/inventory/",
            {"name": "Sprinkles", "category": "DECORATION", "quantity": "5", "unit": "kg", "minimum_stock": "2"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
