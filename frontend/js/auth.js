/* ==========================================================
   Crumbly — auth.js
   Student login/register + Bakery member login.
   ========================================================== */

function showFieldError(inputEl, errorEl, message) {
  if (message) {
    inputEl.classList.add("input-error");
    errorEl.textContent = message;
    errorEl.classList.add("show");
  } else {
    inputEl.classList.remove("input-error");
    errorEl.classList.remove("show");
  }
}

function setSubmitLoading(button, isLoading, loadingText, idleText) {
  button.disabled = isLoading;
  button.textContent = isLoading ? loadingText : idleText;
}

/* ---------- Student Login ---------- */
async function initStudentLoginPage() {
  // If already logged in, skip straight to the dashboard
  const existing = await getCurrentUser();
  if (existing && existing.role === "student") {
    window.location.href = "customize.html";
    return;
  }

  const form = document.getElementById("loginForm");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const emailError = document.getElementById("emailError");
  const passwordError = document.getElementById("passwordError");
  const submitBtn = form.querySelector('button[type="submit"]');
  const submitLabel = submitBtn ? submitBtn.textContent : "Sign In";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    let valid = true;

    const email = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;

    if (!email || !email.includes("@")) {
      showFieldError(emailInput, emailError, "Please enter a valid email address.");
      valid = false;
    } else {
      showFieldError(emailInput, emailError, "");
    }

    if (!password) {
      showFieldError(passwordInput, passwordError, "Password is required.");
      valid = false;
    } else {
      showFieldError(passwordInput, passwordError, "");
    }

    if (!valid) return;

    try {
      if (submitBtn) setSubmitLoading(submitBtn, true, "Signing in...", submitLabel);
      const data = await loginStudent({ email, password });
      showToast(data.detail, "success");
      setTimeout(() => (window.location.href = "customize.html"), 600);
    } catch (err) {
      showFieldError(passwordInput, passwordError, err.message || "Incorrect email or password.");
      if (submitBtn) setSubmitLoading(submitBtn, false, "Signing in...", submitLabel);
    }
  });
}

/* ---------- Student Registration ---------- */
async function initStudentRegisterPage() {
  const existing = await getCurrentUser();
  if (existing && existing.role === "student") {
    window.location.href = "customize.html";
    return;
  }

  const domainHint = document.getElementById("domainHint");
  if (domainHint) domainHint.textContent = COLLEGE_EMAIL_DOMAIN;

  const form = document.getElementById("registerForm");
  const fields = {
    fullName: document.getElementById("fullName"),
    studentId: document.getElementById("studentId"),
    phone: document.getElementById("phone"),
    email: document.getElementById("email"),
    department: document.getElementById("department"),
    year: document.getElementById("year"),
    password: document.getElementById("password"),
    confirmPassword: document.getElementById("confirmPassword")
  };
  const errors = {
    fullName: document.getElementById("fullNameError"),
    studentId: document.getElementById("studentIdError"),
    phone: document.getElementById("phoneError"),
    email: document.getElementById("emailError"),
    password: document.getElementById("passwordError"),
    confirmPassword: document.getElementById("confirmPasswordError")
  };
  const submitBtn = form.querySelector('button[type="submit"]');
  const submitLabel = submitBtn ? submitBtn.textContent : "Create Account";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    let valid = true;

    const values = {
      fullName: fields.fullName.value.trim(),
      studentId: fields.studentId.value.trim(),
      phone: fields.phone.value.trim(),
      email: fields.email.value.trim().toLowerCase(),
      department: fields.department.value.trim(),
      year: fields.year.value,
      password: fields.password.value,
      confirmPassword: fields.confirmPassword.value
    };

    if (!values.fullName) {
      showFieldError(fields.fullName, errors.fullName, "Full name is required.");
      valid = false;
    } else showFieldError(fields.fullName, errors.fullName, "");

    if (!values.studentId) {
      showFieldError(fields.studentId, errors.studentId, "Student ID is required.");
      valid = false;
    } else showFieldError(fields.studentId, errors.studentId, "");

    if (!/^\d{10}$/.test(values.phone)) {
      showFieldError(fields.phone, errors.phone, "Enter a valid 10-digit phone number.");
      valid = false;
    } else showFieldError(fields.phone, errors.phone, "");

    if (!values.email.endsWith(COLLEGE_EMAIL_DOMAIN)) {
      showFieldError(fields.email, errors.email, "Please use your official college email address.");
      valid = false;
    } else showFieldError(fields.email, errors.email, "");

    if (values.password.length < 6) {
      showFieldError(fields.password, errors.password, "Password must be at least 6 characters.");
      valid = false;
    } else showFieldError(fields.password, errors.password, "");

    if (values.confirmPassword !== values.password || !values.confirmPassword) {
      showFieldError(fields.confirmPassword, errors.confirmPassword, "Passwords do not match.");
      valid = false;
    } else showFieldError(fields.confirmPassword, errors.confirmPassword, "");

    if (!valid) return;

    try {
      if (submitBtn) setSubmitLoading(submitBtn, true, "Creating your account...", submitLabel);
      const data = await registerStudent({
        name: values.fullName,
        student_id: values.studentId,
        phone: values.phone,
        email: values.email,
        department: values.department,
        year: values.year,
        password: values.password
      });
      showToast(data.detail, "success");
      setTimeout(() => (window.location.href = "customize.html"), 700);
    } catch (err) {
      if (submitBtn) setSubmitLoading(submitBtn, false, "Creating your account...", submitLabel);
      // Map field-specific backend errors back onto the right input where possible
      const backendErrors = err.errors || {};
      if (backendErrors.email) showFieldError(fields.email, errors.email, backendErrors.email[0]);
      if (backendErrors.student_id) showFieldError(fields.studentId, errors.studentId, backendErrors.student_id[0]);
      if (backendErrors.phone) showFieldError(fields.phone, errors.phone, backendErrors.phone[0]);
      if (backendErrors.password) showFieldError(fields.password, errors.password, backendErrors.password[0]);
      if (!Object.keys(backendErrors).length) {
        showToast(err.message || "Could not create your account. Please try again.", "error");
      }
    }
  });
}

/* ---------- Bakery Member Login ---------- */
async function initOwnerLoginPage() {
  const existing = await getCurrentUser();
  if (existing && existing.role === "bakery") {
    window.location.href = "owner-dashboard.html";
    return;
  }

  const form = document.getElementById("ownerLoginForm");
  const emailInput = document.getElementById("ownerEmail");
  const passwordInput = document.getElementById("ownerPassword");
  const emailError = document.getElementById("ownerEmailError");
  const passwordError = document.getElementById("ownerPasswordError");
  const submitBtn = form.querySelector('button[type="submit"]');
  const submitLabel = submitBtn ? submitBtn.textContent : "Sign In";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;

    showFieldError(emailInput, emailError, "");
    showFieldError(passwordInput, passwordError, "");

    try {
      if (submitBtn) setSubmitLoading(submitBtn, true, "Signing in...", submitLabel);
      const data = await loginBakery({ email, password });
      showToast(data.detail, "success");
      setTimeout(() => (window.location.href = "owner-dashboard.html"), 600);
    } catch (err) {
      showFieldError(passwordInput, passwordError, err.message || "Incorrect email or password.");
      if (submitBtn) setSubmitLoading(submitBtn, false, "Signing in...", submitLabel);
    }
  });
}

/* ---------- Logout handlers (shared) ---------- */
async function handleStudentLogout() {
  await logoutStudent();
  window.location.href = "student-login.html";
}
async function handleOwnerLogout() {
  await logoutBakery();
  window.location.href = "bakery-login.html";
}
