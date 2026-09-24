/* ==========================================================
   Crumbly — analytics-admin.js
   Renders GET /api/bakery/analytics/ as simple CSS bar charts —
   no external chart library needed, per project constraints.
   ========================================================== */

async function initOwnerAnalyticsPage() {
  const session = await requireBakery();
  if (!session) return;

  const sidebar = document.getElementById("ownerSidebar");
  const mobileToggle = document.getElementById("mobileSidebarToggle");
  if (mobileToggle) mobileToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  try {
    const data = await getBakeryAnalytics();
    renderStats(data);
    renderDailyChart(data.orders_per_day);
    renderBarChart("chartFlavors", data.popular_flavors, "flavor");
    renderBarChart("chartSizes", data.popular_sizes, "size");
    renderBarChart("chartEggless", data.egg_vs_eggless, "cake_type");
    renderBarChart("chartCreams", data.popular_creams, "cream");
    renderBarChart("chartDecorations", data.popular_decorations, "decorations");
    renderRatings(data);
    renderRecentReviews(data.recent_reviews);
  } catch (e) {
    document.getElementById("analyticsStats").innerHTML = `<p class="mb-0" style="color:var(--color-danger);">${e.message || "Could not load analytics."}</p>`;
  }
}

function renderStats(data) {
  const grid = document.getElementById("analyticsStats");
  grid.innerHTML = `
    <div class="owner-stat-card"><div class="stat-num">${data.orders_today}</div><div class="stat-label">Orders Today</div></div>
    <div class="owner-stat-card"><div class="stat-num">${data.orders_week}</div><div class="stat-label">Orders This Week</div></div>
    <div class="owner-stat-card"><div class="stat-num">${data.orders_month}</div><div class="stat-label">Orders This Month</div></div>
    <div class="owner-stat-card"><div class="stat-num">${data.completed_orders}</div><div class="stat-label">Completed</div></div>
    <div class="owner-stat-card"><div class="stat-num">${data.rejected_orders}</div><div class="stat-label">Rejected</div></div>
    <div class="owner-stat-card"><div class="stat-num">${data.cancelled_orders}</div><div class="stat-label">Cancelled</div></div>
    <div class="owner-stat-card"><div class="stat-num">₹${data.revenue_today}</div><div class="stat-label">Revenue Today</div></div>
    <div class="owner-stat-card"><div class="stat-num">₹${data.revenue_week}</div><div class="stat-label">Revenue This Week</div></div>
    <div class="owner-stat-card"><div class="stat-num">₹${data.revenue_month}</div><div class="stat-label">Revenue This Month</div></div>`;
}

function renderDailyChart(orderPerDay) {
  const el = document.getElementById("dailyChart");
  const max = Math.max(1, ...orderPerDay.map((d) => d.count));
  el.innerHTML = orderPerDay
    .map((d) => {
      const heightPct = Math.max(4, Math.round((d.count / max) * 100));
      const label = new Date(d.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" });
      return `<div class="day-col">
        <div class="day-count">${d.count}</div>
        <div class="day-bar" style="height:${heightPct}%;"></div>
        <div class="day-label">${label}</div>
      </div>`;
    })
    .join("");
}

function renderBarChart(containerId, rows, keyField) {
  const el = document.getElementById(containerId);
  if (!rows || !rows.length) {
    el.innerHTML = `<p class="mb-0" style="font-size:13px;">No data yet.</p>`;
    return;
  }
  const max = Math.max(...rows.map((r) => r.count));
  el.innerHTML = rows
    .map((r) => {
      const label = r[keyField] || "—";
      const pct = Math.max(4, Math.round((r.count / max) * 100));
      return `<div class="bar-chart-row">
        <span class="bar-label">${label}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${pct}%;"></span></span>
        <span class="bar-value">${r.count}</span>
      </div>`;
    })
    .join("");
}

function renderRatings(data) {
  const el = document.getElementById("ratingsSummary");
  if (!data.review_count) {
    el.innerHTML = `<p class="mb-0" style="font-size:13px;">No reviews yet.</p>`;
    return;
  }
  el.innerHTML = `
    <div class="star-display" style="font-size:22px;">${starString(Math.round(data.average_rating))}</div>
    <p class="mb-0" style="margin-top:6px;">${data.average_rating} average from ${data.review_count} review${data.review_count === 1 ? "" : "s"}</p>`;
}

function renderRecentReviews(reviews) {
  const el = document.getElementById("recentReviews");
  if (!reviews || !reviews.length) {
    el.innerHTML = `<p class="mb-0" style="font-size:13px;">No reviews yet.</p>`;
    return;
  }
  el.innerHTML = reviews
    .map(
      (r) => `
      <div class="review-card">
        <div class="review-header">
          <span class="review-author">${r.student_name}</span>
          <span class="star-display">${starString(r.overall_rating)}</span>
        </div>
        ${r.comment ? `<div class="review-comment">"${r.comment}"</div>` : ""}
        <div class="review-date">${timeAgo(r.created_at)}</div>
      </div>`
    )
    .join("");
}
