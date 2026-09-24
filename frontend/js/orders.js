/* ==========================================================
   Crumbly — orders.js
   Order confirmation, My Orders list, Order details + tracker.
   All data comes from the Django API (js/api.js) — no localStorage.
   ========================================================== */

function getFlavorImage(flavorName) {
  const f = FLAVORS.find((x) => x.id === flavorName);
  return f ? cakeImages[f.key] : cakeImages.hero;
}

function getUrlParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function cakeTypeLabel(cakeType) {
  return cakeType === "EGG" ? "Egg" : "Eggless";
}

/* ---------- Order Confirmation ---------- */
async function initOrderConfirmationPage() {
  const student = await requireStudent();
  if (!student) return;

  const orderId = getUrlParam("orderId");
  const root = document.getElementById("confirmationCard");
  const trackBtn = document.getElementById("trackOrderBtn");

  let order = null;
  if (orderId) {
    try {
      order = await getOrder(orderId);
    } catch (e) {
      order = null;
    }
  }

  if (!order) {
    root.innerHTML = `<div class="empty-state"><div class="emoji">🎂</div><h3>Order not found</h3><p>We couldn't find that order. It may have been removed.</p><a href="customize.html" class="btn btn-primary">Customize a Cake</a></div>`;
    trackBtn.style.display = "none";
    return;
  }

  trackBtn.href = "order-details.html?orderId=" + encodeURIComponent(order.order_id);

  root.innerHTML = `
    <div class="detail-card">
      <img src="${order.reference_image || getFlavorImage(order.flavor)}" class="detail-image" alt="${order.flavor} cake">
      <div class="detail-row"><span class="label">Order ID</span><span class="value">${order.order_id}</span></div>
      <div class="detail-row"><span class="label">Cake</span><span class="value">${order.flavor} · ${order.size}</span></div>
      <div class="detail-row"><span class="label">Cake Type</span><span class="value">${cakeTypeLabel(order.cake_type)}</span></div>
      <div class="detail-row"><span class="label">Cream</span><span class="value">${order.cream}</span></div>
      <div class="detail-row"><span class="label">Decorations</span><span class="value">${order.decorations.length ? order.decorations.join(", ") : "None"}</span></div>
      <div class="detail-row"><span class="label">Pickup Date</span><span class="value">${formatDate(order.required_date)}</span></div>
      <div class="detail-row"><span class="label">Pickup Time</span><span class="value">${formatTime(order.required_time)}</span></div>
      <div class="detail-row"><span class="label">Estimated Price</span><span class="value">₹${order.estimated_price}</span></div>
      <div class="detail-row"><span class="label">Status</span><span class="pill pill-${order.status.toLowerCase()}"><span class="dot"></span>${statusLabel(order.status)}</span></div>
    </div>`;
}

