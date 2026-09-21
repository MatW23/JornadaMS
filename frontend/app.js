const state = {
  accessToken: window.localStorage.getItem("jornada.accessToken"),
  refreshToken: window.localStorage.getItem("jornada.refreshToken"),
  user: null,
};

const $ = (selector) => document.querySelector(selector);

function saveTokens(tokens) {
  state.accessToken = tokens.access_token;
  state.refreshToken = tokens.refresh_token;
  window.localStorage.setItem("jornada.accessToken", state.accessToken);
  window.localStorage.setItem("jornada.refreshToken", state.refreshToken);
}

function clearSession() {
  state.accessToken = null;
  state.refreshToken = null;
  state.user = null;
  window.localStorage.removeItem("jornada.accessToken");
  window.localStorage.removeItem("jornada.refreshToken");
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 3200);
}

function showLogin(message = "") {
  $("#app-view").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
  $("#login-error").textContent = message;
}

function showApp() {
  $("#login-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  renderUser();
}

async function refreshSession() {
  if (!state.refreshToken) return false;
  const response = await fetch("/api/v1/auth/refresh", {
    body: JSON.stringify({ refresh_token: state.refreshToken }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });
  if (!response.ok) return false;
  saveTokens(await response.json());
  return true;
}

async function apiRequest(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (state.accessToken) headers.set("Authorization", `Bearer ${state.accessToken}`);
  let response = await fetch(path, { ...options, headers });
  if (response.status === 401 && retry && path !== "/api/v1/auth/refresh") {
    if (await refreshSession()) {
      headers.set("Authorization", `Bearer ${state.accessToken}`);
      response = await fetch(path, { ...options, headers });
    }
  }
  if (!response.ok) {
    let message = "Não foi possível concluir a operação.";
    try { message = (await response.json()).error?.message || message; } catch (_) { /* empty */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return null;
  return response.json();
}

async function loadUser() {
  state.user = await apiRequest("/api/v1/me");
  showApp();
  await checkDatabase();
}

function renderUser() {
  const email = state.user?.email || "Usuário";
  const name = email.split("@")[0].replace(/[._-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const initials = name.split(" ").map((part) => part[0]).join("").slice(0, 2) || "U";
  $("#welcome-title").textContent = `Olá, ${name}.`;
  $("#user-email").textContent = email;
  $("#user-role").textContent = state.user?.roles?.join(" · ") || "Usuário autenticado";
  $("#hero-role").textContent = state.user?.roles?.length ? state.user.roles.join(" · ") : "Usuário autenticado";
  $("#user-avatar").textContent = initials;
}

async function checkDatabase() {
  const statusElement = $("#database-status");
  try {
    await apiRequest("/health/ready", {}, false);
    statusElement.innerHTML = '<span class="status-dot"></span><span>Conectado</span>';
    $("#connection-value").textContent = "Online";
    $("#connection-description").textContent = "API e banco disponíveis";
  } catch (_) {
    statusElement.innerHTML = '<span class="status-dot" style="background:#f79009"></span><span>Verifique a conexão</span>';
    $("#connection-value").textContent = "Atenção";
    $("#connection-description").textContent = "Banco indisponível";
  }
}

function renderDate() {
  const now = new Date();
  const date = now.toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
  $("#current-date").textContent = date;
  $("#summary-date").textContent = now.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

async function handleLogin(event) {
  event.preventDefault();
  const button = $("#login-button");
  const errorElement = $("#login-error");
  button.disabled = true;
  errorElement.textContent = "";
  try {
    const response = await fetch("/api/v1/auth/login", {
      body: JSON.stringify({ email: $("#email").value, password: $("#password").value }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "Email ou senha inválidos.");
    saveTokens(data);
    $("#password").value = "";
    await loadUser();
    showToast("Login realizado com sucesso.");
  } catch (error) {
    errorElement.textContent = error.message || "Não foi possível entrar.";
  } finally {
    button.disabled = false;
  }
}

async function handleLogout() {
  try { await apiRequest("/api/v1/auth/logout", { method: "POST" }, false); } catch (_) { /* session may be expired */ }
  clearSession();
  showLogin();
  showToast("Sessão encerrada.");
}

$("#login-form").addEventListener("submit", handleLogin);
$("#logout-button").addEventListener("click", handleLogout);
renderDate();

if (state.accessToken) {
  loadUser().catch(() => { clearSession(); showLogin(); });
} else {
  showLogin();
}
