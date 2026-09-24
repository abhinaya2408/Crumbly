/* ==========================================================
   Crumbly — owner.js
   Bakery dashboard, table/filters/search, order status actions.
   All data comes from the Django API (js/api.js) — no localStorage.
   ========================================================== */

/* ---------- Dashboard ---------- */
async function initOwnerDashboardPage() {
  const session = await requireBakery();
  if (!session) return;

  let currentFilter = "all";
  let searchTerm = "";
  let searchDebounce = null;

  const tableBody = document.getElementById("ordersTableBody");
  const emptyState = document.getElementById("ownerEmptyState");
  const filterPills = document.getElementById("filterPills");
  const searchInput = document.getElementById("searchInput");
  const sidebar = document.getElementById("ownerSidebar");
  const mobileToggle = document.getElementById("mobileSidebarToggle");

  async function updateStats() {
    try {
      const stats = await getBakeryDashboard();
      document.getElementById("statNew").textContent = stats.pending;
      document.getElementById("statPreparing").textContent = stats.preparing;
      document.getElementById("statReady").textContent = stats.ready;
      document.getElementById("statCompleted").textContent = stats.completed;
      document.getElementById("statTodayOrders").textContent = stats.today_orders;
      document.getElementById("statRevenueToday").textContent = "₹" + stats.revenue_today;

      document.getElementById("countPending").textContent = stats.pending;
      document.getElementById("countPreparing").textContent = stats.preparing;
      document.getElementById("countReady").textContent = stats.ready;
      document.getElementById("countCompleted").textContent = stats.completed;

      const banner = document.getElementById("lowStockBanner");
      if (banner) {
        banner.innerHTML =
          stats.low_stock_count > 0
            ? `<div class="warning-banner">⚠️ ${stats.low_stock_count} ingredient${stats.low_stock_count === 1 ? "" : "s"} running low. <a href="owner-inventory.html" style="color:inherit;text-decoration:underline;">Review inventory →</a></div>`
            : "";
      }
    } catch (e) {
      showToast(e.message || "Could not load dashboard stats.", "error");
    }
  }

  async function renderTable() {
    tableBody.innerHTML = `<tr><td colspan="8">Loading orders...</td></tr>`;
    document.querySelector(".orders-table-wrap").style.display = "block";
    emptyState.style.display = "none";

    let orders = [];
    try {
      const params = {};
      if (currentFilter !== "all") params.status = currentFilter;
      if (searchTerm) params.search = searchTerm;
      orders = await getBakeryOrders(params);
    } catch (e) {
      showToast(e.message || "Could not load orders.", "error");
      orders = [];
    }

    tableBody.innerHTML = "";
    if (!orders.length) {
      emptyState.style.display = "block";
      document.querySelector(".orders-table-wrap").style.display = "none";
      return;
    }
    emptyState.style.display = "none";
    document.querySelector(".orders-table-wrap").style.display = "block";

    orders.forEach((order) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><img class="table-cake-thumb" src="${order.reference_image || getFlavorImage(order.flavor)}" alt="${order.flavor} cake"></td>
        <td><span class="row-link" style="font-weight:700;">#${order.order_id}</span></td>
        <td>${order.student_name}</td>
        <td>${order.flavor} · ${order.size}</td>
        <td>${formatDate(order.required_date)}<br><span style="color:var(--color-text-muted);font-size:12px;">${formatTime(order.required_time)}</span></td>
        <td>₹${order.estimated_price}</td>
        <td><span class="pill pill-${order.status.toLowerCase()}"><span class="dot"></span>${statusLabel(order.status)}</span></td>
        <td><a class="row-link" href="owner-order-details.html?orderId=${encodeURIComponent(order.order_id)}">View →</a></td>`;
      tableBody.appendChild(tr);
    });
  }

  function renderAll() {
    updateStats();
    renderTable();
  }

  filterPills.querySelectorAll(".filter-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      filterPills.querySelectorAll(".filter-pill").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      renderTable();
    });
  });

  document.querySelectorAll("[data-status-filter]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      currentFilter = link.dataset.statusFilter;
      filterPills.querySelectorAll(".filter-pill").forEach((b) => {
        b.classList.toggle("active", b.dataset.filter === currentFilter);
      });
      renderTable();
    });
  });

  searchInput.addEventListener("input", () => {
    searchTerm = searchInput.value.trim();
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(renderTable, 300);
  });

  mobileToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  renderAll();
}

/* ---------- Owner Order Details ---------- */
async function initOwnerOrderDetailsPage() {
  const session = await requireBakery();
  if (!session) return;

  const orderId = getUrlParam("orderId");
  await renderOwnerOrder(orderId);
}

async function renderOwnerOrder(orderId) {
  const root = document.getElementById("ownerOrderRoot");
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
    root.innerHTML = `<div class="empty-state"><div class="emoji">📭</div><h3>Order not found</h3><p>This order ID doesn't exist.</p><a href="owner-dashboard.html" class="btn btn-primary">Back to Dashboard</a></div>`;
    return;
  }

  root.innerHTML = `
    <div class="dashboard-header" style="padding: var(--sp-3) 0 var(--sp-4);">
      <h1>Order #${order.order_id}</h1>
      <p>Placed ${timeAgo(order.created_at)}</p>
    </div>

    ${renderTracker(order.status)}
    ${
      order.status === "REJECTED" && order.rejection_reason
        ? `<div class="detail-card"><h3>Rejection Reason</h3><p class="mb-0">${order.rejection_reason}</p></div>`
        : order.status === "CANCELLED"
        ? `<div class="detail-card"><h3>Cancelled by Student</h3><p class="mb-0">${order.cancellation_reason || "No reason given."}</p></div>`
        : ""
    }

    <div class="detail-grid" style="margin-top: var(--sp-5);">
      <div>
        <div class="detail-card">
          <h3>Student</h3>
          <div class="detail-row"><span class="label">Name</span><span class="value">${order.student_name}</span></div>
          <div class="detail-row"><span class="label">Student ID</span><span class="value">${order.student_id_display}</span></div>
          <div class="detail-row"><span class="label">Email</span><span class="value">${order.student_email}</span></div>
          <div class="detail-row"><span class="label">Phone</span><span class="value">${order.student_phone}</span></div>
        </div>

        <div class="detail-card">
          <h3>Cake</h3>
          <div class="detail-row"><span class="label">Flavor</span><span class="value">${order.flavor}</span></div>
          <div class="detail-row"><span class="label">Cake Type</span><span class="value">${cakeTypeLabel(order.cake_type)}</span></div>
          <div class="detail-row"><span class="label">Size</span><span class="value">${order.size}</span></div>
          <div class="detail-row"><span class="label">Cream</span><span class="value">${order.cream}</span></div>
          <div class="detail-row"><span class="label">Decorations</span><span class="value">${order.decorations.length ? order.decorations.join(", ") : "None"}</span></div>
          <div class="detail-row"><span class="label">Required Date</span><span class="value">${formatDate(order.required_date)}</span></div>
          <div class="detail-row"><span class="label">Required Time</span><span class="value">${order.pickup_slot_label || formatTime(order.required_time)}</span></div>
          <div class="detail-row"><span class="label">Price</span><span class="value">₹${order.estimated_price}</span></div>
          <div class="detail-row"><span class="label">Payment</span><span class="value" id="paymentStatusValue">${order.payment_status}</span></div>
        </div>

        ${order.cake_message ? `<div class="detail-card"><h3>Cake Message</h3><div class="message-box">"${order.cake_message}"</div></div>` : ""}
        ${order.special_instructions ? `<div class="detail-card"><h3>Special Instructions</h3><p class="mb-0">${order.special_instructions}</p></div>` : ""}
        ${order.review ? `<div class="detail-card"><h3>Student Review</h3><div class="star-display">${starString(order.review.overall_rating)}</div>${order.review.comment ? `<p class="review-comment" style="margin-top:8px;">"${order.review.comment}"</p>` : ""}</div>` : ""}
      </div>

      <div>
        <div class="detail-card">
          <h3>Student's Cake Inspiration</h3>
          <img class="detail-image" src="${order.reference_image || getFlavorImage(order.flavor)}" alt="Reference for ${order.flavor} cake">
          ${!order.reference_image ? `<p class="mb-0" style="font-size:12.5px;">Student did not upload a reference photo.</p>` : ""}
        </div>

        <div class="detail-card">
          <h3>Update Status</h3>
          <div id="ownerActions" style="display:flex; flex-direction:column; gap: var(--sp-2);"></div>
        </div>

        <div class="detail-card">
          <h3>Payment</h3>
          <div id="paymentActions" style="display:flex; gap: var(--sp-2); flex-wrap:wrap;"></div>
        </div>

        ${renderStatusHistoryCard(order.status_history)}
      </div>
    </div>`;

  renderOwnerActions(order);
  renderPaymentActions(order);
}

function renderPaymentActions(order) {
  const container = document.getElementById("paymentActions");
  if (!container) return;
  container.innerHTML = "";
  ["PENDING", "PAID", "FAILED", "REFUNDED"]
    .filter((s) => s !== order.payment_status)
    .forEach((s) => {
      const btn = document.createElement("button");
      btn.className = "btn btn-outline btn-sm";
      btn.textContent = "Mark " + s.charAt(0) + s.slice(1).toLowerCase();
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await updateOrderPayment(order.order_id, s);
          showToast("Payment status updated.", "success");
          await renderOwnerOrder(order.order_id);
        } catch (e) {
          showToast(e.message || "Could not update payment status.", "error");
          btn.disabled = false;
        }
      });
      container.appendChild(btn);
    });
}

