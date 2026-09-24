# Crumbly — College Bakery Ordering System

Crumbly is a full-stack cake-ordering platform for a college bakery.
Students customize and order cakes for campus pickup; bakery staff
manage incoming orders, pickup slots, and inventory through a live
dashboard. Built on Django + Django REST Framework with a vanilla
HTML/CSS/JavaScript frontend — no React, no Node, no external chart
libraries.

**Who uses it**
- **Students** register with their college email, customize a cake,
  pick an available pickup slot, track its status, cancel or reorder,
  and leave a review once it's collected.
- **Bakery members** log in separately, work through the order queue
  (accept/reject/prepare/ready/collect), manage pickup slots and
  ingredient inventory, and check analytics.

---

## 1. Technology stack

| Layer      | Technology                                   |
|------------|-----------------------------------------------|
| Frontend   | HTML5, CSS3, vanilla JavaScript (`fetch`)     |
| Backend    | Python, Django, Django REST Framework         |
| Database   | SQLite                                        |
| Media      | Django `ImageField` / `MEDIA_ROOT`            |

No React, Vue, Angular, Bootstrap, Tailwind, Node.js, PHP, Spring
Boot, Firebase, Supabase, MongoDB, Redis, Celery, or WebSockets.

## 2. Project structure

```
smart-college-bakery/
├── manage.py
├── .env.example              # copy to .env to override settings
├── backend/                  # Django project (settings, urls, wsgi/asgi)
├── bakery/                   # Django app
│   ├── models.py             # StudentProfile, BakeryMemberProfile, CakeOrder,
│   │                         #   OrderStatusHistory, Notification, PickupSlot,
│   │                         #   ClosedDate, InventoryItem, Review
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py        # IsStudent / IsBakeryMember
│   ├── signals.py            # auto-creates notifications on status change
│   ├── pricing.py            # single source of truth for prices
│   ├── admin.py
│   ├── tests.py
│   └── management/commands/seed_demo_data.py
├── frontend/
│   ├── *.html                 # served as Django templates, original filenames
│   ├── css/                   # style.css/student.css/owner.css/... unchanged;
│   │                         #   crumbly-extra.css is new (reviews, timeline,
│   │                         #   charts, slot cards, low-stock badges)
│   └── js/                    # api.js is the fetch layer; every other file
│                             #   calls it instead of touching localStorage
├── media/cake-references/     # uploaded reference photos
└── requirements.txt
```

## 3. Database models & relationships

```
User (Django's built-in auth user)
│
├── StudentProfile        student_id, phone, college_email, department, year
└── BakeryMemberProfile   employee_id, phone

CakeOrder
    order_id (e.g. CRB-1024), student(FK), flavor, size,
    cake_type (EGG/EGGLESS), cream, decorations (JSON list),
    cake_message, special_instructions, reference_image,
    pickup_slot(FK), required_date, required_time, estimated_price,
    status, payment_status, rejection_reason, cancellation_reason,
    reordered_from(FK → self), created_at, updated_at

OrderStatusHistory   order(FK), previous_status, new_status, changed_by(FK User), note, created_at
Notification         student(FK), order(FK), message, notification_type, is_read, created_at
PickupSlot           start_time, end_time, max_orders_per_day, is_active
ClosedDate           date, reason
InventoryItem        name, category, quantity, unit, minimum_stock, is_active
Review               order(OneToOne), student(FK), overall/cake_quality/service ratings, comment
```

There is **no "shape" field anywhere** — cake shape customization was
explicitly removed and never re-added.

## 4. Order status workflow

```
PENDING → ACCEPTED → PREPARING → READY → COLLECTED → COMPLETED
PENDING → REJECTED            (bakery, reason required)
PENDING/ACCEPTED → CANCELLED  (student-initiated, optional reason)
```

Every transition is validated server-side
(`OrderStatusUpdateSerializer.ALLOWED_TRANSITIONS`) — a student can
never set `READY` directly, and the bakery can't skip a step. Every
change is recorded in `OrderStatusHistory` and triggers a
`Notification` automatically via `bakery/signals.py`, regardless of
whether it came from the API or the Django admin.

## 5. Authentication approach

The frontend is served by this **same** Django application, so
everything is same-origin — no CORS package needed. Login uses
Django's built-in **session authentication**:

1. `POST /api/auth/student/login/` (or `/bakery/login/`) calls
   `authenticate()` + `login()`, setting a session cookie the browser
   stores automatically.
