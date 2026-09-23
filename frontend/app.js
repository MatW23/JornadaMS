const state = {
  user: null,
  isAdmin: false,
};

const $ = (selector) => document.querySelector(selector);

function clearSession() {
  state.user = null;
  state.isAdmin = false;
}

function isAdminUser() {
  return state.user?.roles?.some((role) => ["ADMIN", "HR"].includes(role)) || false;
}

function applyAppearance() {
  const theme = window.localStorage.getItem("jornada.theme") || "system";
  const accent = window.localStorage.getItem("jornada.accent") || "lime";
  const resolvedTheme = theme === "system"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : theme;
  document.body.dataset.theme = resolvedTheme;
  document.body.dataset.accent = accent;
  document.querySelectorAll("[data-theme-choice]").forEach((option) => {
    option.classList.toggle("selected", option.dataset.themeChoice === theme);
    option.setAttribute("aria-pressed", option.dataset.themeChoice === theme ? "true" : "false");
  });
  document.querySelectorAll("[data-accent-choice]").forEach((option) => {
    option.classList.toggle("selected", option.dataset.accentChoice === accent);
    option.setAttribute("aria-pressed", option.dataset.accentChoice === accent ? "true" : "false");
  });
}

function setAppearance(type, value) {
  window.localStorage.setItem(`jornada.${type}`, value);
  applyAppearance();
}

function openSettings() {
  applyAppearance();
  $("#settings-modal").classList.remove("hidden");
}

