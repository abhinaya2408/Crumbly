/* ==========================================================
   Crumbly — customize.js
   ========================================================== */

const CREAM_ICONS = { Chocolate: "🍫", Vanilla: "🍦", Strawberry: "🍓", Butterscotch: "🧈" };
const DECO_ICONS = {
  "Fresh Flowers": "🌸",
  "Chocolate Decorations": "🍫",
  "Sprinkles": "✨",
  "Fruits": "🍒",
  "Birthday Theme": "🎉",
  "Custom Decoration": "🎨"
};

let customizeState = {
  flavor: null,
  cakeType: null, // "EGG" | "EGGLESS"
  size: null,
  cream: null,
  decorations: [],
  cakeMessage: "",
  specialInstructions: "",
  referenceImageFile: null, // the actual File, sent to Django
  requiredDate: "",
  pickupSlotId: null
};

let isSubmittingOrder = false;

async function initCustomizePage() {
  const student = await requireStudent();
  if (!student) return;

  buildFlavorGrid();
  buildCakeTypeGrid();
  buildSizeGrid();
  buildCreamGrid();
  buildDecoGrid();
  wireMessageCounter();
  wireInstructions();
  wireImageUpload();
  wireDateTime();
  wirePlaceOrder();

  updatePreview();
  updateSummary();

  const reorderFrom = new URLSearchParams(window.location.search).get("reorderFrom");
  if (reorderFrom) {
    await prefillFromReorder(reorderFrom);
  }
}

async function prefillFromReorder(orderId) {
  try {
    const prefill = await reorderOrder(orderId);
    selectCardByValue("flavorGrid", ".option-card", prefill.flavor);
    customizeState.flavor = prefill.flavor;
    selectCardByValue("cakeTypeGrid", ".pill-option", prefill.cake_type === "EGG" ? "Egg" : "Eggless");
    customizeState.cakeType = prefill.cake_type;
    selectCardByValue("sizeGrid", ".pill-option", prefill.size);
    customizeState.size = prefill.size;
    selectCardByValue("creamGrid", ".pill-option", prefill.cream);
    customizeState.cream = prefill.cream;

    (prefill.decorations || []).forEach((deco) => {
      const label = Array.from(document.querySelectorAll("#decoGrid .deco-option")).find(
        (el) => el.querySelector(".deco-label").textContent === deco
      );
      if (label && !label.classList.contains("selected")) {
        label.classList.add("selected");
        customizeState.decorations.push(deco);
      }
    });

    if (prefill.cake_message) {
      const msgInput = document.getElementById("cakeMessage");
      msgInput.value = prefill.cake_message;
      customizeState.cakeMessage = prefill.cake_message;
      document.getElementById("msgCount").textContent = prefill.cake_message.length;
    }
    if (prefill.special_instructions) {
      const instrInput = document.getElementById("specialInstructions");
      instrInput.value = prefill.special_instructions;
      customizeState.specialInstructions = prefill.special_instructions;
    }

    updatePreview();
    updateSummary();
    showToast("Loaded your previous order — feel free to make changes!", "success");
  } catch (e) {
    showToast(e.message || "Could not load that previous order.", "error");
  }
}

function selectCardByValue(gridId, selector, value) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  grid.querySelectorAll(selector).forEach((el) => {
    el.classList.toggle("selected", el.dataset.value === value);
  });
}

/* ---------- Builders ---------- */
function buildFlavorGrid() {
  const grid = document.getElementById("flavorGrid");
  FLAVORS.forEach((f) => {
    const card = document.createElement("div");
    card.className = "option-card";
    card.dataset.value = f.id;
    const price = SIZE_PRICES["1 Kg"] + f.base;
    card.innerHTML = `
      <div class="check-badge">✓</div>
      <div class="img-wrap"><img src="${cakeImages[f.key]}" alt="${f.id} cake"></div>
      <div class="option-card-body">
        <h4>${f.id}</h4>
        <p class="desc">${f.desc}</p>
        <div class="price">From ₹${price}</div>
      </div>`;
    card.addEventListener("click", () => {
      grid.querySelectorAll(".option-card").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      customizeState.flavor = f.id;
      updatePreview();
      updateSummary();
    });
    grid.appendChild(card);
  });
}