2. Every following request rides on that cookie.
3. CSRF protection stays **on** for all unsafe requests
   (POST/PATCH/DELETE) from an already-logged-in user —
   `frontend/js/api.js` reads the `csrftoken` cookie and sends it
   back as `X-CSRFToken`.
4. Only the three login/register endpoints are `@csrf_exempt` (a new
   visitor has no session to protect yet), but they're also
   `@ensure_csrf_cookie`, which guarantees the cookie is set the
   moment you log in.

## 6. API endpoints

| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| POST | `/api/auth/student/register/` | Public | Register (college email + optional dept/year) |
| POST | `/api/auth/student/login/` | Public | Student login |
| POST | `/api/auth/student/logout/` | Student | Logout |
| POST | `/api/auth/bakery/login/` | Public | Bakery login |
| POST | `/api/auth/bakery/logout/` | Bakery | Logout |
| GET | `/api/auth/me/` | Any | Who's logged in |
| GET/PATCH | `/api/students/me/` | Student | View/edit phone, department, year |
| POST | `/api/orders/` | Student | Create order (multipart, validates pickup slot capacity) |
| GET | `/api/orders/my/` | Student | Own orders |
| GET | `/api/orders/<order_id>/` | Owner* | Full order detail |
| PATCH | `/api/orders/<order_id>/status/` | Bakery | Advance/reject (reason required for reject) |
| POST | `/api/orders/<order_id>/cancel/` | Student | Cancel (Pending/Accepted only) |
| POST | `/api/orders/<order_id>/reorder/` | Student | Get prefill data from a past order |
| PATCH | `/api/orders/<order_id>/payment/` | Bakery | Mark Pending/Paid/Failed/Refunded |
| GET/POST | `/api/orders/<order_id>/review/` | Student | Get/submit a review (Completed only) |
| GET | `/api/pickup-slots/available/?date=` | Student | Slots with remaining capacity for a date |
| GET | `/api/bakery/dashboard/` | Bakery | Live counts + today/week/month revenue + low-stock count |
| GET | `/api/bakery/orders/?status=&search=&date=&sort=` | Bakery | Filterable/searchable/sortable order list |
| GET/POST | `/api/bakery/pickup-slots/` | Bakery (POST) | List/create recurring slot templates |
| PATCH/DELETE | `/api/bakery/pickup-slots/<id>/` | Bakery | Edit/deactivate/delete a slot |
| GET/POST | `/api/bakery/closed-dates/` | Bakery (POST) | List/add closed dates |
| DELETE | `/api/bakery/closed-dates/<id>/` | Bakery | Remove a closed date |
| GET/POST | `/api/bakery/inventory/` | Bakery | List/add inventory items |
| GET/PATCH/DELETE | `/api/bakery/inventory/<id>/` | Bakery | View/update/delete an item |
| GET | `/api/bakery/analytics/` | Bakery | Orders/revenue trends, popularity breakdowns, ratings |
| GET | `/api/notifications/` | Student | Own notifications |
| PATCH | `/api/notifications/<id>/read/` | Student | Mark one read |
| POST | `/api/notifications/read-all/` | Student | Mark all read |

\* the student who placed the order, or any bakery member.

## 7. Student flow

Landing page → Student Login/Register (college email enforced both
client- and server-side) → Customize a Cake (flavor → size →
Egg/Eggless → cream → decorations → message → instructions →
reference image → pickup date → **available pickup slot**, fetched
live from the backend) → instant estimated price → Place Order →
Confirmation → track from **My Orders** (search + status tabs) →
notified the moment status changes, especially `READY` → **Cancel**
while Pending/Accepted, or **Reorder** once it's in a final state →
**Review** once Completed.

## 8. Bakery flow

Bakery Login → Dashboard (live counts, today's revenue, low-stock
banner) → open an order → see the student's full details, cake
customization, and reference image → Accept / Reject (reason
required) → Start Preparing → Mark Cake Ready (student notified) →
Mark Collected → Complete Order → mark payment status → manage
**Pickup Slots**, **Inventory**, and check **Analytics** from the
sidebar.

## 9. Notification flow

Every order status change automatically creates a `Notification` for
the student (`ORDER_PLACED`, `ORDER_ACCEPTED`, `ORDER_PREPARING`,
`ORDER_READY`, `ORDER_COLLECTED`, `ORDER_REJECTED`,
`ORDER_CANCELLED`) via a model signal, so it fires no matter which
code path changed the status. The frontend polls
`GET /api/notifications/` every 25 seconds to keep the navbar's
unread badge fresh — **simple polling, not WebSockets**, by design.

