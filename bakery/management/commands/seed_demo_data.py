"""
Creates realistic Crumbly demo data: students, bakery members, pickup
slots, a closed date, inventory items, cake orders (in a mix of
statuses), notifications, order status history, and one review.

Usage:
    python manage.py seed_demo_data

Safe to run more than once — it uses get_or_create and will simply
skip anything that already exists rather than duplicating it.
"""

from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from bakery.models import (
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
from bakery.pricing import calculate_price

DEMO_PASSWORD = "demo1234"


class Command(BaseCommand):
    help = "Seed the database with demo Crumbly students, bakery members, orders, slots, inventory, and reviews."

    @transaction.atomic
    def handle(self, *args, **options):
        students = self._create_students()
        self._create_bakery_members()
        slots = self._create_pickup_slots()
        self._create_closed_dates()
        self._create_inventory()
        orders = self._create_orders(students, slots)
        self._create_status_history(orders)
        self._create_notifications(orders)
        self._create_reviews(orders, students)

        self.stdout.write(self.style.SUCCESS("Crumbly demo data ready. Sample logins:"))
        self.stdout.write("  Student  → student@yourcollege.edu / Student@123")
        self.stdout.write("  Student  → ananya.sharma@yourcollege.edu / demo1234")
        self.stdout.write("  Bakery   → bakery@crumbly.local / Bakery@123")

    # ---------- Students ----------
    def _create_students(self):
        data = [
            ("Demo Student", "STU2024000", "student@yourcollege.edu", "9876500000", "Student@123", "Computer Science", "2"),
            ("Ananya Sharma", "STU2024001", "ananya.sharma@yourcollege.edu", "9876543210", DEMO_PASSWORD, "Computer Science", "3"),
            ("Priya Verma", "STU2024002", "priya.verma@yourcollege.edu", "9876543211", DEMO_PASSWORD, "Electronics", "2"),
            ("Rahul Nair", "STU2024003", "rahul.nair@yourcollege.edu", "9876543212", DEMO_PASSWORD, "Mechanical", "4"),
        ]
        profiles = {}
        for full_name, student_id, email, phone, password, department, year in data:
            user, created = User.objects.get_or_create(
                username=email, defaults={"email": email, "first_name": full_name}
            )
            if created:
                user.set_password(password)
                user.save()
            profile, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": student_id,
                    "phone": phone,
                    "college_email": email,
                    "department": department,
                    "year": year,
                },
            )
            profiles[student_id] = profile
        return profiles

    # ---------- Bakery members ----------
    def _create_bakery_members(self):
        data = [
            ("Demo Bakery Owner", "bakery@crumbly.local", "Bakery@123", "EMP000", "9000000000"),
            ("Bakery Owner", "owner@crumbly.local", "bakery123", "EMP001", "9000000001"),
            ("Assistant Baker", "assistant@crumbly.local", "bakery123", "EMP002", "9000000002"),
        ]
        for full_name, email, password, employee_id, phone in data:
            user, created = User.objects.get_or_create(
                username=email, defaults={"email": email, "first_name": full_name}
            )
            if created:
                user.set_password(password)
                user.save()
            BakeryMemberProfile.objects.get_or_create(
                user=user, defaults={"employee_id": employee_id, "phone": phone}
            )

    # ---------- Pickup slots ----------
    def _create_pickup_slots(self):
        if PickupSlot.objects.exists():
            return list(PickupSlot.objects.all())
        templates = [
            (time(10, 0), time(10, 30), 3),
            (time(10, 30), time(11, 0), 3),
            (time(11, 0), time(11, 30), 3),
            (time(16, 0), time(16, 30), 4),
            (time(16, 30), time(17, 0), 4),
            (time(17, 0), time(17, 30), 4),
        ]
        slots = []
        for start, end, capacity in templates:
            slot = PickupSlot.objects.create(start_time=start, end_time=end, max_orders_per_day=capacity)
            slots.append(slot)
        return slots

    def _create_closed_dates(self):
        if ClosedDate.objects.exists():
            return
        ClosedDate.objects.create(date=date.today() + timedelta(days=14), reason="Campus Founders' Day")

    # ---------- Inventory ----------
    def _create_inventory(self):
        if InventoryItem.objects.exists():
            return
        items = [
            ("Chocolate Cream", "CREAM", 8, "kg", 3),
            ("Vanilla Cream", "CREAM", 6, "kg", 3),
            ("Strawberry Cream", "CREAM", 5, "kg", 3),
            ("Butterscotch Cream", "CREAM", 4, "kg", 3),
            ("Fresh Flowers", "DECORATION", 12, "bunches", 4),
            ("Chocolate Decorations", "DECORATION", 5, "kg", 2),
            ("Sprinkles", "DECORATION", 1, "kg", 3),  # intentionally low stock for the demo
            ("Fruits (Mixed)", "DECORATION", 9, "kg", 3),
            ("Cake Bases", "FLAVOR_BASE", 20, "pcs", 8),
            ("Birthday Decorations", "DECORATION", 15, "sets", 5),
        ]
        for name, category, qty, unit, minimum in items:
            InventoryItem.objects.create(
                name=name, category=category, quantity=qty, unit=unit, minimum_stock=minimum
            )

    # ---------- Orders ----------
    def _create_orders(self, students, slots):
        if CakeOrder.objects.exists():
            self.stdout.write("Orders already exist — skipping order seeding.")
            return list(CakeOrder.objects.all())

        slot_morning = slots[0]
        slot_late_morning = slots[2]
        slot_evening = slots[3]

        today = date.today()
        rows = [
            dict(
                order_id="CRB-1001",
                student=students["STU2024001"],
                flavor="Chocolate",
                cake_type="EGGLESS",
                size="1 Kg",
                cream="Chocolate",
                decorations=["Sprinkles", "Birthday Theme"],
                cake_message="Happy Birthday Rhea!",
                special_instructions="Please pack it securely, will be carried on a bike.",
                pickup_slot=slot_evening,
                required_date=today + timedelta(days=2),
                required_time=slot_evening.start_time,
                status="PREPARING",
            ),
            dict(
                order_id="CRB-1002",
                student=students["STU2024002"],
                flavor="Red Velvet",
                cake_type="EGG",
                size="1.5 Kg",
                cream="Vanilla",
                decorations=["Fresh Flowers"],
                cake_message="Congrats Team!",
                special_instructions="",
                pickup_slot=slot_morning,
                required_date=today + timedelta(days=1),
                required_time=slot_morning.start_time,
                status="READY",
            ),
            dict(
                order_id="CRB-1003",
                student=students["STU2024003"],
                flavor="Butterscotch",
                cake_type="EGGLESS",
                size="500g",
                cream="Butterscotch",
                decorations=[],
                cake_message="",
                special_instructions="Small farewell cake for hostel room.",
                pickup_slot=slot_evening,
                required_date=today + timedelta(days=4),
                required_time=slot_evening.start_time,
                status="PENDING",
            ),
            dict(
                order_id="CRB-1004",
                student=students["STU2024001"],
                flavor="Black Forest",
                cake_type="EGG",
                size="2 Kg",
                cream="Chocolate",
                decorations=["Chocolate Decorations", "Fruits"],
                cake_message="Happy Anniversary!",
                special_instructions="",
                pickup_slot=slot_morning,
                required_date=today - timedelta(days=3),
                required_time=slot_morning.start_time,
                status="COMPLETED",
            ),
            dict(
                order_id="CRB-1005",
                student=students["STU2024002"],
                flavor="Strawberry",
                cake_type="EGGLESS",
                size="1 Kg",
                cream="Strawberry",
                decorations=["Fresh Flowers", "Sprinkles"],
                cake_message="Happy Birthday Priya!",
                special_instructions="Please use pink and white decoration.",
                pickup_slot=slot_late_morning,
                required_date=today + timedelta(days=3),
                required_time=slot_late_morning.start_time,
                status="ACCEPTED",
            ),
            dict(
                order_id="CRB-1006",
                student=students["STU2024000"],
                flavor="Vanilla",
                cake_type="EGGLESS",
                size="500g",
                cream="Vanilla",
                decorations=[],
                cake_message="Just because :)",
                special_instructions="",
                pickup_slot=slot_morning,
                required_date=today - timedelta(days=1),
                required_time=slot_morning.start_time,
                status="REJECTED",
                rejection_reason="Requested pickup time unavailable",
            ),
            dict(
                order_id="CRB-1007",
                student=students["STU2024003"],
                flavor="Chocolate",
                cake_type="EGG",
                size="1 Kg",
                cream="Chocolate",
                decorations=["Custom Decoration"],
                cake_message="Good luck!",
                special_instructions="",
                pickup_slot=slot_evening,
                required_date=today - timedelta(days=2),
                required_time=slot_evening.start_time,
                status="CANCELLED",
                cancellation_reason="Plans changed",
            ),
        ]

        created_orders = []
        for row in rows:
            price = calculate_price(row["flavor"], row["size"], row["decorations"])
            order = CakeOrder.objects.create(estimated_price=price, **row)
            created_orders.append(order)
        return created_orders

    def _create_status_history(self, orders):
        if OrderStatusHistory.objects.exists() or not orders:
            return
        by_id = {o.order_id: o for o in orders}
        entries = [
            ("CRB-1001", "", "PENDING", "Order placed."),
            ("CRB-1001", "PENDING", "ACCEPTED", ""),
            ("CRB-1001", "ACCEPTED", "PREPARING", ""),
            ("CRB-1002", "", "PENDING", "Order placed."),
            ("CRB-1002", "PENDING", "ACCEPTED", ""),
            ("CRB-1002", "ACCEPTED", "PREPARING", ""),
            ("CRB-1002", "PREPARING", "READY", ""),
            ("CRB-1004", "READY", "COLLECTED", ""),
            ("CRB-1004", "COLLECTED", "COMPLETED", ""),
            ("CRB-1006", "PENDING", "REJECTED", "Requested pickup time unavailable"),
            ("CRB-1007", "PENDING", "CANCELLED", "Plans changed"),
        ]
        for order_id, prev, new, note in entries:
            order = by_id.get(order_id)
            if not order:
                continue
            OrderStatusHistory.objects.create(order=order, previous_status=prev, new_status=new, note=note)

    def _create_notifications(self, orders):
        if not orders:
            return
        by_id = {o.order_id: o for o in orders}
        samples = [
            ("CRB-1001", "ORDER_PREPARING", "👩‍🍳 Your cake order CRB-1001 is now being prepared.", False),
            ("CRB-1001", "ORDER_ACCEPTED", "🎂 Your Crumbly order CRB-1001 has been accepted.", True),
            ("CRB-1002", "ORDER_READY", "🎂 Your cake order CRB-1002 is ready for collection!", False),
            ("CRB-1004", "ORDER_COLLECTED", "Your order CRB-1004 has been collected. Thank you for choosing Crumbly!", True),
            ("CRB-1005", "ORDER_ACCEPTED", "🎂 Your Crumbly order CRB-1005 has been accepted.", False),
            ("CRB-1006", "ORDER_REJECTED", "Unfortunately, your cake order CRB-1006 could not be accepted.", False),
        ]
        # Each demo order already got an auto "ORDER_PLACED" notification
        # from bakery/signals.py the moment it was created above — these
        # extra, status-specific ones are added on top (get_or_create so
        # re-running this command never duplicates them).
        for order_id, ntype, message, is_read in samples:
            order = by_id.get(order_id)
            if not order:
                continue
            Notification.objects.get_or_create(
                order=order,
                notification_type=ntype,
                defaults={"student": order.student, "message": message, "is_read": is_read},
            )

    def _create_reviews(self, orders, students):
        if Review.objects.exists() or not orders:
            return
        by_id = {o.order_id: o for o in orders}
        completed_order = by_id.get("CRB-1004")
        if completed_order:
            Review.objects.create(
                order=completed_order,
                student=completed_order.student,
                overall_rating=5,
                cake_quality_rating=5,
                service_rating=4,
                comment="Absolutely loved the Black Forest cake — moist, not too sweet, and delivered right on time!",
            )
