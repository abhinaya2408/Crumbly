/* ==========================================================
   Crumbly — profile.js
   Student profile: view details, edit phone/department/year.
   ========================================================== */

const YEAR_LABELS = { "1": "1st Year", "2": "2nd Year", "3": "3rd Year", "4": "4th Year", PG: "Postgraduate" };

async function initStudentProfilePage() {
  const student = await requireStudent();
  if (!student) return;

  renderProfile(student);
}

function renderProfile(profile) {
  const root = document.getElementById("profileRoot");
  const initial = (profile.full_name || "?").trim().charAt(0).toUpperCase();

  root.innerHTML = `
    <div class="profile-avatar">${initial}</div>
    <div class="detail-row"><span class="label">Full Name</span><span class="value">${profile.full_name}</span></div>
    <div class="detail-row"><span class="label">Student ID</span><span class="value">${profile.student_id}</span></div>
    <div class="detail-row"><span class="label">College Email</span><span class="value">${profile.email}</span></div>
    <div class="detail-row"><span class="label">Phone</span><span class="value">${profile.phone}</span></div>
    <div class="detail-row"><span class="label">Department</span><span class="value">${profile.department || "—"}</span></div>
    <div class="detail-row"><span class="label">Year</span><span class="value">${YEAR_LABELS[profile.year] || "—"}</span></div>
    <button class="btn btn-secondary btn-sm" id="editProfileBtn" style="margin-top:var(--sp-3);">Edit Details</button>
  `;

  document.getElementById("editProfileBtn").addEventListener("click", () => renderEditForm(profile));
}

function renderEditForm(profile) {
  const root = document.getElementById("profileRoot");
  root.innerHTML = `
    <h3>Edit Profile</h3>
    <p class="mb-0" style="font-size:13px;">Your name, Student ID, and college email can't be changed here — contact the bakery admin for that.</p>

    <div class="form-group" style="margin-top:var(--sp-3);">
      <label for="phoneInput">Phone Number</label>
      <input type="tel" id="phoneInput" value="${profile.phone}">
      <div class="field-error" id="phoneError"></div>
    </div>

    <div class="form-group">
      <label for="departmentInput">Department</label>
      <input type="text" id="departmentInput" value="${profile.department || ""}" placeholder="e.g. Computer Science">
    </div>

    <div class="form-group">
      <label for="yearInput">Year / Semester</label>
      <select id="yearInput">
        <option value="">Select year</option>
        <option value="1">1st Year</option>
        <option value="2">2nd Year</option>
        <option value="3">3rd Year</option>
        <option value="4">4th Year</option>
        <option value="PG">Postgraduate</option>
      </select>
    </div>

    <div class="field-error" id="formError"></div>
    <div style="display:flex; gap:10px; margin-top:var(--sp-3);">
      <button class="btn btn-primary" id="saveProfileBtn">Save Changes</button>
      <button class="btn btn-outline" id="cancelEditBtn">Cancel</button>
    </div>
  `;

  document.getElementById("yearInput").value = profile.year || "";

  document.getElementById("cancelEditBtn").addEventListener("click", () => renderProfile(profile));

  document.getElementById("saveProfileBtn").addEventListener("click", async () => {
    const phoneInput = document.getElementById("phoneInput");
    const phoneError = document.getElementById("phoneError");
    const formError = document.getElementById("formError");
    phoneError.classList.remove("show");
    formError.classList.remove("show");

    if (!/^\d{10}$/.test(phoneInput.value.trim())) {
      phoneError.textContent = "Enter a valid 10-digit phone number.";
      phoneError.classList.add("show");
      return;
    }

    const btn = document.getElementById("saveProfileBtn");
    btn.disabled = true;
    btn.textContent = "Saving...";
    try {
      const updated = await updateStudentProfile({
        phone: phoneInput.value.trim(),
        department: document.getElementById("departmentInput").value.trim(),
        year: document.getElementById("yearInput").value
      });
      showToast("Profile updated.", "success");
      renderProfile(updated);
    } catch (e) {
      formError.textContent = e.message || "Could not save changes.";
      formError.classList.add("show");
      btn.disabled = false;
      btn.textContent = "Save Changes";
    }
  });
}