## 10. Image upload

JPG/JPEG/PNG/WEBP up to 2 MB. Instant local preview with
remove/replace before submitting. On submit, everything (including
the file) goes as `multipart/form-data` via `FormData` — the browser
sets `Content-Type` automatically. Django re-validates extension,
MIME type, and size server-side, and stores files under
`media/cake-references/`.

## 11. Pickup slots

Bakery members define **recurring daily** time windows (e.g. every
day 10:00–10:30, max 3 orders) plus specific **closed dates**
(holidays). When a student picks a date on the customize page, the
frontend calls `GET /api/pickup-slots/available/?date=...`, which
returns only slots with remaining capacity for that exact date — and
the backend re-checks that capacity again when the order is actually
submitted, so two students can never race for the same last slot.

## 12. Inventory

Bakery members track ingredients (name, category, quantity, unit,
minimum stock). Any item below its minimum shows a
"⚠️ Low Stock" badge on the Inventory page and a warning banner on
the Dashboard. Stock is tracked manually (no automatic deduction on
order completion — kept simple and reliable, as the spec asked).

## 13. Reviews & analytics

Once an order is `COMPLETED`, the student can leave one review
(overall/cake-quality/service ratings 1–5 + a comment) from the order
details page. The Analytics page (bakery-only) shows orders/revenue
today/week/month, a 7-day order trend, popularity breakdowns
(flavors, sizes, Egg vs Eggless, creams, decorations), and recent
reviews — all rendered as lightweight CSS bar charts, no chart
library.

## 14. Installation

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (cmd.exe)
venv\Scripts\activate.bat
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser      # for /admin/ access
python manage.py seed_demo_data       # demo students, bakery members, orders, slots, inventory, a review

python manage.py runserver
```

Then open **http://127.0.0.1:8000/**.

### Creating a bakery member account

There's no bakery self-registration page (by design — bakery accounts
are internal). Either run `seed_demo_data` (creates two ready-to-use
accounts) or, via `/admin/`: create/pick a `User`, then add a
**Bakery member profile** with an `employee_id` and `phone`.

## 15. Demo credentials

After `python manage.py seed_demo_data`:

| Role | Email | Password |
|---|---|---|
| Student | `student@yourcollege.edu` | `Student@123` |
| Student | `ananya.sharma@yourcollege.edu` | `demo1234` |
| Student | `priya.verma@yourcollege.edu` | `demo1234` |
| Student | `rahul.nair@yourcollege.edu` | `demo1234` |
| Bakery | `bakery@crumbly.local` | `Bakery@123` |
| Bakery | `owner@crumbly.local` | `bakery123` |
| Bakery | `assistant@crumbly.local` | `bakery123` |

These are clearly-marked development credentials — never used for
any production behaviour.

## 16. Configuration (`.env`)

Copy `.env.example` to `.env` (no extra package required —
`backend/settings.py` reads it with a small built-in loader):

```
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=*
COLLEGE_EMAIL_DOMAIN=@yourcollege.edu
```

**Before deploying anywhere public**, change all four:
- `SECRET_KEY` — generate a real random value.
- `DEBUG=False` — and set `ALLOWED_HOSTS` to your real domain(s).
- `COLLEGE_EMAIL_DOMAIN` — your actual college's email domain. Also
  update the matching constant in `frontend/js/app.js` (it only
  drives the instant frontend hint — the backend is what's actually
  enforced).
- Swap SQLite for a production database if needed; `MEDIA_ROOT`
  should point somewhere durable (or a real object store) in
  production, since Django only serves `/media/` itself while
  `DEBUG=True`.

## 17. Feature checklist

```
✓ Student registration, login, logout, protected pages
✓ College-email domain enforced on frontend AND backend
✓ Separate bakery login/logout, role-based backend permissions
✓ Student profile — view + edit phone/department/year
✓ Cake customization (flavor, size, Egg/Eggless, cream, decorations,
  message ≤50 chars, special instructions, reference image)
✓ No cake-shape feature anywhere (verified — grep finds zero matches)
✓ Live price calculation on the frontend; backend always recalculates
✓ Order creation, backed entirely by the Django database
✓ Full status workflow incl. CANCELLED, with backend-enforced transitions
✓ Visual order tracker + full status-change timeline
✓ Order cancellation (Pending/Accepted only, with reason)
✓ Reorder (prefills the customize page from a past order)
✓ My Orders — tabs for every status + search by order ID/flavor
✓ Order details — student info, cake info, pickup, reference image,
  price breakdown, tracker, timeline, review