function buildCakeTypeGrid() {
  const grid = document.getElementById("cakeTypeGrid");
  grid.querySelectorAll(".pill-option").forEach((el) => {
    el.addEventListener("click", () => {
      grid.querySelectorAll(".pill-option").forEach((c) => c.classList.remove("selected"));
      el.classList.add("selected");
      // The markup's data-value is "Egg" / "Eggless" — the API expects EGG / EGGLESS.
      customizeState.cakeType = el.dataset.value.toUpperCase() === "EGG" ? "EGG" : "EGGLESS";
      updatePreview();
    });
  });
}

function buildSizeGrid() {
  const grid = document.getElementById("sizeGrid");
  Object.keys(SIZE_PRICES).forEach((size) => {
    const el = document.createElement("div");
    el.className = "pill-option";
    el.dataset.value = size;
    el.innerHTML = `
      <div class="pill-icon">🎂</div>
      <div class="pill-label">${size}</div>
      <div class="pill-sub">₹${SIZE_PRICES[size]}</div>`;
    el.addEventListener("click", () => {
      grid.querySelectorAll(".pill-option").forEach((c) => c.classList.remove("selected"));
      el.classList.add("selected");
      customizeState.size = size;
      updatePreview();
      updateSummary();
    });
    grid.appendChild(el);
  });
}

function buildCreamGrid() {
  const grid = document.getElementById("creamGrid");
  Object.keys(CREAM_ICONS).forEach((cream) => {
    const el = document.createElement("div");
    el.className = "pill-option";
    el.dataset.value = cream;
    el.innerHTML = `
      <div class="pill-icon">${CREAM_ICONS[cream]}</div>
      <div class="pill-label">${cream}</div>`;
    el.addEventListener("click", () => {
      grid.querySelectorAll(".pill-option").forEach((c) => c.classList.remove("selected"));
      el.classList.add("selected");
      customizeState.cream = cream;
      updatePreview();
    });
    grid.appendChild(el);
  });
}

function buildDecoGrid() {
  const grid = document.getElementById("decoGrid");
  Object.keys(DECORATION_PRICES).forEach((deco) => {
    const el = document.createElement("label");
    el.className = "deco-option";
    el.innerHTML = `
      <span class="deco-icon">${DECO_ICONS[deco] || "✨"}</span>
      <span class="deco-label">${deco}</span>
      <span class="deco-price">+₹${DECORATION_PRICES[deco]}</span>
      <input type="checkbox" value="${deco}" style="display:none;">`;
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const checked = el.classList.toggle("selected");
      if (checked) {
        customizeState.decorations.push(deco);
      } else {
        customizeState.decorations = customizeState.decorations.filter((d) => d !== deco);
      }
      updateSummary();
      updatePreview();
    });
    grid.appendChild(el);
  });
}

function wireMessageCounter() {
  const input = document.getElementById("cakeMessage");
  const count = document.getElementById("msgCount");
  input.addEventListener("input", () => {
    customizeState.cakeMessage = input.value;
    count.textContent = input.value.length;
    updatePreview();
  });
}

function wireInstructions() {
  const el = document.getElementById("specialInstructions");
  el.addEventListener("input", () => {
    customizeState.specialInstructions = el.value;
  });
}

function wireDateTime() {
  const dateInput = document.getElementById("requiredDate");
  const today = new Date().toISOString().slice(0, 10);
  dateInput.min = today;
  dateInput.addEventListener("change", () => {
    customizeState.requiredDate = dateInput.value;
    customizeState.pickupSlotId = null;
    loadSlotsForDate(dateInput.value);
  });
}