function closeSettings() {
  $("#settings-modal").classList.add("hidden");
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
  applyAppearance();
  state.isAdmin = isAdminUser();
  document.querySelectorAll(".admin-only").forEach((item) => item.classList.toggle("hidden", !state.isAdmin));
  document.querySelectorAll(".employee-only").forEach((item) => item.classList.toggle("hidden", state.isAdmin));
  $("#open-attendance-button").textContent = state.isAdmin ? "Ver registros" : "Registrar ponto";
  if (state.isAdmin) showOverview();
  else showEmployeeAttendance();
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
    if (state.isAdmin) {
      const employees = await apiRequest("/api/v1/employees");
      $("#attendance-employee-field").classList.remove("hidden");
      employeeSelect.innerHTML = employees.items.map((employee) => `<option value="${employee.id}">${escapeHtml(employee.name)} · ${escapeHtml(employee.registration_code)}</option>`).join("");
      if (!employees.items.length) {
        table.innerHTML = '<tr><td colspan="4" class="table-empty">Cadastre um colaborador antes de registrar o ponto.</td></tr>';
        $("#clock-in-button").disabled = true;
        $("#break-start-button").disabled = true;
        $("#break-end-button").disabled = true;
        $("#clock-out-button").disabled = true;
        return;
      }
    } else {
      $("#attendance-employee-field").classList.add("hidden");
    }
    await refreshAttendanceEvents();
  } catch (error) {
    table.innerHTML = `<tr><td colspan="4" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function refreshAttendanceEvents() {
  const employeeId = state.isAdmin ? $("#attendance-employee").value : null;
  if (state.isAdmin && !employeeId) return;
  const employeeFilter = employeeId ? `&employee_id=${encodeURIComponent(employeeId)}` : "";
  const [response, summaries] = await Promise.all([
    apiRequest(`/api/v1/time-events?from=${today()}&to=${today()}${employeeFilter}`),
    apiRequest(`/api/v1/attendance/days?from=${today()}&to=${today()}${employeeFilter}`),
  ]);
  const events = response.items;
  const eventLabels = {
    ENTRADA: "Entrada",
    INICIO_INTERVALO: "Início do intervalo",
    FIM_INTERVALO: "Fim do intervalo",
    SAIDA: "Saída",
  };
  $("#attendance-table").innerHTML = events.length
    ? events.map((event) => `<tr><td>${new Date(event.occurred_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</td><td>${eventLabels[event.event_type] || escapeHtml(event.event_type)}</td><td>${escapeHtml(event.source)}</td><td><span class="status-tag">Válido</span></td></tr>`).join("")
    : '<tr><td colspan="4" class="table-empty">Nenhuma marcação hoje.</td></tr>';
  const lastEvent = events.at(-1);
  const lastType = lastEvent?.event_type;
  $("#clock-in-button").disabled = lastType === "ENTRADA" || lastType === "INICIO_INTERVALO" || lastType === "FIM_INTERVALO";
  $("#break-start-button").disabled = lastType !== "ENTRADA";
  $("#break-end-button").disabled = lastType !== "INICIO_INTERVALO";
  $("#clock-out-button").disabled = !lastEvent || !["ENTRADA", "FIM_INTERVALO"].includes(lastType);
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
    const payload = { event_type: eventType, occurred_at: new Date().toISOString(), source: "WEB" };
    if (state.isAdmin) payload.employee_id = $("#attendance-employee").value;
    await apiRequest("/api/v1/time-events", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(payload) });
    const messages = {
      ENTRADA: "Entrada registrada.",
      INICIO_INTERVALO: "Intervalo iniciado.",
      FIM_INTERVALO: "Intervalo encerrado.",
      SAIDA: "Saída registrada.",
    };
    showToast(messages[eventType]);
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

function reportQuery() {
  const params = new URLSearchParams({ from: $("#report-from").value, to: $("#report-to").value });
  if ($("#report-employee").value) params.set("employee_id", $("#report-employee").value);
  if ($("#report-status").value) params.set("status", $("#report-status").value);
  return params;
}

async function loadReports() {
  const table = $("#reports-table");
  const errorElement = $("#report-error");
  errorElement.textContent = "";
  try {
    const [report, employees] = await Promise.all([
      apiRequest(`/api/v1/reports/attendance?${reportQuery().toString()}`),
      apiRequest("/api/v1/employees"),
    ]);
    const selectedEmployee = $("#report-employee").value;
    $("#report-employee").innerHTML = `<option value="">Todos</option>${employees.items.map((employee) => `<option value="${escapeHtml(employee.id)}">${escapeHtml(employee.name)} · ${escapeHtml(employee.registration_code)}</option>`).join("")}`;
    $("#report-employee").value = selectedEmployee;
    $("#report-worked").textContent = formatMinutes(report.totals.worked_minutes);
    $("#report-scheduled").textContent = formatMinutes(report.totals.scheduled_minutes);
    $("#report-balance").textContent = formatSignedMinutes(report.totals.balance_minutes);
    $("#report-delay").textContent = formatMinutes(report.totals.delay_minutes);
    table.innerHTML = report.items.length
      ? report.items.map((item) => `<tr><td>${escapeHtml(item.work_date)}</td><td><strong>${escapeHtml(item.employee_name)}</strong><small class="table-subtext">${escapeHtml(item.registration_code)}</small></td><td>${formatMinutes(item.scheduled_minutes)}</td><td>${formatMinutes(item.worked_minutes)}</td><td>${formatSignedMinutes(item.balance_minutes)}</td><td>${formatMinutes(item.delay_minutes)}</td><td><span class="status-tag">${formatStatus(item.status)}</span></td></tr>`).join("")
      : '<tr><td colspan="7" class="table-empty">Nenhum resumo encontrado no período.</td></tr>';
  } catch (error) {
    table.innerHTML = `<tr><td colspan="7" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
    errorElement.textContent = error.message;
  }
}

function formatSignedMinutes(minutes) {
  return `${minutes < 0 ? "−" : ""}${formatMinutes(Math.abs(minutes))}`;
}

function formatStatus(status) {
  return { COMPLETE: "Completo", IN_PROGRESS: "Em andamento", INCONSISTENT: "Inconsistente" }[status] || status;
}

function formatAdjustmentStatus(status) {
  return { PENDING: "Pendente", APPROVED: "Aprovado", REJECTED: "Rejeitado" }[status] || status;
}

function formatEventType(eventType) {
  return { ENTRADA: "Entrada", INICIO_INTERVALO: "Início do intervalo", FIM_INTERVALO: "Fim do intervalo", SAIDA: "Saída" }[eventType] || eventType;
}

async function loadAdjustments() {
  const table = $("#adjustments-table");
  const errorElement = $("#adjustment-error");
  errorElement.textContent = "";
  try {
    const requests = await apiRequest("/api/v1/adjustment-requests");
    if (!state.isAdmin) {
      const events = await apiRequest(`/api/v1/time-events?from=${today()}&to=${today()}`);
      $("#adjustment-target").innerHTML = `<option value="">Nova marcação</option>${events.items.filter((event) => event.status === "VALID").map((event) => `<option value="${escapeHtml(event.id)}">${escapeHtml(formatEventType(event.event_type))} · ${new Date(event.occurred_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</option>`).join("")}`;
    }
    table.innerHTML = requests.items.length
      ? requests.items.map((item) => `<tr><td>${escapeHtml(item.work_date)}</td><td><strong>${escapeHtml(item.employee_name)}</strong></td><td>${escapeHtml(formatEventType(item.proposed_event_type))}<small class="table-subtext">${new Date(item.proposed_occurred_at).toLocaleString("pt-BR")}</small></td><td class="adjustment-reason-cell">${escapeHtml(item.reason)}</td><td><span class="status-tag">${escapeHtml(formatAdjustmentStatus(item.status))}</span></td><td>${state.isAdmin && item.status === "PENDING" ? `<button class="button button-small button-secondary" data-adjustment-action="approve" data-adjustment-id="${escapeHtml(item.id)}">Aprovar</button> <button class="button button-small button-danger" data-adjustment-action="reject" data-adjustment-id="${escapeHtml(item.id)}">Rejeitar</button>` : "—"}</td></tr>`).join("")
      : '<tr><td colspan="6" class="table-empty">Nenhuma solicitação encontrada.</td></tr>';
  } catch (error) {
    table.innerHTML = `<tr><td colspan="6" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
    errorElement.textContent = error.message;
  }
}

async function submitAdjustment(event) {
  event.preventDefault();
  const errorElement = $("#adjustment-error");
  errorElement.textContent = "";
  try {
    const localDate = new Date($("#adjustment-occurred-at").value);
    const payload = {
      event_type: $("#adjustment-event-type").value,
      occurred_at: localDate.toISOString(),
      reason: $("#adjustment-reason").value,
    };
    if ($("#adjustment-target").value) payload.target_event_id = $("#adjustment-target").value;
    await apiRequest("/api/v1/adjustment-requests", { method: "POST", body: JSON.stringify(payload) });
    $("#adjustment-form").reset();
    showToast("Solicitação enviada para análise.");
    await loadAdjustments();
  } catch (error) { errorElement.textContent = error.message; }
}

async function decideAdjustment(requestId, action) {
  const errorElement = $("#adjustment-error");
  errorElement.textContent = "";
  try {
    await apiRequest(`/api/v1/adjustment-requests/${encodeURIComponent(requestId)}/${action}`, { method: "POST", body: JSON.stringify({}) });
    showToast(action === "approve" ? "Ajuste aprovado." : "Ajuste rejeitado.");
    await loadAdjustments();
  } catch (error) { errorElement.textContent = error.message; }
}

async function exportReport() {
  const errorElement = $("#report-error");
  errorElement.textContent = "";
  try {
    const response = await fetch(`/api/v1/reports/attendance/export?${reportQuery().toString()}`, { credentials: "same-origin" });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error?.message || "Não foi possível exportar o relatório.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "jornada-relatorio.csv";
    link.click();
    URL.revokeObjectURL(url);
    showToast("Relatório exportado.");
  } catch (error) { errorElement.textContent = error.message; }
}

async function handleScheduleSubmit(event) {
  event.preventDefault();
  const errorElement = $("#schedule-error");
  errorElement.textContent = "";
  try {
    const breakStart = $("#schedule-break-start").value;
    const breakEnd = $("#schedule-break-end").value;
    await apiRequest("/api/v1/work-schedules", { method: "POST", body: JSON.stringify({ name: $("#schedule-name").value, start_time: `${$("#schedule-start").value}:00`, break_start: breakStart ? `${breakStart}:00` : null, break_end: breakEnd ? `${breakEnd}:00` : null, end_time: `${$("#schedule-end").value}:00`, tolerance_minutes: Number($("#schedule-tolerance").value), same_day_only: true }) });
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
  $("#reports-panel").classList.add("hidden");
  $("#adjustments-panel").classList.add("hidden");
  $("#overview-view").classList.add("hidden");
  $("#employees-panel").classList.remove("hidden");
  $("#employees-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadEmployees();
}

function showAttendance() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $(state.isAdmin ? "#attendance-nav" : "#employee-attendance-nav").classList.add("active");
  $(".breadcrumb").innerHTML = state.isAdmin
    ? 'JORNADAMS <span>/</span> REGISTROS'
    : 'JORNADAMS <span>/</span> MEU PONTO';
  $("#welcome-title").textContent = state.isAdmin ? "Registros de ponto" : "Meu ponto";
  $("#attendance-title").textContent = state.isAdmin ? "Registros de ponto" : "Meu registro de ponto";
  $("#employees-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  $("#reports-panel").classList.add("hidden");
  $("#adjustments-panel").classList.add("hidden");
  $("#overview-view").classList.add("hidden");
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
  $("#reports-panel").classList.add("hidden");
  $("#adjustments-panel").classList.add("hidden");
  $("#overview-view").classList.add("hidden");
  $("#schedules-panel").classList.remove("hidden");
  $("#schedules-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadSchedules();
}

function showReports() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $("#reports-nav").classList.add("active");
  $(".breadcrumb").innerHTML = 'JORNADAMS <span>/</span> RELATÓRIOS';
  $("#welcome-title").textContent = "Relatórios de jornada";
  $("#employees-panel").classList.add("hidden");
  $("#attendance-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  $("#adjustments-panel").classList.add("hidden");
  $("#overview-view").classList.add("hidden");
  $("#reports-panel").classList.remove("hidden");
  $("#reports-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadReports();
}

function showAdjustments() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $(state.isAdmin ? "#adjustments-nav" : "#employee-adjustments-nav").classList.add("active");
  $(".breadcrumb").innerHTML = state.isAdmin
    ? 'JORNADAMS <span>/</span> AJUSTES'
    : 'JORNADAMS <span>/</span> SOLICITAÇÕES';
  $("#welcome-title").textContent = state.isAdmin ? "Ajustes de jornada" : "Minhas solicitações";
  $("#adjustments-title").textContent = state.isAdmin ? "Solicitações de ajuste" : "Minhas solicitações de ajuste";
  $("#employees-panel").classList.add("hidden");
  $("#attendance-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  $("#reports-panel").classList.add("hidden");
  $("#overview-view").classList.add("hidden");
  $("#adjustments-panel").classList.remove("hidden");
  $("#adjustments-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  loadAdjustments();
}

function showOverview() {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  $("#overview-nav").classList.add("active");
  $(".breadcrumb").innerHTML = 'JORNADAMS <span>/</span> VISÃO GERAL';
  renderUser();
  $("#employees-panel").classList.add("hidden");
  $("#attendance-panel").classList.add("hidden");
  $("#schedules-panel").classList.add("hidden");
  $("#reports-panel").classList.add("hidden");
  $("#adjustments-panel").classList.add("hidden");
  $("#overview-view").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showEmployeeAttendance() {
  showAttendance();
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
  const isoDate = today();
  const date = now.toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
  $("#current-date").textContent = date;
  $("#summary-date").textContent = now.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  if (!$("#report-from").value) $("#report-from").value = isoDate;
  if (!$("#report-to").value) $("#report-to").value = isoDate;
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
$("#settings-button").addEventListener("click", openSettings);
$("#mobile-settings-button").addEventListener("click", openSettings);
$("#close-settings-button").addEventListener("click", closeSettings);
$("#close-settings-footer").addEventListener("click", closeSettings);
$("#settings-modal").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeSettings();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("#settings-modal").classList.contains("hidden")) closeSettings();
});
document.querySelectorAll("[data-theme-choice]").forEach((option) => {
  option.addEventListener("click", () => setAppearance("theme", option.dataset.themeChoice));
});
document.querySelectorAll("[data-accent-choice]").forEach((option) => {
  option.addEventListener("click", () => setAppearance("accent", option.dataset.accentChoice));
});
$("#overview-nav").addEventListener("click", showOverview);
$("#employees-nav").addEventListener("click", showEmployees);
$("#attendance-nav").addEventListener("click", showAttendance);
$("#employee-attendance-nav").addEventListener("click", showEmployeeAttendance);
$("#schedules-nav").addEventListener("click", showSchedules);
$("#reports-nav").addEventListener("click", showReports);
$("#adjustments-nav").addEventListener("click", showAdjustments);
$("#employee-adjustments-nav").addEventListener("click", showAdjustments);
$("#open-attendance-button").addEventListener("click", showAttendance);
$("#new-employee-button").addEventListener("click", () => $("#employee-form").classList.toggle("hidden"));
$("#cancel-employee-button").addEventListener("click", () => $("#employee-form").classList.add("hidden"));
$("#employee-form").addEventListener("submit", handleEmployeeSubmit);
$("#attendance-employee").addEventListener("change", refreshAttendanceEvents);
$("#clock-in-button").addEventListener("click", () => submitAttendance("ENTRADA"));
$("#break-start-button").addEventListener("click", () => submitAttendance("INICIO_INTERVALO"));
$("#break-end-button").addEventListener("click", () => submitAttendance("FIM_INTERVALO"));
$("#clock-out-button").addEventListener("click", () => submitAttendance("SAIDA"));
$("#schedule-form").addEventListener("submit", handleScheduleSubmit);
$("#assign-schedule-button").addEventListener("click", assignSchedule);
$("#report-form").addEventListener("submit", (event) => { event.preventDefault(); loadReports(); });
$("#export-report-button").addEventListener("click", exportReport);
$("#adjustment-form").addEventListener("submit", submitAdjustment);
$("#adjustments-table").addEventListener("click", (event) => {
  const button = event.target.closest("[data-adjustment-action]");
  if (button) decideAdjustment(button.dataset.adjustmentId, button.dataset.adjustmentAction);
});
renderDate();
applyAppearance();

loadUser().catch(() => { clearSession(); showLogin(); });
