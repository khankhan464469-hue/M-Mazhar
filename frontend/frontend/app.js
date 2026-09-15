const tabs = document.querySelectorAll(".tab");
const panels = {
  login: document.querySelector("#loginForm"),
  customer: document.querySelector("#customerForm"),
  admin: document.querySelector("#adminForm"),
  forgot: document.querySelector("#forgotForm"),
};
const messageBox = document.querySelector("#messageBox");
const sessionStatus = document.querySelector("#sessionStatus");
const logoutButton = document.querySelector("#logoutButton");
const profileOutput = document.querySelector("#profileOutput");

let session = JSON.parse(localStorage.getItem("eventPortalSession") || "null");

function setTab(name) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
  Object.entries(panels).forEach(([key, panel]) => {
    panel.classList.toggle("active", key === name);
  });
  showMessage("", "");
}

function showMessage(text, type = "") {
  messageBox.textContent = text;
  messageBox.className = `message ${type}`.trim();
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function saveSession(data) {
  session = data;
  localStorage.setItem("eventPortalSession", JSON.stringify(data));
  renderSession();
}

function clearSession() {
  session = null;
  localStorage.removeItem("eventPortalSession");
  renderSession();
  profileOutput.textContent = "Login as admin to view records.";
}

function renderSession() {
  if (!session?.access_token) {
    sessionStatus.textContent = "Not signed in";
    logoutButton.hidden = true;
    return;
  }

  sessionStatus.textContent = `${session.full_name || session.email} (${session.role})`;
  logoutButton.hidden = false;
}

async function apiRequest(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok || data.error) {
    throw new Error(data.detail || data.error || "Request failed");
  }

  return data;
}

async function submitForm(form, path, successMessage) {
  showMessage("Working...", "");

  try {
    const data = await apiRequest(path, {
      method: "POST",
      body: JSON.stringify(formData(form)),
    });

    if (data.access_token) {
      saveSession(data);
    }

    form.reset();
    const note = data.note ? `\n${data.note}` : "";
    showMessage(`${successMessage || data.message}${note}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadProfiles(role) {
  if (!session?.access_token) {
    showMessage("Please login as admin first.", "error");
    return;
  }

  profileOutput.textContent = "Loading...";

  try {
    const data = await apiRequest(`/profiles/${role}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
    });

    profileOutput.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    profileOutput.textContent = error.message;
    showMessage(error.message, "error");
  }
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setTab(tab.dataset.tab));
});

panels.login.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/login", "Login successful.");
});

panels.customer.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/signup", "Customer account created and saved.");
});

panels.admin.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/admin/signup", "Admin account created and saved.");
});

panels.forgot.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/forgot-password", "Password reset email sent.");
});

document.querySelector("#loadCustomers").addEventListener("click", () => loadProfiles("customers"));
document.querySelector("#loadAdmins").addEventListener("click", () => loadProfiles("admins"));
logoutButton.addEventListener("click", clearSession);

document.querySelectorAll(".side-nav a").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".side-nav a").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

renderSession();
