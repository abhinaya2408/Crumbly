/* ==========================================================
   Crumbly — inventory-admin.js
   Bakery-side ingredient/inventory CRUD + low-stock warnings.
   ========================================================== */

const CATEGORY_LABELS = {
  CREAM: "Cream",
  FLAVOR_BASE: "Flavor / Base",
  DECORATION: "Decoration",
  PACKAGING: "Packaging",
  OTHER: "Other"
};

async function initOwnerInventoryPage() {
  const session = await requireBakery();
  if (!session) return;

  const sidebar = document.getElementById("ownerSidebar");
  const mobileToggle = document.getElementById("mobileSidebarToggle");
  if (mobileToggle) mobileToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

  await loadInventory();
  wireAddItem();
}

async function loadInventory() {
  const body = document.getElementById("inventoryBody");
  const banner = document.getElementById("lowStockBannerInv");
  body.innerHTML = `<tr><td colspan="6">Loading inventory...</td></tr>`;

  try {
    const items = await getInventory();
    const lowCount = items.filter((i) => i.is_low_stock).length;
    banner.innerHTML =
      lowCount > 0
        ? `<div class="warning-banner">⚠️ ${lowCount} ingredient${lowCount === 1 ? "" : "s"} running low on stock.</div>`
        : "";

    if (!items.length) {
      body.innerHTML = `<tr><td colspan="6">No inventory items yet — add one above.</td></tr>`;
      return;
    }

    body.innerHTML = "";
    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${item.name}</td>
        <td><span class="category-badge">${CATEGORY_LABELS[item.category] || item.category}</span></td>
        <td>
          <input type="number" step="0.1" min="0" value="${item.quantity}" data-field="quantity" style="width:90px;">
          ${item.unit}
        </td>
        <td>${item.minimum_stock} ${item.unit}</td>
        <td>${item.is_low_stock ? '<span class="badge-warning">⚠️ Low Stock</span>' : '<span class="pill pill-ready">Available</span>'}</td>
        <td></td>`;

      const qtyInput = tr.querySelector('[data-field="quantity"]');
      qtyInput.addEventListener("change", async () => {
        try {
          await updateInventoryItem(item.id, { quantity: qtyInput.value });
          showToast("Quantity updated.", "success");
          await loadInventory();
        } catch (e) {
          showToast(e.message || "Could not update quantity.", "error");
        }
      });

      const actionsCell = tr.lastElementChild;
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "btn btn-danger btn-sm";
      deleteBtn.textContent = "Delete";
      deleteBtn.addEventListener("click", async () => {
        if (!window.confirm(`Delete "${item.name}" from inventory?`)) return;
        try {
          await deleteInventoryItem(item.id);
          showToast("Item deleted.", "success");
          await loadInventory();
        } catch (e) {
          showToast(e.message || "Could not delete item.", "error");
        }
      });
      actionsCell.appendChild(deleteBtn);
      body.appendChild(tr);
    });
  } catch (e) {
    body.innerHTML = `<tr><td colspan="6" style="color:var(--color-danger);">${e.message || "Could not load inventory."}</td></tr>`;
  }
}

function wireAddItem() {
  document.getElementById("addItemBtn").addEventListener("click", async () => {
    const name = document.getElementById("itemName").value.trim();
    const category = document.getElementById("itemCategory").value;
    const quantity = document.getElementById("itemQuantity").value;
    const unit = document.getElementById("itemUnit").value.trim() || "kg";
    const minimum = document.getElementById("itemMinimum").value;
    const errorEl = document.getElementById("itemFormError");
    errorEl.classList.remove("show");

    if (!name) {
      errorEl.textContent = "Please enter an item name.";
      errorEl.classList.add("show");
      return;
    }

    try {
      await createInventoryItem({
        name,
        category,
        quantity,
        unit,
        minimum_stock: minimum
      });
      showToast("Item added to inventory.", "success");
      document.getElementById("itemName").value = "";
      document.getElementById("itemQuantity").value = "0";
      document.getElementById("itemMinimum").value = "0";
      await loadInventory();
    } catch (e) {
      errorEl.textContent = e.message || "Could not add this item.";
      errorEl.classList.add("show");
    }
  });
}