✓ Database-backed notifications, all types, polling every 25s
✓ Pickup slot management (recurring templates + closed dates),
  capacity enforced server-side at booking time
✓ Bakery dashboard — real counts, today/week/month revenue, low-stock banner
✓ Bakery order management — search, status filter, date filter, sort
✓ Bakery order details — everything needed to fulfil + status actions
✓ Rejection reason required + shown to the student
✓ Simple "Pay at Pickup" payment status (Pending/Paid/Failed/Refunded)
✓ Ratings & reviews (one per completed order, 3 rating dimensions)
✓ Inventory management + low-stock warnings
✓ Analytics dashboard (orders, revenue, popularity, ratings) — CSS-only charts
✓ Responsive layout (existing responsive breakpoints preserved/extended)
✓ Form validation, frontend AND backend, with friendly error messages
✓ Reference-image validation (type, size) enforced server-side
✓ Consistent, documented REST API structure
✓ Django admin configured for every model
✓ .env support (dependency-free), configurable SECRET_KEY/DEBUG/ALLOWED_HOSTS
✓ Demo data via a management command (students, bakery, slots, inventory, orders, review)
✓ Basic automated tests (bakery/tests.py) — auth, permissions, status
  transitions, cancellation rules, reorder eligibility, slot
  overbooking, review rules, inventory permissions
✓ Friendly error handling (no raw Django tracebacks reach the browser)
✓ Loading states + duplicate-submission guards on order placement
✓ Empty states (no orders, no notifications, no matching bakery orders)
✓ Accessibility basics — semantic HTML, labelled inputs, focus states
  carried over from the original design; status never relies on
  color alone (icon + text pill everywhere)
```

## 18. Testing

Run the automated suite:

```bash
python manage.py check
python manage.py test
```

`bakery/tests.py` covers: student registration + college-email
validation, student/bakery login separation, permission boundaries
(student can't reach bakery endpoints or another student's order and
vice versa, student can't change order status), status-transition
enforcement (no skipping steps, reject requires a reason),
notification creation on status change, cancellation rules, reorder
eligibility, pickup-slot overbooking rejection, review rules (only
Completed, only once), and inventory permissions.

**Important:** this project was built and syntax-checked in an
environment without internet access, so these tests — and
`makemigrations`/`migrate`/`runserver` — have **not** been executed
end-to-end by the assistant that wrote this code. Every Python file
passed `py_compile` and every JavaScript file passed `node --check`,
and all HTML element IDs referenced by JS were cross-checked against
the actual markup, but please run the checklist below yourself after
installing.

Manual checklist:
- [ ] `python manage.py migrate` runs with no errors
- [ ] `python manage.py seed_demo_data` runs with no errors
- [ ] Student register/login/logout; bakery login/logout; cross-role login is rejected
- [ ] Place an order with every field, incl. reference image and a pickup slot
- [ ] Cancel a Pending order; confirm it disappears from cancellable state
- [ ] Reorder a Completed order; confirm the customize page prefills
- [ ] Bakery: Accept → Preparing → Ready → Collected → Complete on an order
- [ ] Bakery: Reject a Pending order, confirm reason is required and shown to the student
- [ ] Notifications badge updates; mark-one-read and mark-all-read work
- [ ] Leave a review on a Completed order; confirm it can't be submitted twice
- [ ] Add/deactivate/delete a pickup slot; add/remove a closed date; confirm a fully-booked date shows no slots
- [ ] Add/edit/delete an inventory item; confirm low-stock badge appears below minimum
- [ ] Analytics page loads with real numbers, not zeros/placeholders
- [ ] Try the whole flow on a narrow (mobile-width) browser window

## 19. Troubleshooting

- **"No such table" errors** → run `python manage.py migrate`.
- **Login works but every other request 403s** → make sure you're
  loading pages through Django (`http://127.0.0.1:8000/...`), not
  opening the HTML files directly from disk — the `csrftoken` cookie
  needs a real origin.
- **Uploaded images don't display** → confirm `DEBUG=True` and that
  `media/cake-references/` exists and is writable.
- **No pickup slots show up on the customize page** → run
  `seed_demo_data`, or add slots yourself at
  `owner-pickup-slots.html` while logged in as a bakery member.
- **"An account with this email already exists"** → the seed script
  is idempotent; re-running it won't duplicate accounts.