function renderOwnerActions(order) {
  const container = document.getElementById("ownerActions");
  container.innerHTML = "";

  function addBtn(label, cls, nextStatus, needsReason) {
    const btn = document.createElement("button");
    btn.className = "btn " + cls + " btn-block";
    btn.textContent = label;
    btn.addEventListener("click", async () => {
      let reason = "";
      if (needsReason) {
        reason = window.prompt("Please provide a reason for rejecting this order:", "") || "";
        if (!reason.trim()) {
          showToast("A reason is required to reject an order.", "error");
          return;
        }
      }
      await advanceOrderStatus(order.order_id, nextStatus, btn, label, reason);
    });
    container.appendChild(btn);
  }

  switch (order.status) {
    case "PENDING":
      addBtn("Accept Order", "btn-primary", "ACCEPTED");
      addBtn("Reject Order", "btn-danger", "REJECTED", true);
      break;
    case "ACCEPTED":
      addBtn("Start Preparing", "btn-primary", "PREPARING");
      break;
    case "PREPARING":
      addBtn("Mark Cake Ready", "btn-primary", "READY");
      break;
    case "READY":
      addBtn("Mark Collected", "btn-primary", "COLLECTED");
      break;
    case "COLLECTED":
      addBtn("Complete Order", "btn-primary", "COMPLETED");
      break;
    default:
      container.innerHTML = `<p class="mb-0" style="font-size:13.5px;">No further actions available for this order.</p>`;
  }
}

const STATUS_TOASTS = {
  ACCEPTED: "Order accepted.",
  REJECTED: "Order rejected.",
  PREPARING: "Cake is now being prepared.",
  READY: "Cake marked as ready.",
  COLLECTED: "Order marked as collected.",
  COMPLETED: "Order completed."
};

async function advanceOrderStatus(orderId, newStatus, btn, originalLabel, reason) {
  btn.disabled = true;
  btn.textContent = "Updating...";
  try {
    await updateOrderStatus(orderId, newStatus, reason);
    showToast(STATUS_TOASTS[newStatus] || "Order updated.", "success");
    await renderOwnerOrder(orderId);
  } catch (e) {
    showToast(e.message || "Could not update the order.", "error");
    btn.disabled = false;
    btn.textContent = originalLabel;
  }
}