/* ---------- My Orders ---------- */
async function initMyOrdersPage() {
  const student = await requireStudent();
  if (!student) return;

  let currentTab = "all";
  let searchTerm = "";
  let allOrders = [];
  const listEl = document.getElementById("ordersList");
  const emptyEl = document.getElementById("emptyState");
  const tabBar = document.getElementById("tabBar");
  const searchInput = document.getElementById("orderSearchInput");

  function matchesTab(order, tab) {
    if (tab === "all") return true;
    return order.status.toLowerCase() === tab;
  }

  function matchesSearch(order, term) {
    if (!term) return true;
    const t = term.toLowerCase();
    return order.order_id.toLowerCase().includes(t) || order.flavor.toLowerCase().includes(t);
  }

  function render() {
    const orders = allOrders
      .filter((o) => matchesTab(o, currentTab) && matchesSearch(o, searchTerm))
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    listEl.innerHTML = "";
    if (!orders.length) {
      emptyEl.style.display = "block";
      listEl.style.display = "none";
      return;
    }
    emptyEl.style.display = "none";
    listEl.style.display = "flex";

    orders.forEach((order) => {
      const card = document.createElement("div");
      card.className = "order-card";
      card.innerHTML = `
        <img class="order-thumb" src="${order.reference_image || getFlavorImage(order.flavor)}" alt="${order.flavor} cake">
        <div class="order-info">
          <div class="order-id">Order #${order.order_id}</div>
          <div class="order-title">${order.flavor} Cake · ${order.size}</div>
          <div class="order-meta">Required: ${formatDate(order.required_date)} · ${formatTime(order.required_time)}</div>
          <div class="order-actions" style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
            <a href="order-details.html?orderId=${encodeURIComponent(order.order_id)}" class="btn btn-outline btn-sm">View / Track</a>
            ${order.can_cancel ? `<button class="btn btn-danger btn-sm" data-action="cancel">Cancel</button>` : ""}
            ${order.can_reorder ? `<button class="btn btn-secondary btn-sm" data-action="reorder">Reorder</button>` : ""}
            ${order.can_review ? `<a href="order-details.html?orderId=${encodeURIComponent(order.order_id)}#review" class="btn btn-secondary btn-sm">Leave a Review</a>` : ""}
          </div>
        </div>
        <div class="order-side">
          <span class="pill pill-${order.status.toLowerCase()}"><span class="dot"></span>${statusLabel(order.status)}</span>
          <span style="font-weight:700;font-size:14px;">₹${order.estimated_price}</span>
        </div>`;

      const cancelBtn = card.querySelector('[data-action="cancel"]');
      if (cancelBtn) {
        cancelBtn.addEventListener("click", async () => {
          await handleCancelOrder(order.order_id, cancelBtn);
          await reload();
        });
      }
      const reorderBtn = card.querySelector('[data-action="reorder"]');
      if (reorderBtn) {
        reorderBtn.addEventListener("click", () => {
          window.location.href = "customize.html?reorderFrom=" + encodeURIComponent(order.order_id);
        });
      }

      listEl.appendChild(card);
    });
  }

  tabBar.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBar.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentTab = btn.dataset.tab;
      render();
    });
  });

  searchInput.addEventListener("input", () => {
    searchTerm = searchInput.value.trim();
    render();
  });

  async function reload() {
    try {
      allOrders = await getMyOrders();
    } catch (e) {
      allOrders = [];
      showToast(e.message || "Could not load your orders.", "error");
    }
    render();
  }

  listEl.innerHTML = `<p class="mb-0">Loading orders...</p>`;
  await reload();
}

/* Shared cancel-order flow used by both My Orders and Order Details */
async function handleCancelOrder(orderId, triggerBtn) {
  const reason = window.prompt("Optional: let the bakery know why you're cancelling (or leave blank).", "");
  if (reason === null) return false; // user pressed Cancel on the prompt itself
  if (!window.confirm("Cancel order " + orderId + "? This can't be undone.")) return false;

  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.textContent = "Cancelling...";
  }
  try {
    await cancelOrder(orderId, reason);
    showToast("Order cancelled.", "success");
    return true;
  } catch (e) {
    showToast(e.message || "Could not cancel this order.", "error");
    return false;
  }
}

