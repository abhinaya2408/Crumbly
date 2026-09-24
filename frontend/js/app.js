/* ==========================================================
   Crumbly — app.js
   Shared config, pricing, cake images, toasts, formatting helpers,
   and session/role guards. All other JS files rely on this (and
   js/api.js, loaded just before it) being loaded first.
   ========================================================== */

/* ---------- Config ----------
   Must match backend.settings.COLLEGE_EMAIL_DOMAIN. This copy only
   drives the frontend's instant validation message — the Django
   backend is the one that actually enforces it (frontend validation
   alone is never enough, see README.md). */
const COLLEGE_EMAIL_DOMAIN = "@yourcollege.edu";

/* ---------- Cake images (swap these URLs for local files later) ----------
   To use local files instead: drop images into a static folder and
   change each URL below to the local path. */
const cakeImages = {
  chocolate: "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80",
  vanilla: "https://images.unsplash.com/photo-1519869325930-281384150729?auto=format&fit=crop&w=800&q=80",
  redVelvet: "https://images.unsplash.com/photo-1586788680434-30d324b2d46f?auto=format&fit=crop&w=800&q=80",
  blackForest: "https://images.unsplash.com/photo-1571115177098-24ec42ed204d?auto=format&fit=crop&w=800&q=80",
  butterscotch: "https://images.unsplash.com/photo-1587248720327-8eb72564be1e?auto=format&fit=crop&w=800&q=80",
  strawberry: "https://images.unsplash.com/photo-1565958011703-44f9829ba187?auto=format&fit=crop&w=800&q=80",
  birthday: "https://images.unsplash.com/photo-1464349095431-e9a21285b5f3?auto=format&fit=crop&w=1200&q=80",
  hero: "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=1400&q=80",
  custom: "https://images.unsplash.com/photo-1550617931-e17a7b70dce2?auto=format&fit=crop&w=800&q=80",
  chocolateDecoration: "https://images.unsplash.com/photo-1541599468348-e96984315921?auto=format&fit=crop&w=800&q=80",
  fruitDecoration: "https://images.unsplash.com/photo-1587668178277-295251f900ce?auto=format&fit=crop&w=800&q=80",
  flowerDecoration: "https://images.unsplash.com/photo-1519340241574-2cec6aef0c01?auto=format&fit=crop&w=800&q=80"
};

/* Flavor metadata used across landing + customize pages.
   Must match bakery/pricing.py on the backend. */
const FLAVORS = [
  { id: "Chocolate", key: "chocolate", desc: "Rich, moist chocolate sponge with creamy chocolate frosting.", base: 0 },
  { id: "Vanilla", key: "vanilla", desc: "Classic vanilla sponge with silky vanilla buttercream.", base: 0 },
  { id: "Red Velvet", key: "redVelvet", desc: "Velvety cocoa sponge with tangy cream cheese frosting.", base: 50 },
  { id: "Black Forest", key: "blackForest", desc: "Chocolate sponge, cherries and whipped cream layers.", base: 60 },
  { id: "Butterscotch", key: "butterscotch", desc: "Caramel-kissed sponge with crunchy praline bits.", base: 40 },
  { id: "Strawberry", key: "strawberry", desc: "Light sponge layered with fresh strawberry cream.", base: 50 }
];

/* ---------- Pricing (frontend copy, for instant feedback only —
   the Django backend always recalculates and is the source of truth) ---------- */
const SIZE_PRICES = { "500g": 300, "1 Kg": 550, "1.5 Kg": 750, "2 Kg": 1000 };

const DECORATION_PRICES = {
  "Fresh Flowers": 50,
  "Chocolate Decorations": 100,
  "Sprinkles": 30,
  "Fruits": 80,
  "Birthday Theme": 100,
  "Custom Decoration": 150
};

function flavorSurcharge(flavorName) {
  const f = FLAVORS.find((x) => x.id === flavorName);
  return f ? f.base : 0;
}

function calculatePrice({ flavor, size, decorations }) {
  const basePrice = (SIZE_PRICES[size] || 0) + flavorSurcharge(flavor);
  const decorPrice = (decorations || []).reduce(
    (sum, d) => sum + (DECORATION_PRICES[d] || 0),
    0
  );
  return { basePrice, decorPrice, total: basePrice + decorPrice };
}

/* ---------- Toasts ---------- */
function showToast(message, type) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = "toast" + (type ? " toast-" + type : "");
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

/* ---------- Session / role guards (backed by the Django API) ----------
   Every page's inline <script>init...Page()</script> call is now
   async — see auth.js / customize.js / orders.js / owner.js /
   notifications.js. */

/* Require a logged-in student; redirect to login if missing.
   Returns the student's profile object, or null (after redirecting). */
async function requireStudent() {
  const user = await getCurrentUser();
  if (!user || user.role !== "student") {
    window.location.href = "student-login.html";
    return null;
  }
  return user.profile;
}

/* Require an active bakery session; redirect to bakery login if missing. */
async function requireBakery() {
  const user = await getCurrentUser();
  if (!user || user.role !== "bakery") {
    window.location.href = "bakery-login.html";
    return null;
  }
  return user.profile;
}

/* ---------- Formatting helpers ---------- */
function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr + "T00:00:00");
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
}
function formatTime(timeStr) {
  if (!timeStr) return "";
  const [h, m] = timeStr.split(":");
  const hour = parseInt(h, 10);
  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = ((hour + 11) % 12) + 1;
  return `${displayHour}:${m} ${period}`;
}
function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  const days = Math.floor(hrs / 24);
  return days + "d ago";
}
function statusLabel(status) {
  const map = {
    PENDING: "Pending",
    ACCEPTED: "Accepted",
    PREPARING: "Preparing",
    READY: "Ready",
    COLLECTED: "Collected",
    COMPLETED: "Completed",
    REJECTED: "Rejected"
  };
  return map[status] || status;
}

/* ---------- Nav / mobile menu wiring + notification badge (runs on every page) ---------- */
document.addEventListener("DOMContentLoaded", async () => {
  const toggle = document.querySelector(".nav-toggle");
  const menu = document.querySelector(".nav-links");
  if (toggle && menu) {
    toggle.addEventListener("click", () => {
      menu.classList.toggle("open");
      toggle.classList.toggle("open");
    });
  }

  // Populate unread notification badges wherever present. Polls every
  // 25s so students see a fresh count without needing WebSockets
  // (see README.md → "Real-time vs polling").
  const badges = document.querySelectorAll("[data-unread-badge]");
  if (badges.length) {
    const refreshBadge = async () => {
      const user = await getCurrentUser();
      if (!user || user.role !== "student") return;
      try {
        const notifications = await getNotifications();
        const count = notifications.filter((n) => !n.is_read).length;
        badges.forEach((el) => {
          if (count > 0) {
            el.textContent = count;
            el.style.display = "inline-flex";
          } else {
            el.style.display = "none";
          }
        });
      } catch (e) {
        /* not logged in / network hiccup — leave badge hidden */
      }
    };
    refreshBadge();
    setInterval(refreshBadge, 25000);
  }
});
