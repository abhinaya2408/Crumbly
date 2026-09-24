/* ==========================================================
   Crumbly — notifications.js
   ========================================================== */

async function initNotificationsPage() {
  const student = await requireStudent();
  if (!student) return;

  const listEl = document.getElementById("notifList");
  const emptyEl = document.getElementById("notifEmptyState");
  const markAllBtn = document.getElementById("markAllReadBtn");

  async function refreshBadges() {
    try {
      const notifications = await getNotifications();
      const count = notifications.filter((n) => !n.is_read).length;
      document.querySelectorAll("[data-unread-badge]").forEach((el) => {
        if (count > 0) {
          el.textContent = count;
          el.style.display = "inline-flex";
        } else {
          el.style.display = "none";
        }
      });
    } catch (e) {
      /* ignore — badge just stays as-is */
    }
  }

  async function render() {
    listEl.innerHTML = `<p class="mb-0">Loading notifications...</p>`;
    let notifications = [];
    try {
      notifications = await getNotifications();
    } catch (e) {
      showToast(e.message || "Could not load notifications.", "error");
    }
    notifications = notifications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    listEl.innerHTML = "";
    if (!notifications.length) {
      emptyEl.style.display = "block";
      listEl.style.display = "none";
      return;
    }
    emptyEl.style.display = "none";
    listEl.style.display = "flex";

    notifications.forEach((n) => {
      const item = document.createElement("div");
      item.className = "notif-item" + (n.is_read ? "" : " unread");
      item.innerHTML = `
        <span class="notif-icon">🔔</span>
        <div class="notif-content">
          <div class="notif-message">${n.message}</div>
          <div class="notif-time">${timeAgo(n.created_at)} · Order #${n.order_id}</div>
        </div>
        ${!n.is_read ? '<span class="notif-unread-dot"></span>' : ""}`;
      item.style.cursor = "pointer";
      item.addEventListener("click", async () => {
        if (!n.is_read) {
          try {
            await markNotificationRead(n.id);
            await refreshBadges();
          } catch (e) {
            /* non-fatal — still navigate to the order */
          }
        }
        window.location.href = "order-details.html?orderId=" + encodeURIComponent(n.order_id);
      });
      listEl.appendChild(item);
    });

    await refreshBadges();
  }

  markAllBtn.addEventListener("click", async () => {
    markAllBtn.disabled = true;
    try {
      await markAllNotificationsRead();
      showToast("All notifications marked as read.", "success");
      await render();
    } catch (e) {
      showToast(e.message || "Could not update notifications.", "error");
    } finally {
      markAllBtn.disabled = false;
    }
  });

  render();
}
