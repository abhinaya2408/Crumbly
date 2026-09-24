/* ==========================================================
   Crumbly — pickup-slots-admin.js
   Bakery-side management of recurring pickup slots + closed dates.
   ========================================================== */

async function initOwnerPickupSlotsPage() {
  const session = await requireBakery();
  if (!session) return;

  const sidebar = document.getElementById("ownerSidebar");
  const mobileToggle = document.getElementById("mobileSidebarToggle");
  if (mobileToggle) mobileToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  await loadSlots();
  await loadClosedDates();
  wireAddSlot();
  wireAddClosedDate();
}

async function loadSlots() {
  const grid = document.getElementById("slotGridManage");
  grid.innerHTML = `<p class="mb-0">Loading slots...</p>`;
  try {
    const slots = await getPickupSlots();
    if (!slots.length) {
      grid.innerHTML = `<p class="mb-0">No pickup slots configured yet — add one below.</p>`;
      return;
    }
    grid.innerHTML = "";
    slots.forEach((slot) => {
      const card = document.createElement("div");
      card.className = "slot-card" + (slot.is_active ? "" : " inactive");
      card.innerHTML = `
        <div class="slot-time">${formatTime(slot.start_time)} – ${formatTime(slot.end_time)}</div>
        <div class="slot-meta">Max ${slot.max_orders_per_day} orders/day · ${slot.is_active ? "Active" : "Inactive"}</div>
        <div class="slot-actions">
          <button class="btn btn-outline btn-sm" data-action="toggle">${slot.is_active ? "Deactivate" : "Activate"}</button>
          <button class="btn btn-danger btn-sm" data-action="delete">Delete</button>
        </div>`;
      card.querySelector('[data-action="toggle"]').addEventListener("click", async () => {
        try {
          await updatePickupSlot(slot.id, { is_active: !slot.is_active });
          await loadSlots();
        } catch (e) {
          showToast(e.message || "Could not update slot.", "error");
        }
      });
      card.querySelector('[data-action="delete"]').addEventListener("click", async () => {
        if (!window.confirm("Delete this pickup slot? Existing orders keep their booked time.")) return;
        try {
          await deletePickupSlot(slot.id);
          showToast("Slot deleted.", "success");
          await loadSlots();
        } catch (e) {
          showToast(e.message || "Could not delete slot.", "error");
        }
      });
      grid.appendChild(card);
    });
  } catch (e) {
    grid.innerHTML = `<p class="mb-0" style="color:var(--color-danger);">${e.message || "Could not load pickup slots."}</p>`;
  }
}

function wireAddSlot() {
  document.getElementById("addSlotBtn").addEventListener("click", async () => {
    const start = document.getElementById("slotStart").value;
    const end = document.getElementById("slotEnd").value;
    const capacity = parseInt(document.getElementById("slotCapacity").value, 10) || 1;
    const errorEl = document.getElementById("slotFormError");
    errorEl.classList.remove("show");

    if (!start || !end) {
      errorEl.textContent = "Please choose both a start and end time.";
      errorEl.classList.add("show");
      return;
    }

    try {
      await createPickupSlot({ start_time: start, end_time: end, max_orders_per_day: capacity, is_active: true });
      showToast("Pickup slot added.", "success");
      document.getElementById("slotStart").value = "";
      document.getElementById("slotEnd").value = "";
      await loadSlots();
    } catch (e) {
      errorEl.textContent = e.message || "Could not add this slot.";
      errorEl.classList.add("show");
    }
  });
}

async function loadClosedDates() {
  const body = document.getElementById("closedDatesBody");
  body.innerHTML = `<tr><td colspan="3">Loading...</td></tr>`;
  try {
    const dates = await getClosedDates();
    if (!dates.length) {
      body.innerHTML = `<tr><td colspan="3">No upcoming closed dates.</td></tr>`;
      return;
    }
    body.innerHTML = "";
    dates.forEach((d) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${formatDate(d.date)}</td><td>${d.reason || "—"}</td><td></td>`;
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "btn btn-danger btn-sm";
      deleteBtn.textContent = "Remove";
      deleteBtn.addEventListener("click", async () => {
        try {
          await deleteClosedDate(d.id);
          showToast("Closed date removed.", "success");
          await loadClosedDates();
        } catch (e) {
          showToast(e.message || "Could not remove this date.", "error");
        }
      });
      tr.lastElementChild.appendChild(deleteBtn);
      body.appendChild(tr);
    });
  } catch (e) {
    body.innerHTML = `<tr><td colspan="3" style="color:var(--color-danger);">${e.message || "Could not load closed dates."}</td></tr>`;
  }
}

function wireAddClosedDate() {
  document.getElementById("addClosedDateBtn").addEventListener("click", async () => {
    const dateVal = document.getElementById("closedDateInput").value;
    const reason = document.getElementById("closedReasonInput").value.trim();
    const errorEl = document.getElementById("closedFormError");
    errorEl.classList.remove("show");

    if (!dateVal) {
      errorEl.textContent = "Please choose a date.";
      errorEl.classList.add("show");
      return;
    }

    try {
      await createClosedDate({ date: dateVal, reason });
      showToast("Closed date added.", "success");
      document.getElementById("closedDateInput").value = "";
      document.getElementById("closedReasonInput").value = "";
      await loadClosedDates();
    } catch (e) {
      errorEl.textContent = e.message || "Could not add this closed date.";
      errorEl.classList.add("show");
    }
  });
}