/* ---------- Order Details (student) ---------- */
async function initOrderDetailsPage() {
  const student = await requireStudent();
  if (!student) return;

  const orderId = getUrlParam("orderId");
  const root = document.getElementById("orderDetailsRoot");
  root.innerHTML = `<p class="mb-0">Loading order...</p>`;

  let order = null;
  if (orderId) {
    try {
      order = await getOrder(orderId);
    } catch (e) {
      order = null;
    }
  }

  if (!order) {
    root.innerHTML = `<div class="empty-state"><div class="emoji">🎂</div><h3>Order not found</h3><p>Invalid order ID or this order doesn't belong to your account.</p><a href="my-orders.html" class="btn btn-primary">Back to My Orders</a></div>`;
    return;
  }

  const reasonBlock =
    order.status === "REJECTED" && order.rejection_reason
      ? `<div class="detail-card"><h3>Rejection Reason</h3><p class="mb-0">${order.rejection_reason}</p></div>`
      : order.status === "CANCELLED" && order.cancellation_reason
      ? `<div class="detail-card"><h3>Cancellation Reason</h3><p class="mb-0">${order.cancellation_reason}</p></div>`
      : "";

  root.innerHTML = `
    <div class="dashboard-header" style="padding: var(--sp-3) 0 var(--sp-4);">
      <h1>Order #${order.order_id}</h1>
      <p>Placed on ${new Date(order.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</p>
    </div>

    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom: var(--sp-4);">
      ${order.can_cancel ? `<button class="btn btn-danger btn-sm" id="cancelOrderBtn">Cancel Order</button>` : ""}
      ${order.can_reorder ? `<button class="btn btn-secondary btn-sm" id="reorderBtn">Reorder</button>` : ""}
    </div>

    ${renderTracker(order.status)}
    ${reasonBlock}

    <div class="detail-grid" style="margin-top: var(--sp-5);">
      <div>
        <div class="detail-card">
          <h3>Cake Details</h3>
          <div class="detail-row"><span class="label">Flavor</span><span class="value">${order.flavor}</span></div>
          <div class="detail-row"><span class="label">Cake Type</span><span class="value">${cakeTypeLabel(order.cake_type)}</span></div>
          <div class="detail-row"><span class="label">Size</span><span class="value">${order.size}</span></div>
          <div class="detail-row"><span class="label">Cream</span><span class="value">${order.cream}</span></div>
          <div class="detail-row"><span class="label">Decorations</span><span class="value">${order.decorations.length ? order.decorations.join(", ") : "None"}</span></div>
          <div class="detail-row"><span class="label">Pickup Date</span><span class="value">${formatDate(order.required_date)}</span></div>
          <div class="detail-row"><span class="label">Pickup Time</span><span class="value">${order.pickup_slot_label || formatTime(order.required_time)}</span></div>
          <div class="detail-row"><span class="label">Estimated Price</span><span class="value">₹${order.estimated_price}</span></div>
          <div class="detail-row"><span class="label">Payment</span><span class="value">${order.payment_status}</span></div>
        </div>
        ${order.cake_message ? `<div class="detail-card"><h3>Cake Message</h3><div class="message-box">"${order.cake_message}"</div></div>` : ""}
        ${order.special_instructions ? `<div class="detail-card"><h3>Special Instructions</h3><p class="mb-0">${order.special_instructions}</p></div>` : ""}

        <div class="detail-card" id="reviewSection"></div>
      </div>
      <div>
        <div class="detail-card">
          <h3>Reference Image</h3>
          <img class="detail-image" src="${order.reference_image || getFlavorImage(order.flavor)}" alt="Reference for ${order.flavor} cake">
          ${!order.reference_image ? `<p class="mb-0" style="font-size:12.5px;">No reference photo uploaded — showing a sample ${order.flavor.toLowerCase()} cake image.</p>` : ""}
        </div>
        ${renderStatusHistoryCard(order.status_history)}
      </div>
    </div>`;

  const cancelBtn = document.getElementById("cancelOrderBtn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", async () => {
      const ok = await handleCancelOrder(order.order_id, cancelBtn);
      if (ok) initOrderDetailsPage();
    });
  }
  const reorderBtn = document.getElementById("reorderBtn");
  if (reorderBtn) {
    reorderBtn.addEventListener("click", () => {
      window.location.href = "customize.html?reorderFrom=" + encodeURIComponent(order.order_id);
    });
  }

  renderReviewSection(order);

  if (window.location.hash === "#review") {
    document.getElementById("reviewSection").scrollIntoView({ behavior: "smooth" });
  }
}

/* ---------- Status history timeline ---------- */
function renderStatusHistoryCard(history) {
  if (!history || !history.length) return "";
  const items = history
    .map(
      (h) => `
      <div class="tl-item">
        <div class="tl-title">${h.previous_status ? statusLabel(h.previous_status) + " → " : ""}${statusLabel(h.new_status)}</div>
        <div class="tl-meta">${h.changed_by_name} · ${timeAgo(h.created_at)}</div>
        ${h.note ? `<div class="tl-note">"${h.note}"</div>` : ""}
      </div>`
    )
    .join("");
  return `<div class="detail-card"><h3>Order Timeline</h3><div class="status-timeline">${items}</div></div>`;
}

