const state = {
  user: null,
};

const $ = (selector) => document.querySelector(selector);

function clearSession() {
  state.user = null;
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
  const response = await fetch("/api/v1/auth/refresh", {
    body: JSON.stringify({}),
    headers: { "Content-Type": "application/json" },
    method: "POST",
    credentials: "same-origin",
  });
  if (!response.ok) return false;
  return true;
}

async function apiRequest(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  let response = await fetch(path, { ...options, headers, credentials: "same-origin" });
  if (response.status === 401 && retry && path !== "/api/v1/auth/refresh") {
    if (await refreshSession()) {
      response = await fetch(path, { ...options, headers, credentials: "same-origin" });
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

async function loadEmployees() {
  const table = $("#employees-table");
  try {
    const [employees, branches] = await Promise.all([
      apiRequest("/api/v1/employees"),
      apiRequest("/api/v1/branches"),
    ]);
    $("#employee-branch").innerHTML = branches.items.map((branch) => `<option value="${escapeHtml(branch.id)}">${escapeHtml(branch.name)} · ${escapeHtml(branch.code)}</option>`).join("");
    table.innerHTML = employees.items.length
      ? employees.items.map((employee) => `<tr><td><strong>${escapeHtml(employee.name)}</strong></td><td>${escapeHtml(employee.registration_code)}</td><td>${escapeHtml(branches.items.find((branch) => branch.id === employee.branch_id)?.name || "—")}</td><td><span class="status-tag">${employee.status === "ACTIVE" ? "Ativo" : "Inativo"}</span></td></tr>`).join("")
      : '<tr><td colspan="4" class="table-empty">Nenhum colaborador cadastrado.</td></tr>';
  } catch (error) {
    table.innerHTML = `<tr><td colspan="4" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
  }
}

function today() {
  const current = new Date();
  const year = current.getFullYear();
  const month = String(current.getMonth() + 1).padStart(2, "0");
  const day = String(current.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

async function loadAttendance() {
  const table = $("#attendance-table");
  const employeeSelect = $("#attendance-employee");
  try {
    const employees = await apiRequest("/api/v1/employees");
    employeeSelect.innerHTML = employees.items.map((employee) => `<option value="${employee.id}">${escapeHtml(employee.name)} · ${escapeHtml(employee.registration_code)}</option>`).join("");
    if (!employees.items.length) {
      table.innerHTML = '<tr><td colspan="4" class="table-empty">Cadastre um colaborador antes de registrar o ponto.</td></tr>';
      $("#clock-in-button").disabled = true;
      $("#clock-out-button").disabled = true;
      return;
    }
    await refreshAttendanceEvents();
  } catch (error) {
    table.innerHTML = `<tr><td colspan="4" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function refreshAttendanceEvents() {
  const employeeId = $("#attendance-employee").value;
  if (!employeeId) return;
  const [response, summaries] = await Promise.all([
    apiRequest(`/api/v1/time-events?from=${today()}&to=${today()}&employee_id=${employeeId}`),
    apiRequest(`/api/v1/attendance/days?from=${today()}&to=${today()}&employee_id=${employeeId}`),
  ]);
  const events = response.items;
  $("#attendance-table").innerHTML = events.length
    ? events.map((event) => `<tr><td>${new Date(event.occurred_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</td><td>${event.event_type === "ENTRADA" ? "Entrada" : "Saída"}</td><td>${event.source}</td><td><span class="status-tag">Válido</span></td></tr>`).join("")
    : '<tr><td colspan="4" class="table-empty">Nenhuma marcação hoje.</td></tr>';
  const lastEvent = events.at(-1);
  $("#clock-in-button").disabled = lastEvent?.event_type === "ENTRADA";
  $("#clock-out-button").disabled = !lastEvent || lastEvent.event_type === "SAIDA";
  const summary = summaries.items[0];
  $("#attendance-summary").textContent = summary
    ? `${formatMinutes(summary.worked_minutes)} trabalhadas · ${formatMinutes(summary.scheduled_minutes)} previstas`
    : "Nenhuma marcação";
}

function formatMinutes(minutes) {
  return `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`;
}

async function submitAttendance(eventType) {
  const errorElement = $("#attendance-error");
  errorElement.textContent = "";
  try {
    await apiRequest("/api/v1/time-events", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ event_type: eventType, occurred_at: new Date().toISOString(), source: "WEB", employee_id: $("#attendance-employee").value }) });
    showToast(eventType === "ENTRADA" ? "Entrada registrada." : "Saída registrada.");
    await refreshAttendanceEvents();
  } catch (error) { errorElement.textContent = error.message; }
}

async function loadSchedules() {
  try {
    const [schedules, employees] = await Promise.all([apiRequest("/api/v1/work-schedules"), apiRequest("/api/v1/employees")]);
    $("#schedule-select").innerHTML = schedules.items.map((schedule) => `<option value="${schedule.id}">${escapeHtml(schedule.name)} · ${schedule.start_time.slice(0, 5)}–${schedule.end_time.slice(0, 5)}</option>`).join("");
    $("#schedule-employee").innerHTML = employees.items.map((employee) => `<option value="${employee.id}">${escapeHtml(employee.name)}</option>`).join("");
    $("#schedules-table").innerHTML = schedules.items.length
      ? schedules.items.map((schedule) => `<tr><td><strong>${escapeHtml(schedule.name)}</strong></td><td>${schedule.start_time.slice(0, 5)}–${schedule.end_time.slice(0, 5)}</td><td>${schedule.tolerance_minutes} min</td><td><span class="status-tag">Ativa</span></td></tr>`).join("")
      : '<tr><td colspan="4" class="table-empty">Nenhuma jornada cadastrada.</td></tr>';
  } catch (error) { $("#schedule-error").textContent = error.message; }
}

async function handleScheduleSubmit(event) {
  event.preventDefault();
  const errorElement = $("#schedule-error");
  errorElement.textContent = "";
  try {
    await apiRequest("/api/v1/work-schedules", { method: "POST", body: JSON.stringify({ name: $("#schedule-name").value, start_time: `${$("#schedule-start").value}:00`, end_time: `${$("#schedule-end").value}:00`, tolerance_minutes: Number($("#schedule-tolerance").value), same_day_only: true }) });
    $("#schedule-form").reset();
    showToast("Jornada criada.");
    await loadSchedules();
  } catch (error) { errorElement.textContent = error.message; }
}

async function assignSchedule() {
  const errorElement = $("#schedule-error");
  errorElement.textContent = "";
  try {
    await apiRequest(`/api/v1/employees/${$("#schedule-employee").value}/schedules`, { method: "POST", body: JSON.stringify({ schedule_id: $("#schedule-select").value, starts_on: today() }) });
    showToast("Jornada vinculada ao colaborador.");
  } catch (error) { errorElement.textContent = error.message; }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}

function showEmployees() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $("#employees-nav").classList.add("active");
  $(".breadcrumb").innerHTML = 'JORNADAMS <span>/</span> COLABORADORES';
  $("#welcome-title").textContent = "Colaboradores";
  $("#attendance-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  $("#employees-panel").classList.remove("hidden");
  $("#employees-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadEmployees();
}

function showAttendance() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $("#attendance-nav").classList.add("active");
  $(".breadcrumb").innerHTML = 'JORNADAMS <span>/</span> REGISTRO DE PONTO';
  $("#welcome-title").textContent = "Registro de ponto";
  $("#employees-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  $("#attendance-panel").classList.remove("hidden");
  $("#attendance-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadAttendance();
}

function showSchedules() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $("#schedules-nav").classList.add("active");
  $(".breadcrumb").innerHTML = 'JORNADAMS <span>/</span> JORNADAS';
  $("#welcome-title").textContent = "Jornadas de trabalho";
  $("#employees-panel").classList.add("hidden");
  $("#attendance-panel").classList.add("hidden");
  $("#schedules-panel").classList.remove("hidden");
  $("#schedules-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadSchedules();
}

function showOverview() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $("#overview-nav").classList.add("active");
  $(".breadcrumb").innerHTML = 'JORNADAMS <span>/</span> VISÃO GERAL';
  renderUser();
  $("#employees-panel").classList.add("hidden");
  $("#attendance-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function handleEmployeeSubmit(event) {
  event.preventDefault();
  const errorElement = $("#employee-error");
  errorElement.textContent = "";
  try {
    await apiRequest("/api/v1/employees", { method: "POST", body: JSON.stringify({
      name: $("#employee-name").value,
      registration_code: $("#employee-registration").value,
      branch_id: $("#employee-branch").value,
    }) });
    $("#employee-form").reset();
    $("#employee-form").classList.add("hidden");
    showToast("Colaborador cadastrado.");
    await loadEmployees();
  } catch (error) { errorElement.textContent = error.message; }
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
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "Email ou senha inválidos.");
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
$("#overview-nav").addEventListener("click", showOverview);
$("#employees-nav").addEventListener("click", showEmployees);
$("#attendance-nav").addEventListener("click", showAttendance);
$("#schedules-nav").addEventListener("click", showSchedules);
$("#open-attendance-button").addEventListener("click", showAttendance);
$("#new-employee-button").addEventListener("click", () => $("#employee-form").classList.toggle("hidden"));
$("#cancel-employee-button").addEventListener("click", () => $("#employee-form").classList.add("hidden"));
$("#employee-form").addEventListener("submit", handleEmployeeSubmit);
$("#attendance-employee").addEventListener("change", refreshAttendanceEvents);
$("#clock-in-button").addEventListener("click", () => submitAttendance("ENTRADA"));
$("#clock-out-button").addEventListener("click", () => submitAttendance("SAIDA"));
$("#schedule-form").addEventListener("submit", handleScheduleSubmit);
$("#assign-schedule-button").addEventListener("click", assignSchedule);
renderDate();

loadUser().catch(() => { clearSession(); showLogin(); });
