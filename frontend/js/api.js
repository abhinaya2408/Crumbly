/* ==========================================================
   Crumbly — js/api.js
   Thin fetch() wrapper around the Django REST API. Every other JS
   file (auth.js, customize.js, orders.js, owner.js, notifications.js)
   calls functions from here instead of touching localStorage.

   Authentication: the backend uses Django SESSION authentication
   (see backend/settings.py + README.md). The browser stores the
   session automatically via a cookie once you log in — we just need
   to send Django's CSRF token back on every non-GET request, which
   getCookie() below reads straight out of the "csrftoken" cookie.
   ========================================================== */

const API_BASE = "/api";

/* ---------- low-level request helper ---------- */
function getCookie(name) {
  const match = document.cookie.match("(?:^|; )" + name + "=([^;]*)");
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiRequest(path, { method = "GET", body, isFormData = false } = {}) {
  const headers = {};
  if (!isFormData) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(API_BASE + path, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body)
  });

  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }

  if (!response.ok) {
    const message =
      (data && data.detail) ||
      (data && data.errors && firstErrorMessage(data.errors)) ||
      "Something went wrong. Please try again.";
    const error = new Error(message);
    error.status = response.status;
    error.errors = data && data.errors;
    throw error;
  }

  return data;
}

function firstErrorMessage(errors) {
  if (Array.isArray(errors)) return errors[0];
  if (typeof errors === "object" && errors !== null) {
    const firstKey = Object.keys(errors)[0];
    return firstErrorMessage(errors[firstKey]);
  }
  return String(errors);
}

/* ---------- current-user cache ----------
   undefined = not fetched yet this page load, null = confirmed logged out */
let currentUserCache;

function clearCurrentUserCache() {
  currentUserCache = undefined;
}

async function getCurrentUser(force) {
  if (currentUserCache !== undefined && !force) return currentUserCache;
  try {
    currentUserCache = await apiRequest("/auth/me/");
  } catch (e) {
    currentUserCache = null;
  }
  return currentUserCache;
}

/* ---------- auth ---------- */
async function registerStudent(payload) {
  const data = await apiRequest("/auth/student/register/", { method: "POST", body: payload });
  clearCurrentUserCache();
  return data;
}
async function loginStudent(payload) {
  const data = await apiRequest("/auth/student/login/", { method: "POST", body: payload });
  clearCurrentUserCache();
  return data;
}
async function loginBakery(payload) {
  const data = await apiRequest("/auth/bakery/login/", { method: "POST", body: payload });
  clearCurrentUserCache();
  return data;
}
async function logoutStudent() {
  try {
    await apiRequest("/auth/student/logout/", { method: "POST" });
  } finally {
    clearCurrentUserCache();
  }
}
async function logoutBakery() {
  try {
    await apiRequest("/auth/bakery/logout/", { method: "POST" });
  } finally {
    clearCurrentUserCache();
  }
}

/* ---------- student profile ---------- */
async function getStudentProfile() {
  return apiRequest("/students/me/");
}
async function updateStudentProfile(payload) {
  return apiRequest("/students/me/", { method: "PATCH", body: payload });
}

/* ---------- orders ---------- */
async function createOrder(formData) {
  return apiRequest("/orders/", { method: "POST", body: formData, isFormData: true });
}
async function getMyOrders() {
  return apiRequest("/orders/my/");
}
async function getOrder(orderId) {
  return apiRequest("/orders/" + encodeURIComponent(orderId) + "/");
}
async function updateOrderStatus(orderId, newStatus, reason) {
  return apiRequest("/orders/" + encodeURIComponent(orderId) + "/status/", {
    method: "PATCH",
    body: { status: newStatus, reason: reason || "" }
  });
}
async function cancelOrder(orderId, reason) {
  return apiRequest("/orders/" + encodeURIComponent(orderId) + "/cancel/", {
    method: "POST",
    body: { reason: reason || "" }
  });
}
async function reorderOrder(orderId) {
  return apiRequest("/orders/" + encodeURIComponent(orderId) + "/reorder/", { method: "POST" });
}
async function updateOrderPayment(orderId, paymentStatus) {
  return apiRequest("/orders/" + encodeURIComponent(orderId) + "/payment/", {
    method: "PATCH",
    body: { payment_status: paymentStatus }
  });
}
async function getOrderReview(orderId) {
  try {
    return await apiRequest("/orders/" + encodeURIComponent(orderId) + "/review/");
  } catch (e) {
    if (e.status === 404) return null;
    throw e;
  }
}
async function submitOrderReview(orderId, payload) {
  return apiRequest("/orders/" + encodeURIComponent(orderId) + "/review/", { method: "POST", body: payload });
}

/* ---------- pickup slots (student availability check) ---------- */
async function getAvailablePickupSlots(dateStr) {
  return apiRequest("/pickup-slots/available/?date=" + encodeURIComponent(dateStr));
}

/* ---------- bakery ---------- */
async function getBakeryDashboard() {
  return apiRequest("/bakery/dashboard/");
}
async function getBakeryOrders(params) {
  const query = params && Object.keys(params).length ? "?" + new URLSearchParams(params).toString() : "";
  return apiRequest("/bakery/orders/" + query);
}

/* ---------- bakery: pickup slots + closed dates ---------- */
async function getPickupSlots() {
  return apiRequest("/bakery/pickup-slots/");
}
async function createPickupSlot(payload) {
  return apiRequest("/bakery/pickup-slots/", { method: "POST", body: payload });
}
async function updatePickupSlot(id, payload) {
  return apiRequest("/bakery/pickup-slots/" + encodeURIComponent(id) + "/", { method: "PATCH", body: payload });
}
async function deletePickupSlot(id) {
  return apiRequest("/bakery/pickup-slots/" + encodeURIComponent(id) + "/", { method: "DELETE" });
}
async function getClosedDates() {
  return apiRequest("/bakery/closed-dates/");
}
async function createClosedDate(payload) {
  return apiRequest("/bakery/closed-dates/", { method: "POST", body: payload });
}
async function deleteClosedDate(id) {
  return apiRequest("/bakery/closed-dates/" + encodeURIComponent(id) + "/", { method: "DELETE" });
}

/* ---------- bakery: inventory ---------- */
async function getInventory(lowStockOnly) {
  return apiRequest("/bakery/inventory/" + (lowStockOnly ? "?low_stock=true" : ""));
}
async function createInventoryItem(payload) {
  return apiRequest("/bakery/inventory/", { method: "POST", body: payload });
}
async function updateInventoryItem(id, payload) {
  return apiRequest("/bakery/inventory/" + encodeURIComponent(id) + "/", { method: "PATCH", body: payload });
}
async function deleteInventoryItem(id) {
  return apiRequest("/bakery/inventory/" + encodeURIComponent(id) + "/", { method: "DELETE" });
}

/* ---------- bakery: analytics ---------- */
async function getBakeryAnalytics() {
  return apiRequest("/bakery/analytics/");
}

/* ---------- notifications ---------- */
async function getNotifications() {
  return apiRequest("/notifications/");
}
async function markNotificationRead(id) {
  return apiRequest("/notifications/" + encodeURIComponent(id) + "/read/", { method: "PATCH" });
}
async function markAllNotificationsRead() {
  return apiRequest("/notifications/read-all/", { method: "POST" });
}