async function loadSlotsForDate(dateStr) {
  const grid = document.getElementById("slotGrid");
  const slotError = document.getElementById("slotError");
  slotError.classList.remove("show");

  if (!dateStr) {
    grid.innerHTML = `<p class="mb-0" id="slotHint" style="font-size:13px;color:var(--color-text-muted);">Choose a date above to see available pickup slots.</p>`;
    return;
  }

  grid.innerHTML = `<p class="mb-0" style="font-size:13px;color:var(--color-text-muted);">Loading available slots...</p>`;
  try {
    const slots = await getAvailablePickupSlots(dateStr);
    if (!slots.length) {
      grid.innerHTML = `<p class="mb-0" style="font-size:13px;color:var(--color-danger);">No pickup slots available on this date — the bakery may be closed, or every slot is fully booked. Please try another date.</p>`;
      return;
    }
    grid.innerHTML = "";
    slots.forEach((slot) => {
      const el = document.createElement("div");
      el.className = "pill-option";
      el.dataset.value = String(slot.id);
      el.innerHTML = `
        <div class="pill-icon">🕐</div>
        <div class="pill-label">${slot.label}</div>
        <div class="pill-sub">${slot.remaining} slot${slot.remaining === 1 ? "" : "s"} left</div>`;
      el.addEventListener("click", () => {
        grid.querySelectorAll(".pill-option").forEach((c) => c.classList.remove("selected"));
        el.classList.add("selected");
        customizeState.pickupSlotId = slot.id;
      });
      grid.appendChild(el);
    });
  } catch (e) {
    grid.innerHTML = "";
    slotError.textContent = e.message || "Could not load pickup slots for this date.";
    slotError.classList.add("show");
  }
}

/* ---------- Image upload ---------- */
function wireImageUpload() {
  const uploadArea = document.getElementById("uploadArea");
  const fileInput = document.getElementById("referenceImageInput");
  const chooseBtn = document.getElementById("chooseImageBtn");
  const preview = document.getElementById("uploadPreview");
  const previewImg = document.getElementById("uploadPreviewImg");
  const fileName = document.getElementById("uploadFileName");
  const fileSize = document.getElementById("uploadFileSize");
  const removeBtn = document.getElementById("removeImageBtn");
  const imageError = document.getElementById("imageError");

  chooseBtn.addEventListener("click", () => fileInput.click());
  uploadArea.addEventListener("click", (e) => {
    if (e.target === uploadArea || e.target.classList.contains("upload-icon") || e.target.classList.contains("upload-title") || e.target.classList.contains("upload-hint")) {
      fileInput.click();
    }
  });

  ["dragover", "dragenter"].forEach((evt) =>
    uploadArea.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadArea.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    uploadArea.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadArea.classList.remove("dragover");
    })
  );
  uploadArea.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleImageFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files[0]) {
      handleImageFile(fileInput.files[0]);
    }
  });

  function handleImageFile(file) {
    imageError.classList.remove("show");
    if (!["image/jpeg", "image/jpg", "image/png", "image/webp"].includes(file.type)) {
      imageError.textContent = "Please upload a JPG, PNG, or WEBP image.";
      imageError.classList.add("show");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      imageError.textContent = "Please upload an image smaller than 2 MB.";
      imageError.classList.add("show");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      customizeState.referenceImageFile = file;
      previewImg.src = reader.result;
      fileName.textContent = file.name;
      fileSize.textContent = (file.size / 1024).toFixed(0) + " KB";
      preview.classList.add("show");
      uploadArea.style.display = "none";
      showToast("Reference image uploaded", "success");
    };
    reader.onerror = () => {
      imageError.textContent = "Unable to upload image. Please try again.";
      imageError.classList.add("show");
    };
    reader.readAsDataURL(file);
  }

  removeBtn.addEventListener("click", () => {
    customizeState.referenceImageFile = null;
    fileInput.value = "";
    preview.classList.remove("show");
    uploadArea.style.display = "block";
  });
}

/* ---------- Live preview ---------- */
function updatePreview() {
  const img = document.getElementById("previewImage");
  const title = document.getElementById("previewTitle");
  const tags = document.getElementById("previewTags");
  const msgBox = document.getElementById("previewMessageBox");

  const flavor = FLAVORS.find((f) => f.id === customizeState.flavor);
  img.src = flavor ? cakeImages[flavor.key] : cakeImages.hero;
  img.alt = (customizeState.flavor || "Cake") + " preview";
  title.textContent = (customizeState.flavor || "Chocolate") + " Cake";

  const parts = [];
  if (customizeState.size) parts.push(customizeState.size);
  if (customizeState.cakeType) parts.push(customizeState.cakeType === "EGG" ? "Egg" : "Eggless");
  if (customizeState.cream) parts.push(customizeState.cream + " Cream");
  if (customizeState.decorations.length) parts.push(customizeState.decorations.join(", "));
  tags.textContent = parts.length ? parts.join(" · ") : "Select your options to see a live preview";

  if (customizeState.cakeMessage.trim()) {
    msgBox.style.display = "block";
    msgBox.textContent = '"' + customizeState.cakeMessage.trim() + '"';
  } else {
    msgBox.style.display = "none";
  }
}