/* ---------- Review section (form for a completed order, or the existing review) ---------- */
function renderReviewSection(order) {
  const container = document.getElementById("reviewSection");
  if (!container) return;

  if (order.review) {
    container.innerHTML = `
      <h3>Your Review</h3>
      <div class="star-display">${starString(order.review.overall_rating)}</div>
      ${order.review.comment ? `<p class="review-comment" style="margin-top:8px;">"${order.review.comment}"</p>` : ""}`;
    return;
  }

  if (!order.can_review) {
    container.style.display = "none";
    return;
  }

  let overall = 0;
  let quality = 0;
  let service = 0;

  container.innerHTML = `
    <h3>Leave a Review</h3>
    <p class="mb-0" style="font-size:13px;">How was your cake? Your feedback helps Crumbly improve.</p>
    <div style="margin-top:var(--sp-3);">
      <label style="font-size:13px;font-weight:600;">Overall Rating</label>
      <div class="star-input" id="starOverall"></div>
    </div>
    <div style="margin-top:var(--sp-2);">
      <label style="font-size:13px;font-weight:600;">Cake Quality</label>
      <div class="star-input" id="starQuality"></div>
    </div>
    <div style="margin-top:var(--sp-2);">
      <label style="font-size:13px;font-weight:600;">Service</label>
      <div class="star-input" id="starService"></div>
    </div>
    <div class="form-group" style="margin-top:var(--sp-3);">
      <label for="reviewComment">Comments (optional)</label>
      <textarea id="reviewComment" rows="3" placeholder="Tell us more..."></textarea>
    </div>
    <div class="field-error" id="reviewError"></div>
    <button class="btn btn-primary" id="submitReviewBtn" style="margin-top:var(--sp-2);">Submit Review</button>`;

  function buildStars(containerId, onChange) {
    const el = document.getElementById(containerId);
    for (let i = 1; i <= 5; i++) {
      const star = document.createElement("button");
      star.type = "button";
      star.textContent = "★";
      star.dataset.value = i;
      star.addEventListener("click", () => {
        onChange(i);
        Array.from(el.children).forEach((c) => c.classList.toggle("filled", Number(c.dataset.value) <= i));
      });
      el.appendChild(star);
    }
  }

  buildStars("starOverall", (v) => (overall = v));
  buildStars("starQuality", (v) => (quality = v));
  buildStars("starService", (v) => (service = v));

  document.getElementById("submitReviewBtn").addEventListener("click", async () => {
    const reviewError = document.getElementById("reviewError");
    reviewError.classList.remove("show");
    if (!overall || !quality || !service) {
      reviewError.textContent = "Please rate all three categories before submitting.";
      reviewError.classList.add("show");
      return;
    }
    const btn = document.getElementById("submitReviewBtn");
    btn.disabled = true;
    btn.textContent = "Saving review...";
    try {
      await submitOrderReview(order.order_id, {
        overall_rating: overall,
        cake_quality_rating: quality,
        service_rating: service,
        comment: document.getElementById("reviewComment").value.trim()
      });
      showToast("Thanks for your review! 🎂", "success");
      initOrderDetailsPage();
    } catch (e) {
      reviewError.textContent = e.message || "Could not save your review.";
      reviewError.classList.add("show");
      btn.disabled = false;
      btn.textContent = "Submit Review";
    }
  });
}

function starString(rating) {
  let out = "";
  for (let i = 1; i <= 5; i++) out += i <= rating ? "★" : '<span class="empty">★</span>';
  return out;
}

/* Renders the horizontal status tracker; shared by student + owner views */
function renderTracker(status) {
  if (status === "REJECTED" || status === "CANCELLED") {
    const label = status === "REJECTED" ? "Rejected" : "Cancelled";
    const note =
      status === "REJECTED"
        ? "Unfortunately this order was not accepted. See the reason below."
        : "This order was cancelled.";
    return `<div class="detail-card"><h3>Order Status</h3>
      <div class="tracker rejected">
        <div class="tracker-step done"><div class="tracker-dot">✓</div><div class="tracker-label">Order Placed</div></div>
        <div class="tracker-step current"><div class="tracker-line"></div><div class="tracker-dot">✕</div><div class="tracker-label">${label}</div></div>
      </div>
      <p class="mb-0" style="text-align:center;">${note}</p>
    </div>`;
  }

  const labels = ["Order Placed", "Accepted", "Preparing", "Ready", "Collected"];
  const currentIndex = STATUS_STEPS.indexOf(status === "COLLECTED" ? "COMPLETED" : status);

  const steps = labels
    .map((label, i) => {
      let cls = "";
      if (i < currentIndex) cls = "done";
      else if (i === currentIndex) cls = "done current";
      const icon = i <= currentIndex ? "✓" : (i + 1);
      return `<div class="tracker-step ${cls}"><div class="tracker-line"></div><div class="tracker-dot">${icon}</div><div class="tracker-label">${label}</div></div>`;
    })
    .join("");

  return `<div class="detail-card"><h3>Order Status</h3><div class="tracker">${steps}</div></div>`;
}

/* ---------- Status tracker step order ---------- */
const STATUS_STEPS = ["PENDING", "ACCEPTED", "PREPARING", "READY", "COMPLETED"];