/* ---------- Price summary (instant, frontend-only estimate) ---------- */
function updateSummary() {
  const { basePrice, decorPrice, total } = calculatePrice({
    flavor: customizeState.flavor,
    size: customizeState.size,
    decorations: customizeState.decorations
  });
  document.getElementById("sumBase").textContent = "₹" + basePrice;
  document.getElementById("sumDecor").textContent = "₹" + decorPrice;
  document.getElementById("sumTotal").textContent = "₹" + total;
}

/* ---------- Validation + Place order ---------- */
function wirePlaceOrder() {
  document.getElementById("placeOrderBtn").addEventListener("click", placeOrder);
}

async function placeOrder() {
  if (isSubmittingOrder) return; // guards against duplicate submissions on double-click

  const student = await requireStudent();
  if (!student) return;

  const formError = document.getElementById("formError");
  const dateError = document.getElementById("dateError");
  const slotError = document.getElementById("slotError");
  formError.classList.remove("show");
  dateError.classList.remove("show");
  slotError.classList.remove("show");

  const missing = [];
  if (!customizeState.flavor) missing.push("cake flavor");
  if (!customizeState.cakeType) missing.push("cake type (Egg/Eggless)");
  if (!customizeState.size) missing.push("cake size");
  if (!customizeState.cream) missing.push("cream");
  if (!customizeState.requiredDate) {
    missing.push("required date");
    dateError.textContent = "Please select a date.";
    dateError.classList.add("show");
  } else {
    const today = new Date().toISOString().slice(0, 10);
    if (customizeState.requiredDate < today) {
      missing.push("valid required date");
      dateError.textContent = "Please choose a date that is today or later.";
      dateError.classList.add("show");
    }
  }
  if (!customizeState.pickupSlotId) {
    missing.push("pickup slot");
    slotError.textContent = "Please select an available pickup slot.";
    slotError.classList.add("show");
  }

  if (missing.length) {
    formError.textContent = "Please complete: " + missing.join(", ") + ".";
    formError.classList.add("show");
    showToast("Please fill in all required fields.", "error");
    return;
  }

  const placeOrderBtn = document.getElementById("placeOrderBtn");
  const originalLabel = placeOrderBtn.textContent;

  const formData = new FormData();
  formData.append("flavor", customizeState.flavor);
  formData.append("cake_type", customizeState.cakeType);
  formData.append("size", customizeState.size);
  formData.append("cream", customizeState.cream);
  formData.append("decorations", JSON.stringify(customizeState.decorations));
  formData.append("cake_message", customizeState.cakeMessage.trim());
  formData.append("special_instructions", customizeState.specialInstructions.trim());
  formData.append("required_date", customizeState.requiredDate);
  formData.append("pickup_slot", customizeState.pickupSlotId);
  const reorderFrom = new URLSearchParams(window.location.search).get("reorderFrom");
  if (reorderFrom) formData.append("reordered_from", reorderFrom);
  if (customizeState.referenceImageFile) {
    formData.append("reference_image", customizeState.referenceImageFile);
  }

  try {
    isSubmittingOrder = true;
    placeOrderBtn.disabled = true;
    placeOrderBtn.textContent = "Creating your order...";

    const order = await createOrder(formData);

    showToast("Order placed successfully! 🎂", "success");
    setTimeout(() => {
      window.location.href = "order-confirmation.html?orderId=" + encodeURIComponent(order.order_id);
    }, 500);
  } catch (err) {
    formError.textContent = err.message || "Could not place your order. Please try again.";
    formError.classList.add("show");
    showToast(err.message || "Could not place your order.", "error");
    placeOrderBtn.disabled = false;
    placeOrderBtn.textContent = originalLabel;
    isSubmittingOrder = false;
  }
}
