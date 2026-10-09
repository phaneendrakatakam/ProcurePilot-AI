(() => {
  "use strict";

  const TOKEN_KEY = "procurepilot_access_token";
  const API = "/api/v1";

  const state = {
    user: null,
    departments: [],
    budgets: [],
    vendors: [],
    rfqs: [],
    rfqSuppliers: [],
    users: [],
    roles: [],
    audit: [],
    purchaseRequests: [],
    quotations: [],
    pendingQuotations: [],
    selectedRequestId: null,
    editingRequestId: null,
    comparisonRfqId: null,
    selectionRfqId: null,
    purchaseOrderId: null,
    goodsReceiptId: null,
    invoiceId: null,
    matchingInvoiceId: null,
    approvalId: null,
    approvalRequestId: null,
    currentView: "home",
  };

  const roleNames = {
    EMPLOYEE: "Employee",
    MANAGER: "Manager",
    PROCUREMENT_ANALYST: "Procurement Analyst",
    PROCUREMENT_HEAD: "Procurement Head",
    AP_ANALYST: "AP Analyst",
    FINANCE_MANAGER: "Finance Manager",
    GOODS_RECEIVER: "Goods Receiver",
    ADMINISTRATOR: "Administrator",
  };

  const icons = {
    home: "\u2302", users: "\u25ce", departments: "\u25c7", budgets: "\u25a5", vendors: "\u25eb", audit: "\u25c9",
    requests: "\u25a4", approvals: "\u2713", sourcing: "\u2318", invoices: "\u25a7", receipts: "\u25a3", analytics: "\u2301",
    settings: "\u2699", exceptions: "\u25b3", payment: "\u25cd",
  };

  const roleNavigation = {
    ADMINISTRATOR: [
      ["home", "Dashboard", "home"], ["users", "Users & Roles", "users"], ["departments", "Departments", "departments"],
      ["budgets", "Budgets", "budgets"], ["vendors", "Vendors", "vendors"], ["audit", "Audit Trail", "audit"],
    ],
    EMPLOYEE: [["home", "My Procurement", "home"], ["my-requests", "My Requests", "requests"], ["new-request", "New Request", "requests"]],
    MANAGER: [["home", "Approval Workspace", "home"], ["approvals", "Pending Approvals", "approvals"], ["team", "Team Activity", "analytics"]],
    PROCUREMENT_ANALYST: [["home", "Procurement Workspace", "home"], ["requests", "Requests", "requests"], ["rfqs", "RFQs", "sourcing"], ["quotes", "Quotations", "sourcing"], ["purchase-orders", "Purchase Orders", "sourcing"], ["deliveries", "Expected Deliveries", "receipts"], ["receipts", "Goods Receipts", "receipts"], ["invoices", "Invoices", "invoices"], ["vendors", "Vendors", "vendors"], ["exceptions", "Exceptions", "exceptions"]],
    PROCUREMENT_HEAD: [["home", "Command Center", "home"], ["approvals", "High-Value Approvals", "approvals"], ["vendors", "Vendors", "vendors"], ["purchase-orders", "Purchase Orders", "sourcing"], ["deliveries", "Expected Deliveries", "receipts"], ["receipts", "Goods Receipts", "receipts"], ["invoices", "Invoices", "invoices"], ["analytics", "Analytics", "analytics"], ["audit", "Audit", "audit"]],
    AP_ANALYST: [["home", "AP Workspace", "home"], ["invoices", "Invoices", "invoices"], ["matching", "3-Way Matching", "invoices"], ["exceptions", "Exceptions", "exceptions"], ["payment", "Payment Readiness", "payment"]],
    FINANCE_MANAGER: [["home", "Finance Control Center", "home"], ["approvals", "Finance Approvals", "approvals"], ["invoices", "Invoices", "invoices"], ["budgets", "Budget Exceptions", "budgets"], ["payment", "Payment Readiness", "payment"], ["analytics", "Analytics", "analytics"]],
    GOODS_RECEIVER: [["home", "Receiving Workspace", "home"], ["deliveries", "Expected Deliveries", "receipts"], ["receipts", "Goods Receipts", "receipts"]],
  };

  const els = {
    loading: document.querySelector("#app-loading"), shell: document.querySelector("#app-shell"), content: document.querySelector("#content"),
    nav: document.querySelector("#sidebar-nav"), workspace: document.querySelector("#workspace-name"), profileName: document.querySelector("#profile-name"),
    profileRole: document.querySelector("#profile-role"), profileInitials: document.querySelector("#profile-initials"), logout: document.querySelector("#logout-button"),
    mobileMenu: document.querySelector("#mobile-menu-button"), sidebar: document.querySelector("#sidebar"), search: document.querySelector("#global-search"),
    toastRegion: document.querySelector("#toast-region"), modalRoot: document.querySelector("#modal-root"), notificationButton: document.querySelector(".notification-button"), notificationDot: document.querySelector(".notification-dot"),
  };

  function token() { return sessionStorage.getItem(TOKEN_KEY); }
  function hasPermission(code) { return state.user?.permissions?.includes(code); }
  function canViewReceiving() { return hasPermission("goods_receipts.manage") || hasPermission("sourcing.manage"); }
  function canManageReceiving() { return hasPermission("goods_receipts.manage"); }
  function canViewInvoices() { return hasPermission("invoices.review") || hasPermission("finance.review") || hasPermission("sourcing.manage"); }
  function canManageInvoices() { return hasPermission("invoices.review"); }
  function canFinalizePayment() { return hasPermission("finance.review"); }
  function hasRole(code) { return state.user?.roles?.some(role => (typeof role === "string" ? role : role?.code) === code); }
  function primaryRole() { return state.user?.roles?.[0] || "EMPLOYEE"; }
  function escapeHTML(value = "") {
    return String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  }
  function formatDate(value) {
    if (!value) return "\u2014";
    return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  }
  function money(value, currency = "INR") {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: currency || "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
  }
  function moneyOrPending(value, currency = "INR") {
    return value == null ? "Not estimated" : money(value, currency);
  }
  function initials(name = "") { return name.split(/\s+/).filter(Boolean).slice(0,2).map(v => v[0]).join("").toUpperCase() || "PP"; }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token()}`);
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    let response;
    try {
      response = await fetch(`${API}${path}`, { ...options, headers });
    } catch (err) {
      if (navigator.onLine === false) throw new Error("You appear to be offline. Check your connection and try again.");
      throw new Error("ProcurePilot could not reach the server. Check the connection and try again.");
    }
    if (response.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY);
      window.location.replace("/login");
      throw new Error("Your session expired.");
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data?.detail;
      let message;
      if (Array.isArray(detail)) {
        message = detail.map(item => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") return item.msg || item.message || JSON.stringify(item);
          return String(item);
        }).join("; ");
      } else if (detail && typeof detail === "object") {
        message = detail.msg || detail.message || JSON.stringify(detail);
      } else {
        message = detail || `Request failed (${response.status})`;
      }
      throw new Error(String(message));
    }
    return data;
  }

  function toast(message, tone = "success") {
    const node = document.createElement("div");
    node.className = `toast toast--${tone}`;
    node.textContent = message;
    els.toastRegion.append(node);
    window.setTimeout(() => node.remove(), 3500);
  }

  function modal({ title, body, submitLabel = "Save", onSubmit }) {
    els.modalRoot.innerHTML = `
      <div class="modal-backdrop" data-close-modal>
        <section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <header><div><span class="eyebrow">PROCUREPILOT</span><h2 id="modal-title">${escapeHTML(title)}</h2></div><button class="icon-button" data-close-modal aria-label="Close">\u00d7</button></header>
          <form id="modal-form"><div class="modal-body">${body}</div><div id="modal-error" class="form-error" hidden></div><footer><button type="button" class="button button--ghost" data-close-modal>Cancel</button><button class="button button--primary" type="submit">${escapeHTML(submitLabel)}</button></footer></form>
        </section>
      </div>`;
    const close = () => { els.modalRoot.innerHTML = ""; };
    els.modalRoot.querySelectorAll("[data-close-modal]").forEach(el => el.addEventListener("click", e => { if (e.target === el || el.tagName === "BUTTON") close(); }));
    const form = els.modalRoot.querySelector("#modal-form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const error = els.modalRoot.querySelector("#modal-error");
      const submit = form.querySelector("button[type=submit]");
      error.hidden = true; submit.disabled = true;
      try { await onSubmit(new FormData(form)); close(); }
      catch (err) { error.textContent = err.message; error.hidden = false; submit.disabled = false; }
    });
  }

  async function refreshNotificationIndicator() {
    if (!els.notificationDot) return;
    try {
      const unread = await api("/notifications?unread_only=true");
      els.notificationDot.hidden = unread.length === 0;
      els.notificationDot.title = unread.length ? `${unread.length} unread notification${unread.length === 1 ? "" : "s"}` : "No unread notifications";
    } catch (_) {
      els.notificationDot.hidden = true;
    }
  }

  async function openNotifications() {
    try {
      const notifications = await api("/notifications");
      const rows = notifications.length ? notifications.map(item => `
        <article class="notification-item ${item.read_at ? "is-read" : ""}">
          <div><span class="eyebrow">${escapeHTML(item.notification_type.replaceAll("_", " "))}</span><h3>${escapeHTML(item.subject)}</h3><p>${escapeHTML(item.body)}</p><small>${formatDate(item.created_at)} · ${escapeHTML(item.status)}</small></div>
          ${item.read_at ? "" : `<button class="button button--small button--ghost" data-mark-notification="${item.id}">Mark read</button>`}
        </article>`).join("") : `<div class="empty-inline">No notifications yet.</div>`;
      els.modalRoot.innerHTML = `<div class="modal-backdrop" data-close-notifications><section class="modal" role="dialog" aria-modal="true" aria-labelledby="notifications-title"><header><div><span class="eyebrow">NOTIFICATIONS</span><h2 id="notifications-title">Procurement notifications</h2></div><button class="icon-button" data-close-notifications aria-label="Close">×</button></header><div class="modal-body notification-list">${rows}</div></section></div>`;
      const close = () => { els.modalRoot.innerHTML = ""; };
      els.modalRoot.querySelectorAll("[data-close-notifications]").forEach(el => el.addEventListener("click", e => { if (e.target === el || e.target.tagName === "BUTTON") close(); }));
      els.modalRoot.querySelectorAll("[data-mark-notification]").forEach(button => button.addEventListener("click", async () => {
        await api(`/notifications/${button.dataset.markNotification}/read`, { method: "POST" });
        button.closest(".notification-item")?.remove();
        await refreshNotificationIndicator();
      }));
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function roleLabel() { return state.user.roles.map(r => roleNames[r] || r).join(" \u00b7 "); }

  function routeStateFromLocation() {
    const url = new URL(window.location.href);
    const view = url.searchParams.get("view") || "home";
    const requestId = url.searchParams.get("request");
    const editId = url.searchParams.get("edit");
    const rfqId = url.searchParams.get("rfq");

    if (view === "request-detail" && requestId) state.selectedRequestId = requestId;
    if (view === "new-request" && editId) state.editingRequestId = editId;
    if (view === "quotation-comparison" && rfqId) state.comparisonRfqId = rfqId;
    if (view === "supplier-selection" && rfqId) state.selectionRfqId = rfqId;
    if (view === "purchase-order-detail") state.purchaseOrderId = url.searchParams.get("po");
    if (view === "goods-receipt-detail") state.goodsReceiptId = url.searchParams.get("receipt");
    if (view === "invoice-detail") state.invoiceId = url.searchParams.get("invoice");
    if (view === "matching-detail") state.matchingInvoiceId = url.searchParams.get("invoice");
    if (view === "approval-detail") { state.approvalId = url.searchParams.get("approval"); state.approvalRequestId = requestId; }
    return view;
  }

  function syncRoute(view, { replace = false } = {}) {
    const url = new URL(window.location.href);
    url.pathname = "/app";
    url.search = "";

    if (view && view !== "home") url.searchParams.set("view", view);
    if (view === "request-detail" && state.selectedRequestId) url.searchParams.set("request", state.selectedRequestId);
    if (view === "new-request" && state.editingRequestId) url.searchParams.set("edit", state.editingRequestId);
    if (view === "quotation-comparison" && state.comparisonRfqId) url.searchParams.set("rfq", state.comparisonRfqId);
    if (view === "supplier-selection" && state.selectionRfqId) url.searchParams.set("rfq", state.selectionRfqId);
    if (view === "approval-detail" && state.approvalId) url.searchParams.set("approval", state.approvalId);
    if (view === "approval-detail" && state.approvalRequestId) url.searchParams.set("request", state.approvalRequestId);
    if (view === "purchase-order-detail" && state.purchaseOrderId) url.searchParams.set("po", state.purchaseOrderId);
    if (view === "goods-receipt-detail" && state.goodsReceiptId) url.searchParams.set("receipt", state.goodsReceiptId);
    if (view === "invoice-detail" && state.invoiceId) url.searchParams.set("invoice", state.invoiceId);
    if (view === "matching-detail" && state.matchingInvoiceId) url.searchParams.set("invoice", state.matchingInvoiceId);

    const method = replace ? "replaceState" : "pushState";
    window.history[method]({
      view,
      requestId: view === "request-detail" ? state.selectedRequestId : null,
      editId: view === "new-request" ? state.editingRequestId : null,
      rfqId: view === "quotation-comparison" ? state.comparisonRfqId : view === "supplier-selection" ? state.selectionRfqId : null,
    }, "", url);
  }

  function viewAllowedForCurrentUser(view) {
    let nav = roleNavigation[primaryRole()] || roleNavigation.EMPLOYEE;
    if (state.user?.roles?.includes("ADMINISTRATOR")) nav = roleNavigation.ADMINISTRATOR;
    nav = nav.filter(([key]) => key !== "audit" || hasPermission("users.read"));
    const visibleViews = new Set(nav.map(([key]) => key));
    if (view === "home") return true;
    if (view === "quotation-comparison") return Boolean(state.comparisonRfqId) && hasPermission("sourcing.manage");
    if (view === "supplier-selection") return Boolean(state.selectionRfqId) && hasPermission("sourcing.manage");
    if (view === "purchase-order-detail") return Boolean(state.purchaseOrderId) && hasPermission("sourcing.manage");
    if (["deliveries", "receipts", "goods-receipt-detail"].includes(view)) return canViewReceiving() && (view !== "goods-receipt-detail" || Boolean(state.goodsReceiptId));
    if (["invoices", "invoice-detail"].includes(view)) return canViewInvoices() && (view !== "invoice-detail" || Boolean(state.invoiceId));
    if (["matching", "matching-detail"].includes(view)) return canViewInvoices() && (view !== "matching-detail" || Boolean(state.matchingInvoiceId));
    if (view === "approval-detail") return Boolean(state.approvalId) && hasPermission("approvals.decide");
    if (view === "request-detail") {
      return Boolean(state.selectedRequestId) && (
        hasPermission("purchase_requests.read_own") ||
        hasPermission("purchase_requests.read_department") ||
        hasPermission("purchase_requests.read_all")
      );
    }
    return visibleViews.has(view);
  }

  function buildNavigation() {
    let nav = roleNavigation[primaryRole()] || roleNavigation.EMPLOYEE;
    if (state.user.roles.includes("ADMINISTRATOR")) nav = roleNavigation.ADMINISTRATOR;
    nav = nav.filter(([key]) => key !== "audit" || hasPermission("users.read"));
    const activeView = state.currentView === "request-detail"
      ? (primaryRole() === "EMPLOYEE" ? "my-requests" : "requests")
      : state.currentView === "quotation-comparison" || state.currentView === "supplier-selection" ? "quotes" : state.currentView === "purchase-order-detail" ? "purchase-orders" : state.currentView === "invoice-detail" ? "invoices" : state.currentView === "matching-detail" ? "matching" : state.currentView;
    els.nav.innerHTML = nav.map(([key, label, icon]) => `
      <button type="button" class="sidebar-link ${key === activeView ? "is-active" : ""}" data-view="${key}">
        <span class="nav-icon">${icons[icon] || "\u2022"}</span><span>${escapeHTML(label)}</span>
      </button>`).join("");
    els.nav.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.view)));
  }

  function setUserChrome() {
    els.profileName.textContent = state.user.full_name;
    els.profileRole.textContent = roleLabel();
    els.profileInitials.textContent = initials(state.user.full_name);
    els.workspace.textContent = roleNames[primaryRole()] || "ProcurePilot Workspace";
  }

  async function navigate(view, { syncUrl = true, replaceUrl = false } = {}) {
    if (view === "new-request" && state.currentView !== "request-detail" && !state.editingRequestId) state.editingRequestId = null;
    state.currentView = view;
    if (syncUrl) syncRoute(view, { replace: replaceUrl });
    buildNavigation();
    els.sidebar.classList.remove("is-open");
    els.content.innerHTML = `<div class="skeleton-page"><div></div><div></div><div></div></div>`;
    try {
      if (view === "home") return renderHome();
      if (view === "users") return renderUsers();
      if (view === "departments") return renderDepartments();
      if (view === "budgets") return renderBudgets();
      if (view === "vendors") return renderVendors();
      if (view === "rfqs") return renderRFQs();
      if (view === "quotes") return renderQuotations();
      if (view === "quotation-comparison") return renderQuotationComparison(state.comparisonRfqId);
      if (view === "supplier-selection") return renderSupplierSelection(state.selectionRfqId);
      if (view === "purchase-orders") return renderPurchaseOrders();
      if (view === "purchase-order-detail") return renderPurchaseOrderDetail(state.purchaseOrderId);
      if (view === "deliveries") return renderExpectedDeliveries();
      if (view === "receipts") return renderGoodsReceipts();
      if (view === "goods-receipt-detail") return renderGoodsReceiptDetail(state.goodsReceiptId);
      if (view === "invoices") return renderInvoices();
      if (view === "invoice-detail") return renderInvoiceDetail(state.invoiceId);
      if (view === "matching") return renderThreeWayMatching();
      if (view === "matching-detail") return renderThreeWayMatchingDetail(state.matchingInvoiceId);
      if (view === "payment") return renderPaymentFinalization();
      if (view === "approvals") return renderApprovals();
      if (view === "approval-detail") return renderApprovalDetail(state.approvalId);
      if (view === "audit") return renderAudit();
      if (view === "my-requests") return renderMyRequests();
      if (view === "new-request") return renderNewRequest();
      if (view === "request-detail") return renderRequestDetail(state.selectedRequestId);
      if (view === "requests" && (hasPermission("purchase_requests.read_all") || hasPermission("purchase_requests.read_department") || hasPermission("purchase_requests.read_own"))) return renderProcurementRequests();
      return renderFutureWorkspace(view);
    } catch (err) {
      els.content.innerHTML = emptyState("Unable to load this workspace", err.message, "Try again", () => navigate(view));
    }
  }

  function pageHeader(kicker, title, copy, action = "") {
    return `<div class="page-header"><div><span class="eyebrow">${escapeHTML(kicker)}</span><h1>${escapeHTML(title)}</h1><p>${escapeHTML(copy)}</p></div>${action}</div>`;
  }

  function statCard(label, value, foot, tone = "green", icon = "\u25cf") {
    return `<article class="metric-card metric-card--${tone}"><div class="metric-icon">${icon}</div><div><span>${escapeHTML(label)}</span><strong>${escapeHTML(String(value))}</strong><small>${escapeHTML(foot)}</small></div></article>`;
  }

  const requestCategories = [
    ["IT_HARDWARE", "IT Hardware"],
    ["IT_SOFTWARE", "IT Software"],
    ["OFFICE_SUPPLIES", "Office Supplies"],
    ["PROFESSIONAL_SERVICES", "Professional Services"],
    ["FACILITIES", "Facilities"],
    ["MARKETING", "Marketing"],
    ["OPERATIONS", "Operations"],
    ["OTHER", "Other"],
  ];

  function requestStatusMeta(status) {
    const map = {
      DRAFT: ["Draft", "muted"],
      NEEDS_CLARIFICATION: ["Needs clarification", "amber"],
      SUBMITTED: ["Submitted", "blue"],
      BUDGET_EXCEPTION: ["Budget exception", "red"],
      POLICY_EXCEPTION: ["Policy exception", "red"],
      READY_FOR_SOURCING: ["Ready for sourcing", "green"],
      SOURCING: ["Sourcing in progress", "blue"],
    };
    return map[status] || [humanizeAction(status || "UNKNOWN"), "muted"];
  }

  function checkMeta(status) {
    const map = {
      PASS: ["Pass", "green", "\u2713"],
      FAIL: ["Fail", "red", "!"],
      NOT_CHECKED: ["Not checked", "muted", "\u2014"],
      NOT_CONFIGURED: ["Not configured", "amber", "!"],
    };
    return map[status] || [humanizeAction(status || "NOT_CHECKED"), "muted", "\u2014"];
  }

  function requestStatusPill(status) {
    const [label, tone] = requestStatusMeta(status);
    return `<span class="request-status request-status--${tone}">${escapeHTML(label)}</span>`;
  }

  function checkPill(status) {
    const [label, tone, icon] = checkMeta(status);
    return `<span class="check-pill check-pill--${tone}"><b>${icon}</b>${escapeHTML(label)}</span>`;
  }

  function requestRequiredDate(value) {
    if (!value) return "Not set";
    return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
  }

  async function loadPurchaseRequests() {
    state.purchaseRequests = await api("/purchase-requests");
    return state.purchaseRequests;
  }

  function requestTableRows(requests) {
    return requests.map(request => `<tr>
      <td><button class="request-link" data-request-id="${request.id}"><strong>${escapeHTML(request.request_number)}</strong><small>${escapeHTML(request.title)}</small></button></td>
      <td>${requestStatusPill(request.status)}</td>
      <td>${escapeHTML(request.category || "\u2014")}</td>
      <td>${moneyOrPending(request.estimated_total ?? request.estimated_budget, request.currency)}</td>
      <td>${request.line_count}</td>
      <td>${request.open_clarifications ? `<span class="clarification-count">${request.open_clarifications}</span>` : "0"}</td>
      <td>${formatDate(request.updated_at)}</td>
      <td><button class="button button--ghost button--small" data-request-id="${request.id}">View</button></td>
    </tr>`).join("");
  }

  function wireRequestLinks() {
    els.content.querySelectorAll("[data-request-id]").forEach(el => el.addEventListener("click", () => {
      state.selectedRequestId = el.dataset.requestId;
      navigate("request-detail");
    }));
  }

  async function renderEmployeeHome() {
    const requests = await loadPurchaseRequests();
    const clarifications = requests.reduce((sum, request) => sum + Number(request.open_clarifications || 0), 0);
    const ready = requests.filter(request => request.status === "READY_FOR_SOURCING").length;
    const drafts = requests.filter(request => request.status === "DRAFT").length;
    const active = requests.length;
    const recent = requests.slice(0, 5);

    els.content.innerHTML = `${pageHeader("EMPLOYEE", "My Procurement", "Create, submit, and track purchase requests from one place.", `<button class="button button--primary" data-nav="new-request">+ New request</button>`)}
      <section class="metric-grid">
        ${statCard("My requests", active, active ? "Live request records" : "No requests yet", "green", "\u25a4")}
        ${statCard("Clarifications", clarifications, clarifications ? "Need your attention" : "Nothing waiting", clarifications ? "amber" : "blue", "\u25f7")}
        ${statCard("Ready for sourcing", ready, "Validated requests", "green", "\u2713")}
        ${statCard("Drafts", drafts, drafts ? "Continue editing" : "No saved drafts", "violet", "\u270e")}
      </section>
      <section class="dashboard-grid request-home-grid">
        <article class="panel panel--span-2">
          <div class="panel-heading"><div><span class="eyebrow">RECENT REQUESTS</span><h2>Your purchase activity</h2><p>Open a request to review validation, budget, policy, clarifications, and history.</p></div><button class="text-link" data-nav="my-requests">View all \u2192</button></div>
          ${recent.length ? `<div class="request-list">${recent.map(request => {
            const [statusLabel, statusTone] = requestStatusMeta(request.status);
            return `<button class="request-list-item" data-request-id="${request.id}">
              <span class="request-list-icon">\u25a4</span>
              <span class="request-list-copy"><strong>${escapeHTML(request.title)}</strong><small>${escapeHTML(request.request_number)} \u00b7 ${request.line_count} line item${request.line_count === 1 ? "" : "s"}</small></span>
              <span class="request-list-value">${moneyOrPending(request.estimated_total ?? request.estimated_budget, request.currency)}<small>${request.open_clarifications ? `${request.open_clarifications} clarification${request.open_clarifications === 1 ? "" : "s"}` : "Updated " + relativeTime(request.updated_at)}</small></span>
              <span class="request-status request-status--${statusTone}">${escapeHTML(statusLabel)}</span>
            </button>`;
          }).join("")}</div>` : `<div class="request-empty"><span>\u25a4</span><h3>Your first purchase request starts here.</h3><p>Create a draft, add line items, and submit it for deterministic budget and policy validation.</p><button class="button button--primary" data-nav="new-request">Create request</button></div>`}
        </article>
        <article class="panel procurement-journey-card">
          <div class="panel-heading"><div><span class="eyebrow">REQUEST JOURNEY</span><h2>From need to sourcing-ready</h2></div></div>
          <div class="request-journey-vertical">
            <div><b>1</b><span><strong>Create</strong><small>Capture the business need and line items.</small></span></div>
            <div><b>2</b><span><strong>Clarify</strong><small>Missing required information stops the request safely.</small></span></div>
            <div><b>3</b><span><strong>Validate</strong><small>Budget and procurement policy checks run deterministically.</small></span></div>
            <div><b>4</b><span><strong>Ready for sourcing</strong><small>Clean requests can move to procurement.</small></span></div>
          </div>
        </article>
      </section>`;
    wireCommonActions();
    wireRequestLinks();
  }

  async function renderMyRequests() {
    const requests = await loadPurchaseRequests();
    const clarificationCount = requests.reduce((sum, request) => sum + Number(request.open_clarifications || 0), 0);
    const ready = requests.filter(request => request.status === "READY_FOR_SOURCING").length;
    els.content.innerHTML = `${pageHeader("PURCHASE REQUESTS", "My Requests", "Track every request you have created, from draft through validation.", `<button class="button button--primary" data-nav="new-request">+ New request</button>`)}
      <section class="metric-grid">
        ${statCard("Total requests", requests.length, "Owned by your account", "green", "\u25a4")}
        ${statCard("Open clarifications", clarificationCount, clarificationCount ? "Action required" : "Nothing waiting", clarificationCount ? "amber" : "blue", "?")}
        ${statCard("Ready for sourcing", ready, "Budget and policy passed", "green", "\u2713")}
        ${statCard("Estimated value", money(requests.reduce((sum, r) => sum + Number(r.estimated_total || 0), 0)), "Across your requests", "violet", "\u20b9")}
      </section>
      ${tablePanel("Purchase request register", requests.length ? `${requests.length} request${requests.length === 1 ? "" : "s"} \u00b7 newest first` : "No requests yet", `<table class="request-table"><thead><tr><th>Request</th><th>Status</th><th>Category</th><th>Value</th><th>Lines</th><th>Clarifications</th><th>Updated</th><th></th></tr></thead><tbody>${requestTableRows(requests) || emptyTableRow(8, "No purchase requests found")}</tbody></table>`)} `;
    wireCommonActions();
    wireRequestLinks();
  }

  async function renderProcurementRequests() {
    if (!hasPermission("sourcing.manage")) {
      els.content.innerHTML = emptyState("Sourcing workspace unavailable", "Your account does not have permission to access the sourcing queue.", "Go to home", () => navigate("home"));
      return;
    }
    if (navigator.onLine === false) {
      els.content.innerHTML = emptyState("You're offline", "The sourcing queue needs a connection to load live procurement work.", "Try again", () => navigate("requests"));
      return;
    }

    let slowNotice;
    const slowTimer = window.setTimeout(() => {
      slowNotice = document.createElement("div");
      slowNotice.className = "inline-state inline-state--slow";
      slowNotice.innerHTML = "<span>\u25cc</span><div><strong>Still loading the sourcing queue</strong><small>The connection is taking longer than usual. Your request data is still safe.</small></div>";
      els.content.prepend(slowNotice);
    }, 900);

    try {
      const requests = await api("/purchase-requests/sourcing/queue");
      window.clearTimeout(slowTimer);
      if (slowNotice) slowNotice.remove();
      state.purchaseRequests = requests;
      drawSourcingWorkspace(requests);
    } catch (err) {
      window.clearTimeout(slowTimer);
      if (slowNotice) slowNotice.remove();
      const offline = navigator.onLine === false || /network|fetch|connect/i.test(err.message);
      els.content.innerHTML = emptyState(
        offline ? "Connection unavailable" : "Sourcing queue could not be loaded",
        offline ? "Check your connection and try again. No sourcing work was changed." : err.message,
        "Try again",
        () => navigate("requests")
      );
    }
  }

  function drawSourcingWorkspace(requests) {
    const searchId = "sourcing-search";
    const filterId = "sourcing-status-filter";
    els.content.innerHTML = `${pageHeader("PROCUREMENT", "Sourcing Workspace", "Turn validated purchase requests into supplier sourcing work. No supplier is selected automatically.")}
      <section class="metric-grid">
        ${statCard("Ready for sourcing", requests.filter(r => r.status === "READY_FOR_SOURCING").length, "Validated and waiting to be sourced", "green", "\u2713")}
        ${statCard("In sourcing", requests.filter(r => r.status === "SOURCING").length, "Sourcing work already started", "blue", "\u2318")}
        ${statCard("Pricing pending", requests.filter(r => r.estimated_total == null).length, "Supplier quotes may be required", "amber", "\u20b9")}
        ${statCard("Open queue", requests.length, "Live sourcing workload", "violet", "\u25a4")}
      </section>
      <section class="panel sourcing-queue-tools">
        <div><span class="eyebrow">SOURCING QUEUE</span><strong>Find procurement work</strong><small>Search by request number, title, or category.</small></div>
        <label class="sourcing-search"><span>\u2315</span><input id="${searchId}" type="search" placeholder="Search sourcing queue\u2026" autocomplete="off" aria-label="Search sourcing queue"></label>
        <select id="${filterId}" aria-label="Filter sourcing status"><option value="all">All active work</option><option value="ready">Ready for sourcing</option><option value="sourcing">In sourcing</option></select>
      </section>
      <section class="panel table-panel sourcing-queue-panel">
        <div class="panel-heading"><div><span class="eyebrow">LIVE PROCUREMENT WORK</span><h2>Requests ready to source</h2><p>Review the validated requirement before RFQ creation.</p></div></div>
        <div class="table-wrap"><table class="request-table"><thead><tr><th>Request</th><th>Status</th><th>Category</th><th>Required by</th><th>Estimate</th><th>Validation</th><th></th></tr></thead><tbody id="sourcing-queue-rows"></tbody></table></div>
      </section>`;

    const rowsEl = els.content.querySelector("#sourcing-queue-rows");
    const draw = () => {
      const q = els.content.querySelector(`#${searchId}`).value.trim().toLowerCase();
      const filter = els.content.querySelector(`#${filterId}`).value;
      const filtered = requests.filter(r => {
        const matchesSearch = !q || [r.request_number, r.title, r.category].filter(Boolean).join(" ").toLowerCase().includes(q);
        const matchesFilter = filter === "all" || (filter === "ready" ? r.status === "READY_FOR_SOURCING" : r.status === "SOURCING");
        return matchesSearch && matchesFilter;
      });
      if (!filtered.length) {
        const searched = Boolean(q) || filter !== "all";
        rowsEl.innerHTML = `<tr><td colspan="7" class="empty-cell"><strong>${searched ? "No sourcing requests match your filters" : "No sourcing work is waiting"}</strong><br><small>${searched ? "Try a different request number, title, category, or status." : "Validated purchase requests will appear here when they are ready for supplier sourcing."}</small></td></tr>`;
        return;
      }
      rowsEl.innerHTML = filtered.map(r => `<tr>
        <td><button class="request-link" data-request-id="${r.id}"><strong>${escapeHTML(r.request_number)}</strong><small>${escapeHTML(r.title)}</small></button></td>
        <td>${requestStatusPill(r.status)}</td>
        <td>${escapeHTML(r.category || "\u2014")}</td>
        <td>${escapeHTML(requestRequiredDate(r.required_date))}</td>
        <td>${moneyOrPending(r.estimated_total ?? r.estimated_budget, r.currency)}</td>
        <td><div class="sourcing-validation">${checkPill(r.budget_check_status)} ${checkPill(r.policy_check_status)}</div></td>
        <td><div class="sourcing-actions">${r.status === "READY_FOR_SOURCING" ? `<button class="button button--primary button--small" data-start-sourcing="${r.id}">Start sourcing</button>` : `<span class="text-success">Sourcing active</span>`}<button class="button button--ghost button--small" data-request-id="${r.id}">View</button></div></td>
      </tr>`).join("");
      wireRequestLinks();
      rowsEl.querySelectorAll("[data-start-sourcing]").forEach(button => button.addEventListener("click", async () => {
        const id = button.dataset.startSourcing;
        button.disabled = true;
        button.textContent = "Starting\u2026";
        try {
          await api(`/purchase-requests/${id}/start-sourcing`, { method: "POST" });
          toast("Sourcing started. The request is now in the sourcing queue.");
          await renderProcurementRequests();
        } catch (err) {
          toast(err.message, "error");
          button.disabled = false;
          button.textContent = "Start sourcing";
        }
      }));
    };
    els.content.querySelector(`#${searchId}`).addEventListener("input", draw);
    els.content.querySelector(`#${filterId}`).addEventListener("change", draw);
    draw();
  }

  function requestLineItemRow(index, item = {}) {
    const specNotes = item.specifications?.notes || "";
    return `<div class="line-item-editor" data-line-item>
      <div class="line-item-number">${index + 1}</div>
      <label>Item name<input name="item_name" value="${escapeHTML(item.name || "")}" placeholder="Enter item or service name"></label>
      <label>Quantity<input name="item_quantity" type="number" min="0.01" step="0.01" value="${escapeHTML(item.quantity || "")}" placeholder="e.g. 10"></label>
      <label>Unit price <span>Optional</span><input name="item_price" type="number" min="0" step="0.01" value="${escapeHTML(item.unit_price ?? "")}" placeholder="Optional until quoted"></label>
      <label class="line-item-description">Description<input name="item_description" value="${escapeHTML(item.description || "")}" placeholder="Describe the item or service"></label>
      <label class="line-item-specs">Specifications / notes<input name="item_specs" value="${escapeHTML(specNotes)}" placeholder="Add specifications, scope, or key requirements"></label>
      <div class="line-item-total"><span>Line total</span><strong data-line-total>${item.unit_price == null ? "Not estimated" : money(Number(item.quantity || 0) * Number(item.unit_price || 0))}</strong></div>
      <button class="icon-button line-remove" type="button" data-remove-line title="Remove line item" aria-label="Remove line item">\u00d7</button>
    </div>`;
  }

  async function renderNewRequest() {
    let existing = null;
    if (state.editingRequestId) {
      existing = await api(`/purchase-requests/${state.editingRequestId}`);
    }
    const categories = requestCategories.map(([value, label]) => `<option value="${value}" ${existing?.category === value ? "selected" : ""}>${escapeHTML(label)}</option>`).join("");
    const items = existing?.items?.length ? existing.items : [{}];

    els.content.innerHTML = `${pageHeader("PURCHASE REQUEST", existing ? `Edit ${existing.request_number}` : "New Request", existing ? "Update the request information, then save and re-submit when ready." : "Capture the business need now. Missing information can remain blank in a draft and will be identified when you submit.", `<button class="button button--ghost" data-nav="my-requests">\u2190 My requests</button>`)}
      <form id="purchase-request-form" class="request-builder">
        <section class="request-builder-main">
          <article class="panel request-form-section">
            <div class="panel-heading"><div><span class="eyebrow">REQUEST DETAILS</span><h2>What do you need?</h2><p>Fields marked \u201crequired for submission\u201d are checked when the request is submitted, not while saving a draft.</p></div></div>
            <div class="request-form-grid">
              <label class="field-span-2">Request title <span>Required for draft</span><input name="title" required minlength="3" maxlength="200" value="${escapeHTML(existing?.title || "")}" placeholder="Enter a clear request title"></label>
              <label>Category <span>Required for submission</span><select name="category"><option value="">Select category</option>${categories}</select></label>
              <label>Required date <span>Required for submission</span><input name="required_date" type="date" value="${escapeHTML(existing?.required_date || "")}"></label>
              <label class="field-span-2">Business justification <span>Required for submission</span><textarea name="justification" rows="4" placeholder="Explain why the purchase is needed and who it supports.">${escapeHTML(existing?.justification || "")}</textarea></label>
              <label>Currency <span>Optional</span><input name="currency" maxlength="3" value="${escapeHTML(existing?.currency || "")}" placeholder="e.g. INR"></label>
              <label>Estimated budget <span>Optional</span><input name="estimated_budget" type="number" min="0" step="0.01" value="${escapeHTML(existing?.estimated_budget ?? "")}" placeholder="Optional budget target"></label>
              <label class="field-span-2">Additional context <span>Optional</span><textarea name="source_text" rows="3" placeholder="Describe the need in your own words or add context for procurement.">${escapeHTML(existing?.source_text || "")}</textarea></label>
            </div>
          </article>

          <article class="panel request-form-section">
            <div class="panel-heading"><div><span class="eyebrow">LINE ITEMS</span><h2>Goods or services</h2><p>Unit price is optional when supplier pricing is not yet known.</p></div><button class="button button--ghost button--small" type="button" id="add-line-item">+ Add line</button></div>
            <div id="line-item-editors" class="line-item-editors">${items.map((item, index) => requestLineItemRow(index, item)).join("")}</div>
          </article>
        </section>

        <aside class="request-builder-aside">
          <article class="panel request-summary-card">
            <span class="eyebrow">DRAFT SUMMARY</span>
            <h2>Request value</h2>
            <strong id="request-estimated-total">${moneyOrPending(existing?.estimated_total, existing?.currency || "INR")}</strong>
            <div class="request-summary-list">
              <span><b>Estimated budget</b><strong id="request-estimated-budget">${moneyOrPending(existing?.estimated_budget, existing?.currency || "INR")}</strong></span>
              <span><b>Line items</b><strong id="request-line-count">${existing?.items?.length || 0}</strong></span>
              <span><b>Budget check</b>${checkPill(existing?.budget_check_status || "NOT_CHECKED")}</span>
              <span><b>Policy check</b>${checkPill(existing?.policy_check_status || "NOT_CHECKED")}</span>
            </div>
            <div class="request-draft-note"><span>i</span><p>Saving creates or updates a draft. Budget and policy controls run only when you submit the request.</p></div>
            <div id="request-form-error" class="form-error" hidden></div>
            <button class="button button--primary button--wide" type="submit">${existing ? "Save changes" : "Save draft"}</button>
          </article>
        </aside>
      </form>`;
    wireCommonActions();
    wireRequestForm(existing);
  }

  function wireRequestForm(existing) {
    const form = els.content.querySelector("#purchase-request-form");
    const editors = els.content.querySelector("#line-item-editors");
    const addButton = els.content.querySelector("#add-line-item");
    const totalEl = els.content.querySelector("#request-estimated-total");
    const countEl = els.content.querySelector("#request-line-count");
    const errorEl = els.content.querySelector("#request-form-error");

    function renumber() {
      [...editors.querySelectorAll("[data-line-item]")].forEach((row, index) => {
        row.querySelector(".line-item-number").textContent = index + 1;
      });
    }

    function recalc() {
      let total = 0;
      let count = 0;
      let hasUnknownPrice = false;
      [...editors.querySelectorAll("[data-line-item]")].forEach(row => {
        const quantity = Number(row.querySelector("[name=item_quantity]").value || 0);
        const priceRaw = row.querySelector("[name=item_price]").value;
        const price = Number(priceRaw || 0);
        const line = quantity * price;
        if (priceRaw === "") {
          hasUnknownPrice = true;
          row.querySelector("[data-line-total]").textContent = "Not estimated";
        } else {
          row.querySelector("[data-line-total]").textContent = money(line, (form.elements.currency.value || "INR").toUpperCase());
          total += line;
        }
        if (row.querySelector("[name=item_name]").value.trim()) count += 1;
      });
      totalEl.textContent = hasUnknownPrice ? "Not estimated" : money(total, (form.elements.currency.value || "INR").toUpperCase());
      const budget = Number(form.elements.estimated_budget.value || 0);
      const budgetEl = els.content.querySelector("#request-estimated-budget");
      if (budgetEl) budgetEl.textContent = form.elements.estimated_budget.value === "" ? "Not provided" : money(budget, (form.elements.currency.value || "INR").toUpperCase());
      countEl.textContent = count;
    }

    function wireRows() {
      editors.querySelectorAll("[data-line-item]").forEach(row => {
        if (row.dataset.wired === "true") return;
        row.dataset.wired = "true";
        row.querySelectorAll("input").forEach(input => input.addEventListener("input", recalc));
        row.querySelector("[data-remove-line]").addEventListener("click", () => {
          row.remove();
          renumber();
          recalc();
        });
      });
    }

    addButton.addEventListener("click", () => {
      const wrapper = document.createElement("div");
      wrapper.innerHTML = requestLineItemRow(editors.querySelectorAll("[data-line-item]").length);
      const row = wrapper.firstElementChild;
      editors.append(row);
      wireRows();
      recalc();
    });
    form.elements.currency.addEventListener("input", recalc);
    form.elements.estimated_budget.addEventListener("input", recalc);
    wireRows();
    recalc();

    form.addEventListener("submit", async event => {
      event.preventDefault();
      errorEl.hidden = true;
      const submitButton = form.querySelector("button[type=submit]");
      submitButton.disabled = true;

      try {
        const items = [];
        for (const row of editors.querySelectorAll("[data-line-item]")) {
          const name = row.querySelector("[name=item_name]").value.trim();
          const quantityRaw = row.querySelector("[name=item_quantity]").value;
          const priceRaw = row.querySelector("[name=item_price]").value;
          const description = row.querySelector("[name=item_description]").value.trim();
          const specs = row.querySelector("[name=item_specs]").value.trim();

          const anyValue = name || quantityRaw || priceRaw || description || specs;
          if (!anyValue) continue;
          if (!name || !quantityRaw) throw new Error("Complete item name and quantity for each line item, or remove the incomplete line.");
          const quantity = Number(quantityRaw);
          const unit_price = priceRaw === "" ? null : Number(priceRaw);
          if (!(quantity > 0) || (unit_price !== null && unit_price < 0)) throw new Error("Quantity must be greater than zero and unit price cannot be negative.");

          items.push({
            name,
            description: description || null,
            quantity,
            unit_price,
            specifications: specs ? { notes: specs } : null,
          });
        }

        const payload = {
          title: form.elements.title.value.trim(),
          category: form.elements.category.value || null,
          justification: form.elements.justification.value.trim() || null,
          required_date: form.elements.required_date.value || null,
          currency: form.elements.currency.value.trim() ? form.elements.currency.value.trim().toUpperCase() : null,
          estimated_budget: form.elements.estimated_budget.value === "" ? null : Number(form.elements.estimated_budget.value),
          source_text: form.elements.source_text.value.trim() || null,
          items,
        };

        const data = existing
          ? await api(`/purchase-requests/${existing.id}`, { method: "PATCH", body: JSON.stringify(payload) })
          : await api("/purchase-requests", { method: "POST", body: JSON.stringify(payload) });

        state.editingRequestId = null;
        state.selectedRequestId = data.id;
        toast(existing ? "Draft updated." : "Draft saved.");
        await navigate("request-detail");
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
        submitButton.disabled = false;
      }
    });
  }

  function requestProgress(lifecycle) {
    const steps = lifecycle.steps || [];
    return `<div class="lifecycle-header"><strong>End-to-end procurement lifecycle</strong><small>Request approval: ${escapeHTML(lifecycle.request_status)} · Overall: ${escapeHTML(lifecycle.overall_status)}</small></div>
      <div class="request-progress request-progress--lifecycle">${steps.map((step, i) => `<div class="request-progress-step ${step.state === "DONE" ? "is-done" : ""} ${step.state === "ACTIVE" ? "is-active" : ""}">
      <span>${step.state === "DONE" ? "✓" : i + 1}</span><strong>${escapeHTML(step.label)}</strong><small>${escapeHTML(step.detail)}</small>
    </div>`).join("")}</div>`;
  }

  async function renderRequestDetail(requestId) {
    if (!requestId) return navigate(primaryRole() === "EMPLOYEE" ? "my-requests" : "requests");
    const [detail, lifecycle] = await Promise.all([api(`/purchase-requests/${requestId}`), api(`/purchase-requests/${requestId}/lifecycle`)]);
    state.selectedRequestId = detail.id;
    const isOwner = detail.requester_id === state.user.id;
    const editable = isOwner && hasPermission("purchase_requests.create") && ["DRAFT", "NEEDS_CLARIFICATION", "BUDGET_EXCEPTION", "POLICY_EXCEPTION"].includes(detail.status);
    const canSubmit = editable;
    const events = [...detail.events].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const openClarifications = detail.clarifications.filter(task => task.status === "OPEN");

    const itemRows = detail.items.map((item, index) => `<tr><td>${index + 1}</td><td><strong>${escapeHTML(item.name)}</strong><small class="table-subline">${escapeHTML(item.description || "")}</small></td><td>${escapeHTML(String(item.quantity))}</td><td>${moneyOrPending(item.unit_price, detail.currency)}</td><td>${moneyOrPending(item.line_total, detail.currency)}</td></tr>`).join("");

    const headerActions = `<div class="header-actions">
      <button class="button button--ghost" data-nav="${primaryRole() === "EMPLOYEE" ? "my-requests" : "requests"}">\u2190 Back</button>
      ${editable ? `<button class="button button--ghost" data-action="edit-request">Edit request</button>` : ""}
      ${canSubmit ? `<button class="button button--primary" data-action="submit-request">${detail.status === "DRAFT" ? "Submit request" : "Re-submit request"}</button>` : ""}
      ${detail.status === "READY_FOR_SOURCING" && hasPermission("sourcing.manage") ? `<button class="button button--primary" data-action="start-sourcing">Start sourcing</button>` : ""}
    </div>`;

    els.content.innerHTML = `${pageHeader("PURCHASE REQUEST", detail.request_number, detail.title, headerActions)}
      <section class="request-detail-hero panel">
        <div class="request-detail-title">
          ${requestStatusPill(detail.status)}
          <p>${escapeHTML(detail.justification || "No business justification provided yet.")}</p>
        </div>
        ${requestProgress(lifecycle)}
      </section>

      <section class="metric-grid">
        ${statCard("Estimated total", moneyOrPending(detail.estimated_total, detail.currency), `${detail.line_count} line item${detail.line_count === 1 ? "" : "s"}`, "green", "\u20b9")}${statCard("Estimated budget", moneyOrPending(detail.estimated_budget, detail.currency), "Optional target", "violet", "\u20b9")}
        ${statCard("Required date", requestRequiredDate(detail.required_date), detail.category || "Category not set", "blue", "\u25f7")}
        ${statCard("Budget check", checkMeta(detail.budget_check_status)[0], detail.budget_check_status === "PASS" ? "Budget available" : "See validation evidence", detail.budget_check_status === "PASS" ? "green" : detail.budget_check_status === "FAIL" ? "red" : "amber", "\u20b9")}
        ${statCard("Policy check", checkMeta(detail.policy_check_status)[0], detail.policy_check_status === "PASS" ? "Deterministic checks passed" : "See validation evidence", detail.policy_check_status === "PASS" ? "green" : detail.policy_check_status === "FAIL" ? "red" : "amber", "\u2713")}
      </section>

      ${openClarifications.length ? `<section class="clarification-banner">
        <div><span class="clarification-banner-icon">?</span><div><strong>${openClarifications.length} clarification${openClarifications.length === 1 ? "" : "s"} required</strong><p>ProcurePilot will not advance this request until the required information is added.</p></div></div>
        ${editable ? `<button class="button button--ghost" data-action="edit-request">Edit request</button>` : ""}
      </section>` : ""}

      <section class="request-detail-grid">
        <article class="panel request-lines-panel">
          <div class="panel-heading"><div><span class="eyebrow">LINE ITEMS</span><h2>Requested goods & services</h2></div></div>
          <div class="table-wrap"><table><thead><tr><th>#</th><th>Item</th><th>Quantity</th><th>Unit price</th><th>Total</th></tr></thead><tbody>${itemRows || emptyTableRow(5, "No line items")}</tbody></table></div>
        </article>

        <article class="panel validation-panel">
          <div class="panel-heading"><div><span class="eyebrow">VALIDATION & EVIDENCE</span><h2>Check outcomes</h2><p>The evidence behind this request's budget and policy statuses.</p></div></div>
          <div class="validation-card validation-card--${checkMeta(detail.budget_check_status)[1]}">
            <div><span>\u20b9</span><strong>Budget validation</strong>${checkPill(detail.budget_check_status)}</div>
            <p>${escapeHTML(detail.budget_check_status === "NOT_CHECKED"
              ? (detail.estimated_budget == null && detail.estimated_total == null
                ? "No budget or commercial estimate was supplied. Budget validation is pending until an amount is available."
                : "Budget validation has not run yet.")
              : (detail.budget_check_message || "Budget validation result is unavailable."))}</p>
          </div>
          <div class="validation-card validation-card--${checkMeta(detail.policy_check_status)[1]}">
            <div><span>\u2713</span><strong>Policy validation</strong>${checkPill(detail.policy_check_status)}</div>
            <p>${escapeHTML(detail.policy_check_status === "NOT_CHECKED"
              ? "Policy validation has not run yet."
              : (detail.policy_check_message || "Policy validation result is unavailable."))}</p>
          </div>
        </article>

        ${detail.clarifications.length ? `<article class="panel clarification-panel">
          <div class="panel-heading"><div><span class="eyebrow">CLARIFICATIONS</span><h2>Information checks</h2><p>Targeted questions are generated when required request information is missing.</p></div></div>
          <div class="clarification-list">${detail.clarifications.map(task => `<div class="clarification-item ${task.status === "OPEN" ? "is-open" : ""}">
            <span>${task.status === "OPEN" ? "?" : "\u2713"}</span>
            <div><strong>${escapeHTML(task.question)}</strong><small>${escapeHTML(humanizeAction(task.field_name))} \u00b7 ${escapeHTML(humanizeAction(task.status))}</small>${task.answer ? `<p>${escapeHTML(task.answer)}</p>` : ""}</div>
          </div>`).join("")}</div>
        </article>` : ""}

        <article class="panel request-events-panel ${detail.clarifications.length ? "" : "panel--span-2"}">
          <div class="panel-heading"><div><span class="eyebrow">REQUEST HISTORY</span><h2>Traceable timeline</h2><p>Human and deterministic system actions recorded for this request.</p></div></div>
          <div class="request-event-list">${events.map(event => `<div class="request-event">
            <span class="audit-actor audit-actor--${event.actor_type.toLowerCase()}">${actorIcon(event.actor_type)}</span>
            <div><strong>${escapeHTML(humanizeAction(event.event_type))}</strong><small>${escapeHTML(event.actor_type)}${event.from_status || event.to_status ? ` \u00b7 ${escapeHTML(event.from_status || "\u2014")} \u2192 ${escapeHTML(event.to_status || "\u2014")}` : ""}</small></div>
            <time>${formatDate(event.created_at)}</time>
          </div>`).join("")}</div>
        </article>
      </section>`;

    wireCommonActions();
    els.content.querySelectorAll("[data-action=edit-request]").forEach(button => button.addEventListener("click", () => {
      state.editingRequestId = detail.id;
      navigate("new-request");
    }));
    els.content.querySelector("[data-action=start-sourcing]")?.addEventListener("click", async buttonEvent => {
      const button = buttonEvent.currentTarget;
      button.disabled = true;
      button.textContent = "Starting\u2026";
      try {
        const updated = await api(`/purchase-requests/${detail.id}/start-sourcing`, { method: "POST" });
        state.selectedRequestId = updated.id;
        toast("Sourcing started for this request.");
        await renderRequestDetail(updated.id);
      } catch (err) {
        toast(err.message, "error");
        button.disabled = false;
        button.textContent = "Start sourcing";
      }
    });
    els.content.querySelector("[data-action=submit-request]")?.addEventListener("click", async buttonEvent => {
      const button = buttonEvent.currentTarget;
      button.disabled = true;
      button.textContent = "Running checks\u2026";
      try {
        const updated = await api(`/purchase-requests/${detail.id}/submit`, { method: "POST" });
        state.selectedRequestId = updated.id;
        if (updated.status === "READY_FOR_SOURCING") toast("Request passed budget and policy checks.");
        else if (updated.status === "NEEDS_CLARIFICATION") toast("Request needs clarification before it can continue.", "error");
        else toast(`Request moved to ${humanizeAction(updated.status)}.`, updated.status.includes("EXCEPTION") ? "error" : "success");
        await renderRequestDetail(updated.id);
      } catch (err) {
        toast(err.message, "error");
        button.disabled = false;
        button.textContent = detail.status === "DRAFT" ? "Submit request" : "Re-submit request";
      }
    });
  }

  async function renderApprovals() {
    if (!hasPermission("approvals.decide")) {
      els.content.innerHTML = emptyState("Approval workspace unavailable", "Your account is not authorized to make approval decisions.", "Go to home", () => navigate("home"));
      return;
    }
    if (navigator.onLine === false) {
      els.content.innerHTML = emptyState("You're offline", "Pending approvals need a connection to load the latest decision state.", "Try again", () => renderApprovals());
      return;
    }
    let slow; const timer = setTimeout(() => { slow=document.createElement("div"); slow.className="inline-state inline-state--slow"; slow.innerHTML='<span>◌</span><div><strong>Still loading approvals</strong><small>The connection is taking longer than usual. Your approval decisions remain unchanged.</small></div>'; els.content.prepend(slow); },900);
    try {
      const rows = await api("/purchase-request-approvals/pending"); clearTimeout(timer); if(slow) slow.remove();
      const title = primaryRole()==="PROCUREMENT_HEAD" ? "High-Value Approvals" : primaryRole()==="FINANCE_MANAGER" ? "Finance Approvals" : "Pending Approvals";
      els.content.innerHTML = `${pageHeader("APPROVAL WORKSPACE", title, "Review assigned procurement decisions with the request, supplier, and approval context in one place.", `<button class="button button--ghost" data-refresh-approvals>Refresh</button>`)}${rows.length ? `<section class="approval-list">${rows.map(approvalCardHTML).join("")}</section>` : `<section class="panel future-panel"><div class="future-icon">✓</div><h2>No approvals need your decision</h2><p>Your assigned approval queue is clear. New decisions will appear here when requests reach your approval step.</p><button class="button button--ghost" data-refresh-approvals>Refresh queue</button></section>`}`;
      els.content.querySelectorAll("[data-open-approval]").forEach(b=>b.addEventListener("click",()=>{state.approvalId=b.dataset.openApproval; state.approvalRequestId=b.dataset.request; navigate("approval-detail");}));
      els.content.querySelectorAll("[data-refresh-approvals]").forEach(b=>b.addEventListener("click",()=>renderApprovals()));
    } catch(err) { clearTimeout(timer); if(slow) slow.remove(); els.content.innerHTML=emptyState("Approval queue could not be loaded", err.message, "Try again", ()=>renderApprovals()); }
  }

  function approvalCardHTML(a) {
    return `<article class="approval-card"><div class="approval-card__main"><div class="approval-card__top"><span class="code-chip">${escapeHTML(a.request_number)}</span><span class="status status--amber">Awaiting your decision</span><span class="status status--muted">Step ${a.approval_sequence} of ${a.total_approval_steps}</span></div><h3>${escapeHTML(a.title)}</h3><div class="approval-card__meta"><span>${escapeHTML(a.requester_name)}</span><span>${escapeHTML(a.department_name||"Department not specified")}</span><span>${escapeHTML(a.category||"Uncategorized")}</span><span class="approval-card__value">${a.estimated_total==null?"Not estimated":money(a.estimated_total,a.currency)}</span></div><div class="approval-chain"><span class="approval-step approval-step--done">Supplier selected</span><b>→</b><span class="approval-step approval-step--current">${escapeHTML(humanizeAction(a.approver_role))}</span>${a.total_approval_steps>1?`<span class="approval-step">Approval chain continues</span>`:""}</div></div><div class="approval-card__action"><button class="button button--primary" data-open-approval="${a.approval_id}" data-request="${a.purchase_request_id}">Review decision</button></div></article>`;
  }

  async function renderApprovalDetail(approvalId) {
    if (!hasPermission("approvals.decide")) { els.content.innerHTML=emptyState("Approval unavailable","Your account is not authorized to make approval decisions.","Go to home",()=>navigate("home")); return; }
    if (!approvalId) return navigate("approvals");
    if (navigator.onLine===false) { els.content.innerHTML=emptyState("You're offline","Approval details require a connection to load current workflow state.","Try again",()=>renderApprovalDetail(approvalId)); return; }
    let slow; const timer=setTimeout(()=>{slow=document.createElement("div");slow.className="inline-state inline-state--slow";slow.innerHTML='<span>◌</span><div><strong>Still loading approval details</strong><small>No decision has been submitted.</small></div>';els.content.prepend(slow)},900);
    try {
      const a = await api(`/purchase-request-approvals/${approvalId}`);
      const [request, pendingApprovals] = await Promise.all([
        api(`/purchase-requests/${a.purchase_request_id}`),
        api("/purchase-request-approvals/pending").catch(() => []),
      ]);
      const assignment = (pendingApprovals || []).find(item => item.approval_id === approvalId);
      clearTimeout(timer); if(slow) slow.remove();
      renderApprovalDetailView(a, request, assignment);
    } catch(err) { clearTimeout(timer); if(slow) slow.remove(); els.content.innerHTML=emptyState("Approval details could not be loaded",err.message,"Back to approvals",()=>navigate("approvals")); }
  }

  function approvalSpecRows(specifications) {
    if (!specifications || typeof specifications !== "object") return "";
    return Object.entries(specifications).map(([key, value]) => {
      const rendered = Array.isArray(value) ? value.join(", ") : typeof value === "object" && value !== null ? JSON.stringify(value) : String(value);
      return `<div class="approval-request-spec"><span>${escapeHTML(humanizeAction(key))}</span><strong>${escapeHTML(rendered)}</strong></div>`;
    }).join("");
  }

  function renderApprovalDetailView(a, request, assignment = null) {
    const canDecide=a.approval_status==="PENDING" && a.request_status==="PENDING_APPROVAL";
    const events = [...(request.events || [])].sort((x,y) => new Date(y.created_at) - new Date(x.created_at));
    const supplierEvent = events.find(event => event.event_type === "SUPPLIER_SELECTED");
    const supplierDetails = supplierEvent?.details || {};
    const requesterName = assignment?.requester_name || "Requester";
    const departmentName = assignment?.department_name || (request.category ? humanizeAction(request.category) : "Department not specified");
    const items = request.items || [];
    const itemRows = items.map((item,index) => `<div class="approval-request-item">
      <div class="approval-request-item__index">${index + 1}</div>
      <div class="approval-request-item__body">
        <strong>${escapeHTML(item.name)}</strong>
        ${item.description ? `<p>${escapeHTML(item.description)}</p>` : ""}
        ${approvalSpecRows(item.specifications) ? `<div class="approval-request-specs">${approvalSpecRows(item.specifications)}</div>` : ""}
      </div>
      <div class="approval-request-item__commercial"><span>Qty</span><strong>${escapeHTML(String(item.quantity))}</strong><span>Unit price</span><strong>${moneyOrPending(item.unit_price, request.currency)}</strong><span>Line total</span><strong>${moneyOrPending(item.line_total, request.currency)}</strong></div>
    </div>`).join("");
    const selectedSupplier = supplierDetails.supplier_name || supplierDetails.supplier_code;
    const selectedQuoteEvent = events.find(event => event.event_type === "QUOTATION_RECEIVED" && String(event.details?.quotation_id) === String(supplierDetails.quotation_id));
    const selectedQuoteTotal = supplierDetails.quotation_total ?? selectedQuoteEvent?.details?.total_amount;
    const approvedVariance = selectedQuoteTotal == null || request.estimated_total == null ? null : Number(selectedQuoteTotal) - Number(request.estimated_total);
    const headerActions = `<button class="button button--ghost" data-back-approvals>← Pending approvals</button>`;
    els.content.innerHTML=`${pageHeader("APPROVAL REVIEW",a.request_number,request.title,headerActions)}
      <div class="approval-review-layout">
        <main class="approval-review-main">
          <section class="panel approval-request-overview">
            <div class="approval-request-overview__top"><div><span class="eyebrow">PURCHASE REQUEST</span><h2>${escapeHTML(request.title)}</h2><p>${escapeHTML(request.justification || "No business justification provided.")}</p></div><div class="approval-review-badges"><span class="status status--amber">${escapeHTML(humanizeAction(a.approval_status))}</span><span class="status status--muted">Step ${a.approval_sequence} of 3 · ${escapeHTML(humanizeAction(a.approver_role))}</span></div></div>
            <div class="approval-request-meta-grid">
              <div><span>Purchase request</span><strong>${escapeHTML(request.request_number)}</strong></div>
              <div><span>Requested by</span><strong>${escapeHTML(requesterName)}</strong></div>
              <div><span>Department</span><strong>${escapeHTML(departmentName)}</strong></div>
              <div><span>Category</span><strong>${escapeHTML(request.category ? humanizeAction(request.category) : "Not specified")}</strong></div>
              <div><span>Required by</span><strong>${escapeHTML(requestRequiredDate(request.required_date))}</strong></div>
              <div><span>Created on</span><strong>${escapeHTML(formatDate(request.created_at))}</strong></div>
              <div><span>Estimated total</span><strong>${moneyOrPending(request.estimated_total, request.currency)}</strong></div>
              <div><span>Estimated budget</span><strong>${moneyOrPending(request.estimated_budget, request.currency)}</strong></div>
              <div><span>Selected quotation (incl. tax)</span><strong>${moneyOrPending(selectedQuoteTotal, request.currency)}</strong></div>
              <div><span>Quote vs request estimate</span><strong>${approvedVariance == null ? "Not available" : `${approvedVariance >= 0 ? "+" : "−"}${money(Math.abs(approvedVariance), request.currency)}`}</strong></div>
            </div>
          </section>
          <section class="panel approval-request-items-panel">
            <div class="panel-heading"><div><span class="eyebrow">REQUESTED GOODS & SERVICES</span><h2>Line items</h2><p>Review exactly what the employee requested before recording your decision.</p></div></div>
            <div class="approval-request-items">${itemRows || `<div class="approval-request-empty">No line items were recorded for this request.</div>`}</div>
          </section>
          <section class="approval-evidence-grid">
            <article class="panel"><div class="panel-heading"><div><span class="eyebrow">VALIDATION & EVIDENCE</span><h2>Check outcomes</h2><p>The evidence recorded during request validation.</p></div></div>
              <div class="approval-evidence-row"><span>Budget validation</span>${checkPill(request.budget_check_status)}<p>${escapeHTML(request.budget_check_message || "No budget validation message recorded.")}</p></div>
              <div class="approval-evidence-row"><span>Policy validation</span>${checkPill(request.policy_check_status)}<p>${escapeHTML(request.policy_check_message || "No policy validation message recorded.")}</p></div>
            </article>
            <article class="panel"><div class="panel-heading"><div><span class="eyebrow">SUPPLIER DECISION</span><h2>Selected supplier</h2><p>Commercial sourcing evidence retained with the request.</p></div></div>
              ${selectedSupplier ? `<div class="approval-supplier-card"><strong>${escapeHTML(supplierDetails.supplier_name || "Selected supplier")}</strong><span>${escapeHTML(supplierDetails.supplier_code || "")}</span><small>Selected ${escapeHTML(formatDate(supplierEvent.created_at))}</small></div><div class="approval-supplier-rationale">${escapeHTML(supplierDetails.rationale || "Selection rationale recorded in sourcing history.")}</div>` : `<div class="approval-request-empty">Supplier selection details are not available in the request history.</div>`}
            </article>
          </section>
        </main>
        <aside class="approval-review-side">
          <section class="panel approval-decision-panel">
            <div class="panel-heading"><div><span class="eyebrow">DECISION</span><h2>${canDecide?"Record your decision":"Decision already recorded"}</h2><p>${canDecide?"Choose approve or reject. Rejection requires a reason of at least 10 characters.":"This approval step is no longer actionable."}</p></div></div>
            ${canDecide?`<div class="approval-note">Only the assigned approver can decide this step. Earlier approval steps must be completed first.</div><div class="approval-decision-field"><label>Comment <textarea id="approval-comment" rows="6" maxlength="2000" placeholder="Optional for approval; required for rejection."></textarea></label><div class="approval-reject-help">For rejection, provide at least 10 characters explaining the decision.</div></div><div class="approval-toolbar"><button class="button button--danger" data-decision="REJECT">Reject request</button><button class="button button--primary" data-decision="APPROVE">Approve request</button></div>`:`${a.decision_comment?`<div class="approval-note"><strong>Decision note</strong><br>${escapeHTML(a.decision_comment)}</div>`:""}`}
          </section>
        </aside>
      </div>
      <section class="panel approval-chain-panel approval-chain-panel--full"><div class="panel-heading"><div><span class="eyebrow">APPROVAL CHAIN</span><h2>Mandatory review path</h2><p>Every employee purchase follows all three approval steps.</p></div></div><div class="approval-chain approval-chain--vertical">${["Manager", "Procurement Head", "Finance Manager"].map((role,i) => { const step=i+1; const text=step<a.approval_sequence?"Completed":step===a.approval_sequence?(a.approval_status==="APPROVED"?"Completed":"Current decision"):"Waiting"; return `<div class="approval-chain-row ${step===a.approval_sequence?"approval-chain-row--current":""}"><span>${step}</span><strong>${role}</strong><small>${text}</small></div>`; }).join("")}</div></section>`;
    els.content.querySelector("[data-back-approvals]")?.addEventListener("click",()=>navigate("approvals"));
    els.content.querySelectorAll("[data-decision]").forEach(button => button.addEventListener("click", async () => {
      const decision = button.dataset.decision;
      const comment = String(els.content.querySelector("#approval-comment")?.value || "").trim();
      if (decision === "REJECT" && comment.length < 10) { toast("A rejection comment must be at least 10 characters.","error"); return; }
      button.disabled = true;
      try { await api(`/purchase-request-approvals/${a.approval_id}/decision`, {method:"POST", body:JSON.stringify({decision, comment:comment || null})}); toast(decision === "APPROVE" ? "Approval recorded." : "Request rejected.", decision === "APPROVE" ? "success" : "error"); await navigate("approvals", {replaceUrl:true}); }
      catch(err) { toast(err.message,"error"); button.disabled=false; }
    }));
  }

  function dashboardDestination(title, row) {
    if ((title === "My requests" || title === "Department requests" || title === "Requests") && row.id) return ["request-detail", row.id];
    if ((title === "My approvals" || title === "Finance approvals" || title === "Approvals") && row.id) return ["approval-detail", row.id];
    if (title === "Purchase orders" && row.id) return ["purchase-order-detail", row.id];
    if (title === "Invoices" && row.id) return ["invoice-detail", row.id];
    const fallback = { "RFQs": "rfqs", "Supplier responses": "quotes", "Expected deliveries": "deliveries", "Invoice exceptions": "exceptions", "Exceptions": "exceptions" };
    return fallback[title] ? [fallback[title], ""] : null;
  }
  function dashboardSection(title, copy, rows, columns) {
    if (!rows || !rows.length) return `<section class="panel"><div class="panel-heading"><div><span class="eyebrow">COMMAND CENTER</span><h2>${escapeHTML(title)}</h2><p>${escapeHTML(copy)}</p></div></div><div class="empty-inline">Nothing requires attention here.</div></section>`;
    return `<section class="panel"><div class="panel-heading"><div><span class="eyebrow">COMMAND CENTER</span><h2>${escapeHTML(title)}</h2><p>${escapeHTML(copy)}</p></div></div><div class="table-wrap"><table><thead><tr>${columns.map(c => `<th>${escapeHTML(c.label)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => { const dest = dashboardDestination(title, row); return `<tr ${dest ? `class="dashboard-navigable" tabindex="0" role="link" data-dashboard-view="${escapeHTML(dest[0])}" data-dashboard-id="${escapeHTML(dest[1])}" aria-label="Open ${escapeHTML(title)} record"` : ""}>${columns.map(c => `<td>${c.render ? c.render(row) : escapeHTML(row[c.key] ?? "—")}</td>`).join("")}</tr>`; }).join("")}</tbody></table></div></section>`;
  }

  async function renderCommandCenter() {
    const data = await api("/dashboard");
    const k = data.kpis || {};
    const moneyValue = money(k.spend || 0);
    const roleTitles = { EMPLOYEE: "My Procurement Command Center", MANAGER: "My Procurement Command Center", PROCUREMENT_ANALYST: "Procurement Command Center", PROCUREMENT_HEAD: "Procurement Command Center", AP_ANALYST: "Finance Control Center", FINANCE_MANAGER: "Finance Control Center", GOODS_RECEIVER: "Receiving Command Center" };
    const roleTitle = roleTitles[data.role] || data.title || "Procurement Command Center";
    const roleCopy = {
      EMPLOYEE: "Track your purchase requests from one operational view.",
      MANAGER: "Review department requests and approvals that need your decision.",
      PROCUREMENT_ANALYST: "Monitor sourcing, purchasing, deliveries, invoices, and exceptions.",
      PROCUREMENT_HEAD: "See procurement flow, intervention points, and operational exceptions.",
      AP_ANALYST: "Review invoice readiness and 3-way match exceptions.",
      FINANCE_MANAGER: "Review finance approvals, invoice exceptions, and payment readiness evidence.",
      GOODS_RECEIVER: "Track issued orders awaiting receipt and partial deliveries.",
    }[data.role] || "Live procurement operations across the available workflows.";

    const allCards = {
      open_requests: ["Open requests", k.open_requests, "Requests still in progress", "green", "▤"],
      pending_approvals: ["Pending approvals", k.pending_approvals, "Awaiting assigned decision", "blue", "✓"],
      rfqs_awaiting_response: ["RFQs awaiting response", k.rfqs_awaiting_response, "Supplier responses outstanding", "amber", "⌘"],
      pos_awaiting_issue: ["POs awaiting issue", k.pos_awaiting_issue, "Draft or pending release", "violet", "▣"],
      expected_deliveries: ["Expected deliveries", k.expected_deliveries, "Issued POs with quantity remaining", "blue", "◫"],
      partial_receipts: ["Partial receipts", k.partial_receipts, "Orders with receipt progress", "amber", "◐"],
      invoice_exceptions: ["Invoice exceptions", k.invoice_exceptions, "Invoices requiring attention", "red", "△"],
      three_way_match_exceptions: ["3-way match exceptions", k.three_way_match_exceptions, "Persisted match exceptions", "red", "≠"],
      spend: ["Spend", moneyValue, "Issued purchase-order value", "green", "₹"],
    };
    const cardSets = {
      EMPLOYEE: ["open_requests"],
      MANAGER: ["open_requests", "pending_approvals"],
      PROCUREMENT_ANALYST: Object.keys(allCards),
      PROCUREMENT_HEAD: Object.keys(allCards),
      AP_ANALYST: ["invoice_exceptions", "three_way_match_exceptions"],
      FINANCE_MANAGER: ["pending_approvals", "invoice_exceptions", "three_way_match_exceptions", "spend"],
      GOODS_RECEIVER: ["expected_deliveries", "partial_receipts"],
    };
    const cards = (cardSets[data.role] || Object.keys(allCards)).map(key => allCards[key]);

    let body = `${pageHeader("PROCUREMENT COMMAND CENTER", roleTitle, roleCopy)}<section class="metric-grid metric-grid--five">${cards.map(c => statCard(c[0], c[1], c[2], c[3], c[4])).join("")}</section>`;
    const s = data.sections || {};
    const status = value => `<span class="pill">${escapeHTML(value || "—")}</span>`;
    const amount = value => escapeHTML(money(value || 0));

    if (data.role === "EMPLOYEE") {
      body += dashboardSection("My requests", "Your active purchase-request queue.", s.requests, [
        {label:"Request", key:"number"}, {label:"Title", key:"title"}, {label:"Status", render:r=>status(r.status)}, {label:"Value", render:r=>amount(r.amount)}, {label:"Required", key:"required_date"}
      ]);
    } else if (data.role === "MANAGER") {
      body += `<div class="dashboard-grid">${dashboardSection("Department requests", "Requests from your department.", s.requests, [{label:"Request",key:"number"},{label:"Title",key:"title"},{label:"Status",render:r=>status(r.status)},{label:"Value",render:r=>amount(r.amount)}])}${dashboardSection("My approvals", "Approval decisions currently assigned to you.", s.approvals, [{label:"Request",key:"request_number"},{label:"Step",render:r=>escapeHTML(String(r.sequence))},{label:"Role",key:"approver_role"},{label:"Status",render:r=>status(r.status)}])}</div>`;
    } else if (data.role === "AP_ANALYST" || data.role === "FINANCE_MANAGER") {
      body += `<div class="dashboard-grid">${data.role === "FINANCE_MANAGER" ? dashboardSection("Finance approvals", "Approval decisions currently assigned to you.", s.approvals, [{label:"Request",key:"request_number"},{label:"Step",render:r=>escapeHTML(String(r.sequence))},{label:"Role",key:"approver_role"},{label:"Status",render:r=>status(r.status)}]) : ""}${dashboardSection("Invoice exceptions", "Invoices requiring finance attention.", s.exceptions, [{label:"Invoice",key:"invoice_number"},{label:"Result",render:r=>status(r.result)},{label:"Qty variance",render:r=>escapeHTML(String(r.quantity_variance))},{label:"Price variance",render:r=>amount(r.price_variance)}])}</div>${dashboardSection("Invoices", "Latest supplier invoices visible to Finance.", s.invoices, [{label:"Invoice",key:"number"},{label:"Supplier",key:"supplier"},{label:"Status",render:r=>status(r.status)},{label:"Total",render:r=>amount(r.total)},{label:"Due",key:"due_date"}])}`;
    } else if (data.role === "GOODS_RECEIVER") {
      body += dashboardSection("Expected deliveries", "Issued purchase orders with outstanding quantity.", s.deliveries, [{label:"PO",key:"number"},{label:"Supplier",key:"supplier"},{label:"Ordered",render:r=>escapeHTML(String(r.ordered_quantity))},{label:"Received",render:r=>escapeHTML(String(r.received_quantity))},{label:"Remaining",render:r=>escapeHTML(String(r.remaining_quantity))},{label:"Required",key:"required_date"}]);
    } else {
      body += `<div class="dashboard-grid">${dashboardSection("Requests", "Active procurement requests.", s.requests, [{label:"Request",key:"number"},{label:"Title",key:"title"},{label:"Status",render:r=>status(r.status)},{label:"Value",render:r=>amount(r.amount)}])}${dashboardSection("Approvals", "Pending approval steps.", s.approvals, [{label:"Request",key:"request_number"},{label:"Step",render:r=>escapeHTML(String(r.sequence))},{label:"Role",key:"approver_role"},{label:"Status",render:r=>status(r.status)}])}</div>`;
      body += `<div class="dashboard-grid">${dashboardSection("RFQs", "Sourcing requests and response deadlines.", s.rfqs, [{label:"RFQ",key:"number"},{label:"Request",key:"request_number"},{label:"Status",render:r=>status(r.status)},{label:"Deadline",key:"response_deadline"}])}${dashboardSection("Supplier responses", "Supplier invitations still awaiting response.", s.supplier_responses, [{label:"Supplier",key:"supplier"},{label:"Status",render:r=>status(r.status)}])}</div>`;
      body += `<div class="dashboard-grid">${dashboardSection("Purchase orders", "Latest purchasing documents.", s.purchase_orders, [{label:"PO",key:"number"},{label:"Supplier",key:"supplier"},{label:"Status",render:r=>status(r.status)},{label:"Total",render:r=>amount(r.total)}])}${dashboardSection("Exceptions", "Persisted 3-way match exceptions.", s.exceptions, [{label:"Invoice",key:"invoice_number"},{label:"Result",render:r=>status(r.result)},{label:"Qty variance",render:r=>escapeHTML(String(r.quantity_variance))},{label:"Price variance",render:r=>amount(r.price_variance)}])}</div>`;
      body += dashboardSection("Expected deliveries", "Issued purchase orders with outstanding quantity.", s.deliveries, [{label:"PO",key:"number"},{label:"Supplier",key:"supplier"},{label:"Ordered",render:r=>escapeHTML(String(r.ordered_quantity))},{label:"Received",render:r=>escapeHTML(String(r.received_quantity))},{label:"Remaining",render:r=>escapeHTML(String(r.remaining_quantity))},{label:"Required",key:"required_date"}]);
    }
    els.content.innerHTML = body;
    const metricTargets = {"Open requests": data.role === "EMPLOYEE" ? "my-requests" : "requests", "Pending approvals": "approvals", "RFQs awaiting response": "rfqs", "POs awaiting issue": "purchase-orders", "Expected deliveries": "deliveries", "Partial receipts": "receipts", "Invoice exceptions": "invoices", "3-way match exceptions": "exceptions", "Spend": "purchase-orders"};
    els.content.querySelectorAll(".metric-grid > *").forEach((card, index) => {
      const view = metricTargets[cards[index]?.[0]];
      if (view && viewAllowedForCurrentUser(view)) { card.classList.add("dashboard-navigable"); card.tabIndex = 0; card.setAttribute("role", "link"); card.setAttribute("aria-label", `Open ${cards[index][0]}`); card.addEventListener("click", () => navigate(view)); card.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate(view); } }); }
    });
    els.content.querySelectorAll("[data-dashboard-view]").forEach(row => {
      const open = () => { const view = row.dataset.dashboardView; if (!viewAllowedForCurrentUser(view)) return; const id = row.dataset.dashboardId; if (view === "request-detail") state.selectedRequestId = id; else if (view === "approval-detail") state.approvalId = id; else if (view === "purchase-order-detail") state.purchaseOrderId = id; else if (view === "invoice-detail") state.invoiceId = id; navigate(view); };
      row.addEventListener("click", open);
      row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    });
  }

  async function renderHome() {
    if (state.user.roles.includes("ADMINISTRATOR")) return renderAdminHome();
    return renderCommandCenter();
  }

  async function loadAdminData() {
    const calls = [];
    if (hasPermission("master_data.manage")) calls.push(api("/admin/master-data/departments").then(v => state.departments = v), api("/admin/master-data/budgets").then(v => state.budgets = v), api("/admin/master-data/vendors").then(v => state.vendors = v));
    if (hasPermission("users.read")) calls.push(api("/admin/users").then(v => state.users = v), api("/admin/roles").then(v => state.roles = v), api("/admin/audit/logs?limit=20").then(v => state.audit = v));
    await Promise.all(calls);
  }

  async function renderAdminHome() {
    await loadAdminData();
    const activeUsers = state.users.filter(u => u.is_active).length;
    const inactiveUsers = state.users.filter(u => !u.is_active).length;
    const activeVendors = state.vendors.filter(v => v.is_active).length;
    const allocated = state.budgets.reduce((sum,b) => sum + Number(b.allocated_amount), 0);
    const consumed = state.budgets.reduce((sum,b) => sum + Number(b.consumed_amount), 0);
    const budgetPct = allocated ? Math.round((consumed / allocated) * 100) : 0;
    const humanAudit = state.audit.filter(a => a.actor_type === "HUMAN").length;
    const recent = state.audit.slice(0, 7);
    const privilegedUsers = state.users.filter(u => u.roles.some(r => ["ADMINISTRATOR","PROCUREMENT_HEAD","FINANCE_MANAGER"].includes(r))).length;

    const control = (icon, title, copy, value, tone = "green") => `<div class="control-card control-card--${tone}"><span class="control-icon">${icon}</span><div><strong>${escapeHTML(title)}</strong><small>${escapeHTML(copy)}</small></div><b>${escapeHTML(String(value))}</b></div>`;

    els.content.innerHTML = `${pageHeader("ADMINISTRATION", `Good ${greeting()}, ${firstName(state.user.full_name)}`, "Manage identity, master data, financial controls, supplier records, and governance from one secure workspace.", `<button class="button button--primary" data-action="create-user">+ New user</button>`)}
      <section class="metric-grid metric-grid--five">
        ${statCard("Active users", activeUsers, `${inactiveUsers} inactive`, "green", "\u25ce")}
        ${statCard("Departments", state.departments.length, "Organizational units", "blue", "\u25c7")}
        ${statCard("Active vendors", activeVendors, `${state.vendors.length} total vendors`, "violet", "\u25eb")}
        ${statCard("Budget utilization", `${budgetPct}%`, `${money(consumed)} consumed`, budgetPct > 85 ? "red" : "amber", "\u20b9")}
        ${statCard("Recent human events", humanAudit, "Latest 20 audit entries", "green", "\u25c9")}
      </section>

      <section class="dashboard-grid admin-dashboard-grid">
        <article class="panel panel--span-2">
          <div class="panel-heading"><div><span class="eyebrow">ENTERPRISE ADMINISTRATION</span><h2>Operational control overview</h2><p>Live status of the configuration and governance areas that keep ProcurePilot controlled and auditable.</p></div><span class="pill pill--success">Systems healthy</span></div>
          <div class="control-grid">
            ${control("\u25ce", "Identity & access", `${state.roles.length} roles configured`, `${activeUsers} users`, "green")}
            ${control("\u25c7", "Organization", "Departments and ownership", `${state.departments.length} units`, "blue")}
            ${control("\u20b9", "Financial controls", "Department budget envelopes", `${state.budgets.length} budgets`, budgetPct > 85 ? "amber" : "green")}
            ${control("\u25eb", "Supplier master", "Eligible enterprise vendors", `${activeVendors} active`, "violet")}
            ${control("\u25c9", "Governance", "Human / system traceability", `${state.audit.length} events`, "green")}
            ${control("\u2699", "Privileged access", "Elevated enterprise roles", `${privilegedUsers} users`, "blue")}
          </div>
          <div class="admin-callout"><span class="admin-callout-icon">\u2713</span><div><strong>Core controls are active</strong><span>Authentication, database-backed RBAC, master data, budget controls, vendor records, and audit visibility are available from this workspace.</span></div></div>
        </article>

        <article class="panel">
          <div class="panel-heading"><div><span class="eyebrow">BUDGET HEALTH</span><h2>Allocated vs. consumed</h2></div><button class="text-link" data-nav="budgets">View budgets \u2192</button></div>
          <div class="donut" style="--pct:${Math.min(budgetPct,100)}"><div><strong>${budgetPct}%</strong><span>consumed</span></div></div>
          <div class="budget-summary"><span><i class="legend legend--blue"></i>Allocated <b>${money(allocated)}</b></span><span><i class="legend legend--green"></i>Consumed <b>${money(consumed)}</b></span><span><i class="legend legend--soft"></i>Available <b>${money(Math.max(allocated-consumed,0))}</b></span></div>
        </article>

        <article class="panel panel--span-2">
          <div class="panel-heading"><div><span class="eyebrow">RECENT ADMINISTRATIVE ACTIVITY</span><h2>What changed across the enterprise</h2><p>Latest auditable actions from users and the platform.</p></div><button class="text-link" data-nav="audit">View audit trail \u2192</button></div>
          <div class="audit-list audit-list--admin">${recent.length ? recent.map(auditRow).join("") : `<div class="empty-inline">No administrative activity yet.</div>`}</div>
        </article>

        <article class="panel">
          <div class="panel-heading"><div><span class="eyebrow">ACCESS & CONFIGURATION</span><h2>Administration snapshot</h2></div></div>
          <div class="health-list"><span><b>Configured roles</b><strong>${state.roles.length}</strong></span><span><b>Active users</b><strong>${activeUsers}</strong></span><span><b>Inactive users</b><strong>${inactiveUsers}</strong></span><span><b>Departments</b><strong>${state.departments.length}</strong></span><span><b>Active vendors</b><strong>${activeVendors}</strong></span><span><b>Audit visibility</b><strong class="text-success">Enabled</strong></span></div>
          <div class="quick-links"><button class="quick-link" data-nav="users"><span>\u25ce</span><b>Manage users</b><small>Roles & access</small></button><button class="quick-link" data-nav="vendors"><span>\u25eb</span><b>Vendor master</b><small>Eligibility & reliability</small></button><button class="quick-link" data-nav="departments"><span>\u25c7</span><b>Departments</b><small>Organization data</small></button></div>
        </article>
      </section>`;
    wireCommonActions();
  }

  function journeyStep(number, label, foot, done) { return `<div class="journey-step ${done ? "is-done" : ""}"><span>${done ? "\u2713" : number}</span><strong>${escapeHTML(label)}</strong><small>${escapeHTML(foot)}</small></div>`; }
  function greeting() { const h = new Date().getHours(); return h < 12 ? "morning" : h < 17 ? "afternoon" : "evening"; }
  function firstName(name) { return name?.split(" ")[0] || "there"; }

  async function renderUsers() {
    state.users = await api("/admin/users");
    state.roles = await api("/admin/roles");
    if (!state.departments.length && hasPermission("master_data.manage")) state.departments = await api("/admin/master-data/departments");
    const rows = state.users.map(user => `<tr><td><div class="user-cell"><span class="table-avatar">${initials(user.full_name)}</span><div><strong>${escapeHTML(user.full_name)}</strong><small>${escapeHTML(user.email)}</small></div></div></td><td>${user.roles.map(r => `<span class="pill">${escapeHTML(roleNames[r] || r)}</span>`).join(" ") || "\u2014"}</td><td>${departmentName(user.department_id)}</td><td><span class="status ${user.is_active ? "status--success" : "status--muted"}">${user.is_active ? "Active" : "Inactive"}</span></td><td>${formatDate(user.created_at)}</td></tr>`).join("");
    els.content.innerHTML = `${pageHeader("IDENTITY & ACCESS", "Users & Roles", "Create accounts, assign enterprise roles, and keep authorization visible.", hasPermission("users.manage") ? `<button class="button button--primary" data-action="create-user">+ New user</button>` : "")}
      <section class="metric-grid">${statCard("Users", state.users.length, `${state.users.filter(u=>u.is_active).length} active`, "green", "\u25ce")}${statCard("Roles", state.roles.length, "RBAC role catalog", "blue", "\u25c7")}${statCard("Administrators", state.users.filter(u=>u.roles.includes("ADMINISTRATOR")).length, "Privileged accounts", "amber", "\u2699")}${statCard("Inactive", state.users.filter(u=>!u.is_active).length, "Disabled access", "red", "\u25cb")}</section>
      ${tablePanel("User directory", "Database-backed identities and role assignments.", `<table><thead><tr><th>User</th><th>Roles</th><th>Department</th><th>Status</th><th>Created</th></tr></thead><tbody>${rows || emptyTableRow(5,"No users found")}</tbody></table>`)} `;
    wireCommonActions();
  }

  async function renderDepartments() {
    state.departments = await api("/admin/master-data/departments");
    const rows = state.departments.map(d => `<tr><td><span class="code-chip">${escapeHTML(d.code)}</span></td><td><strong>${escapeHTML(d.name)}</strong></td><td><span class="status ${d.is_active ? "status--success" : "status--muted"}">${d.is_active ? "Active" : "Inactive"}</span></td><td>${formatDate(d.updated_at)}</td><td>${hasPermission("master_data.manage") ? `<button class="button button--small button--ghost" data-edit-department="${d.id}">Edit</button>` : ""}</td></tr>`).join("");
    els.content.innerHTML = `${pageHeader("MASTER DATA", "Departments", "Enterprise organizational units used by budgets, users, policies, and future purchase workflows.", `<button class="button button--primary" data-action="create-department">+ Department</button>`)}
      ${tablePanel("Department master", `${state.departments.length} configured departments`, `<table><thead><tr><th>Code</th><th>Name</th><th>Status</th><th>Updated</th><th></th></tr></thead><tbody>${rows || emptyTableRow(5,"No departments found")}</tbody></table>`)} `;
    wireDepartmentActions();
  }

  async function renderBudgets() {
    state.budgets = await api("/admin/master-data/budgets");
    if (!state.departments.length) state.departments = await api("/admin/master-data/departments");
    const rows = state.budgets.map(b => { const pct = Number(b.allocated_amount) ? Math.round(Number(b.consumed_amount)/Number(b.allocated_amount)*100) : 0; return `<tr><td><strong>${departmentName(b.department_id)}</strong></td><td>${b.fiscal_year}</td><td>${escapeHTML(b.currency)}</td><td>${money(b.allocated_amount,b.currency)}</td><td>${money(b.consumed_amount,b.currency)}</td><td><div class="progress-cell"><span style="width:${Math.min(pct,100)}%"></span></div><small>${pct}%</small></td><td><span class="status ${b.is_active ? "status--success" : "status--muted"}">${b.is_active ? "Active" : "Inactive"}</span></td></tr>`; }).join("");
    els.content.innerHTML = `${pageHeader("FINANCE MASTER DATA", "Budgets", "Department-level budget envelopes that future policy and purchase-request checks will use.", `<button class="button button--primary" data-action="create-budget">+ Budget</button>`)}
      ${tablePanel("Budget register", `${state.budgets.length} configured budget envelopes`, `<table><thead><tr><th>Department</th><th>FY</th><th>Currency</th><th>Allocated</th><th>Consumed</th><th>Utilization</th><th>Status</th></tr></thead><tbody>${rows || emptyTableRow(7,"No budgets found")}</tbody></table>`)} `;
    wireCommonActions();
  }

  async function renderVendors() {
    state.vendors = await api("/admin/master-data/vendors");
    const active = state.vendors.filter(v => v.is_active);
    const average = state.vendors.length ? Math.round(state.vendors.reduce((sum, v) => sum + Number(v.reliability_score), 0) / state.vendors.length) : 0;
    const terms = state.vendors.length ? Math.round(state.vendors.reduce((sum, v) => sum + v.payment_terms_days, 0) / state.vendors.length) : 0;
    els.content.innerHTML = `${pageHeader("SUPPLIER MASTER", "Vendors", "Maintain supplier identity, contact, capability, commercial terms, and sourcing eligibility.", hasPermission("master_data.manage") ? `<button class="button button--primary" data-action="create-vendor">+ Vendor</button>` : "")}
      <section class="metric-grid">${statCard("Vendors", state.vendors.length, `${active.length} active`, "green", "\u25eb")}${statCard("Avg reliability", `${average}%`, "Across supplier master", "blue", "\u25c9")}${statCard("Payment terms", `${terms}d`, "Average terms", "amber", "\u25f7")}${statCard("Inactive", state.vendors.length-active.length, "Excluded from sourcing", "red", "\u25cb")}</section>
      <section class="panel vendor-toolbar"><div><span class="eyebrow">SUPPLIER DIRECTORY</span><strong>Find a supplier</strong><small>Search by code, legal name, contact, capability, or email.</small></div><label class="vendor-search"><span>\u2315</span><input id="vendor-search" type="search" placeholder="Search suppliers\u2026" autocomplete="off"></label><select id="vendor-status-filter" aria-label="Filter suppliers"><option value="all">All statuses</option><option value="active">Active only</option><option value="inactive">Inactive only</option></select></section>
      <section id="vendor-directory" class="panel table-panel"><div class="panel-heading"><div><span class="eyebrow">LIVE DATABASE DATA</span><h2>Supplier directory</h2><p>Only active suppliers are eligible for future sourcing workflows.</p></div></div><div class="table-wrap"><table><thead><tr><th>Code</th><th>Supplier</th><th>Capability</th><th>Terms</th><th>Reliability</th><th>Status</th><th>Action</th></tr></thead><tbody id="vendor-rows"></tbody></table></div></section>`;
    const draw = () => {
      const q = els.content.querySelector("#vendor-search").value.trim().toLowerCase();
      const status = els.content.querySelector("#vendor-status-filter").value;
      const filtered = state.vendors.filter(v => {
        const matchesStatus = status === "all" || (status === "active" ? v.is_active : !v.is_active);
        const haystack = [v.vendor_code, v.legal_name, v.email, v.contact_person, v.phone, v.capabilities, v.address].filter(Boolean).join(" ").toLowerCase();
        return matchesStatus && (!q || haystack.includes(q));
      });
      const rows = filtered.map(v => `<tr><td><span class="code-chip">${escapeHTML(v.vendor_code)}</span></td><td><strong>${escapeHTML(v.legal_name)}</strong><small class="table-subline">${escapeHTML(v.contact_person || "No contact person")} \u00b7 ${escapeHTML(v.email)}</small></td><td><span class="vendor-capability">${escapeHTML(v.capabilities || "Capability details not recorded")}</span></td><td>${v.payment_terms_days} days</td><td><div class="score"><span style="width:${Math.min(Number(v.reliability_score),100)}%"></span></div><b>${Number(v.reliability_score).toFixed(1)}</b></td><td><span class="status ${v.is_active ? "status--success" : "status--muted"}">${v.is_active ? "Active" : "Inactive"}</span></td><td>${hasPermission("master_data.manage") ? `<button class="text-link" data-edit-vendor="${v.id}">Edit</button>` : `<span class="muted">View only</span>`}</td></tr>`).join("");
      els.content.querySelector("#vendor-rows").innerHTML = rows || `<tr><td colspan="7" class="empty-cell"><strong>${q ? "No suppliers match your search" : status !== "all" ? `No ${status} suppliers` : "No suppliers yet"}</strong><br><small>${q ? "Try a supplier code, name, email, or capability." : "Create the first supplier record to make it available for sourcing."}</small></td></tr>`;
      els.content.querySelectorAll("[data-edit-vendor]").forEach(el => el.addEventListener("click", () => openEditVendor(el.dataset.editVendor)));
    };
    els.content.querySelector("#vendor-search").addEventListener("input", draw);
    els.content.querySelector("#vendor-status-filter").addEventListener("change", draw);
    draw();
    wireCommonActions();
  }

  async function renderAudit() {
    state.audit = await api("/admin/audit/logs?limit=200");
    const rows = state.audit.map(a => `<tr><td><span class="actor actor--${a.actor_type.toLowerCase()}">${actorIcon(a.actor_type)} ${escapeHTML(a.actor_type)}</span>${a.actor_user_name ? `<small class="table-subline">${escapeHTML(a.actor_user_name)}</small>` : ""}</td><td><strong>${humanizeAction(a.action)}</strong><small class="table-subline">${escapeHTML(a.action)}</small></td><td>${escapeHTML(a.entity_type)}<small class="table-subline">${escapeHTML(a.entity_id)}</small></td><td>${detailSummary(a.details)}</td><td>${formatDate(a.created_at)}</td></tr>`).join("");
    els.content.innerHTML = `${pageHeader("GOVERNANCE", "Audit Trail", "Inspect meaningful human and deterministic system actions from one immutable-style operational history.", `<button class="button button--ghost" data-action="refresh-audit">\u21bb Refresh</button>`)}
      <section class="metric-grid">${["HUMAN","SYSTEM"].map((type,i)=>statCard(type, state.audit.filter(a=>a.actor_type===type).length, "Latest 200 events", ["green","blue"][i], actorIcon(type))).join("")}${statCard("Total shown", state.audit.length, "Newest first", "amber", "\u25c9")}</section>
      ${tablePanel("Process audit trail", `${state.audit.length} event${state.audit.length === 1 ? "" : "s"} shown \u00b7 newest first.`, `<table><thead><tr><th>Actor</th><th>Action</th><th>Entity</th><th>Evidence</th><th>Time</th></tr></thead><tbody>${rows || emptyTableRow(5,"No audit events found")}</tbody></table>`)} `;
    wireCommonActions();
  }

  async function renderRFQs() {
    if (!hasPermission("sourcing.manage")) {
      els.content.innerHTML = emptyState("RFQ workspace unavailable", "Your account does not have permission to manage sourcing events.", "Go to home", () => navigate("home"));
      return;
    }
    if (navigator.onLine === false) {
      els.content.innerHTML = emptyState("You're offline", "RFQs need a connection to load live sourcing events.", "Try again", () => navigate("rfqs"));
      return;
    }
    let slowNotice;
    const slowTimer = window.setTimeout(() => {
      slowNotice = document.createElement("div");
      slowNotice.className = "inline-state inline-state--slow";
      slowNotice.innerHTML = "<span>\u25cc</span><div><strong>Still loading RFQs</strong><small>The connection is taking longer than usual. No sourcing changes have been made.</small></div>";
      els.content.prepend(slowNotice);
    }, 900);
    try {
      const [rfqs, suppliers, sourcingRequests] = await Promise.all([api("/rfqs"), api("/rfqs/eligible-suppliers"), api("/purchase-requests/sourcing/queue")]);
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      state.rfqs = rfqs; state.rfqSuppliers = suppliers; state.purchaseRequests = sourcingRequests;
      drawRFQWorkspace();
    } catch (err) {
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      els.content.innerHTML = emptyState("RFQs could not be loaded", err.message, "Try again", () => navigate("rfqs"));
    }
  }

  function drawRFQWorkspace() {
    const sent = state.rfqs.filter(r => r.status === "SENT").length;
    const drafts = state.rfqs.filter(r => r.status === "DRAFT").length;
    const active = state.rfqs.length;
    els.content.innerHTML = `${pageHeader("SOURCING", "RFQs", "Create and send structured requests for quotation to selected active suppliers. Each sent RFQ includes a secure quotation link for the supplier to submit their response.", `<button class="button button--primary" data-action="create-rfq">+ Create RFQ</button>`)}
      <section class="metric-grid">${statCard("RFQs", active, active ? "Sourcing events" : "No RFQs yet", "green", "\u2318")}${statCard("Drafts", drafts, "Ready to review", "violet", "\u270e")}${statCard("Sent", sent, "Awaiting supplier responses", "blue", "\u2197")}${statCard("Active suppliers", state.rfqSuppliers.length, "Eligible for invitation", "amber", "\u25eb")}</section>
      <section class="panel table-panel rfq-table-panel"><div class="panel-heading"><div><span class="eyebrow">SOURCING EVENTS</span><h2>Request for quotation</h2><p>Each RFQ is tied to one sourcing request and one or more selected suppliers.</p></div></div><div class="table-wrap"><table><thead><tr><th>RFQ</th><th>Purchase request</th><th>Status</th><th>Suppliers</th><th>Response deadline</th><th>Action</th></tr></thead><tbody id="rfq-rows"></tbody></table></div></section>`;
    const rows = state.rfqs.map(r => `<tr><td><strong>${escapeHTML(r.rfq_number)}</strong><small class="table-subline">Created ${relativeTime(r.created_at)}</small></td><td><strong>${escapeHTML(r.request_number)}</strong><small class="table-subline">${escapeHTML(r.request_title)}</small></td><td>${requestStatusPill(r.status === "SENT" ? "SENT" : "DRAFT")}</td><td>${r.supplier_count}</td><td>${formatDate(r.response_deadline)}</td><td>${r.status === "DRAFT" ? `<button class="button button--primary button--small" data-send-rfq="${r.id}">Send RFQ</button>` : `<span class="text-success">Sent</span>`}</td></tr>`).join("");
    els.content.querySelector("#rfq-rows").innerHTML = rows || `<tr><td colspan="6" class="empty-cell"><strong>No RFQs yet</strong><br><small>Create an RFQ after a purchase request has entered sourcing.</small></td></tr>`;
    wireCommonActions();
    els.content.querySelector("[data-action=create-rfq]")?.addEventListener("click", openCreateRFQ);
    els.content.querySelectorAll("[data-send-rfq]").forEach(button => button.addEventListener("click", async () => {
      button.disabled = true; button.textContent = "Sending\u2026";
      try { await api(`/rfqs/${button.dataset.sendRfq}/send`, { method: "POST" }); toast("RFQ recorded as sent to the selected suppliers."); await renderRFQs(); }
      catch (err) { toast(err.message, "error"); button.disabled = false; button.textContent = "Send RFQ"; }
    }));
  }

  function openCreateRFQ() {
    const sourcingRequests = state.purchaseRequests.filter(r => r.status === "SOURCING");
    if (!sourcingRequests.length) {
      return toast("No purchase requests are currently in sourcing. Start sourcing a validated request first.", "error");
    }
    const defaultDeadline = new Date(Date.now() + 7 * 86400000); defaultDeadline.setSeconds(0, 0);
    const localDeadline = new Date(defaultDeadline.getTime() - defaultDeadline.getTimezoneOffset() * 60000).toISOString().slice(0,16);
    const requestOptions = sourcingRequests.map(r => `<option value="${r.id}">${escapeHTML(r.request_number)} \u2014 ${escapeHTML(r.title)}</option>`).join("");
    const supplierOptions = state.rfqSuppliers.map(v => `<label class="rfq-supplier-option"><input type="checkbox" name="vendor_id" value="${v.id}"><span><strong>${escapeHTML(v.legal_name)}</strong><small>${escapeHTML(v.vendor_code)} \u00b7 ${escapeHTML(v.email)}</small></span></label>`).join("");
    modal({ title: "Create RFQ", submitLabel: "Create RFQ", body: `<div class="form-grid"><label class="field-span-2">Purchase request<select name="request_id" required>${requestOptions}</select></label><label class="field-span-2">Response deadline<input name="response_deadline" type="datetime-local" min="${new Date().toISOString().slice(0,16)}" value="${localDeadline}" required><small>Choose when supplier responses should be received.</small></label></div><fieldset><legend>Suppliers</legend><div class="rfq-supplier-list">${supplierOptions || `<div class="empty-inline">No active suppliers are available.</div>`}</div></fieldset><label class="field-span-2">RFQ instructions<textarea name="instructions" maxlength="2000" placeholder="Include delivery, quality, documentation, or commercial-response instructions."></textarea></label>`, onSubmit: async fd => {
      const vendorIds = Array.from(els.modalRoot.querySelectorAll("input[name=vendor_id]:checked")).map(x => x.value);
      if (!vendorIds.length) throw new Error("Select at least one active supplier.");
      const requestId = fd.get("request_id");
      const deadline = new Date(fd.get("response_deadline"));
      if (Number.isNaN(deadline.getTime()) || deadline <= new Date()) throw new Error("Choose a future response deadline.");
      await api("/rfqs", { method: "POST", body: JSON.stringify({ request_id: requestId, vendor_ids: vendorIds, response_deadline: deadline.toISOString(), instructions: fd.get("instructions") || null }) });
      toast("RFQ created. Review it before sending to suppliers."); await renderRFQs();
    }});
  }

  async function renderQuotations() {
    if (!hasPermission("sourcing.manage")) {
      els.content.innerHTML = emptyState("Quotation workspace unavailable", "Your account does not have permission to manage supplier quotations.", "Go to home", () => navigate("home"));
      return;
    }
    if (navigator.onLine === false) {
      els.content.innerHTML = emptyState("You're offline", "Quotations need a connection to load supplier responses.", "Try again", () => navigate("quotes"));
      return;
    }
    let slowNotice;
    const slowTimer = window.setTimeout(() => {
      slowNotice = document.createElement("div");
      slowNotice.className = "inline-state inline-state--slow";
      slowNotice.innerHTML = "<span>\u25cc</span><div><strong>Still loading quotations</strong><small>The connection is taking longer than usual. No quotation changes have been made.</small></div>";
      els.content.prepend(slowNotice);
    }, 900);
    try {
      const [quotations, pending] = await Promise.all([api("/quotations"), api("/quotations/pending")]);
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      state.quotations = quotations; state.pendingQuotations = pending;
      drawQuotationWorkspace();
    } catch (err) {
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      els.content.innerHTML = emptyState("Quotations could not be loaded", err.message, "Try again", () => navigate("quotes"));
    }
  }

  function drawQuotationWorkspace() {
    const received = state.quotations.length;
    const pending = state.pendingQuotations.length;
    const sentRfqs = new Set(state.quotations.map(q => q.rfq_id).concat(state.pendingQuotations.map(q => q.rfq_id))).size;
    const quotedValue = state.quotations.reduce((sum, q) => sum + Number(q.total_amount || 0), 0);

    els.content.innerHTML = `${pageHeader("SOURCING", "Quotations", "Record supplier responses received against sent RFQs. Commercial values are captured here for later comparison.", pending ? `<span class="status status--muted">${pending} response${pending === 1 ? "" : "s"} pending</span>` : "")}
      <section class="metric-grid">
        ${statCard("Received", received, received ? "Supplier quotations" : "No quotations yet", "green", "\u2713")}
        ${statCard("Pending responses", pending, pending ? "Awaiting supplier input" : "All invited suppliers responded", "violet", "\u231b")}
        ${statCard("RFQs in response", sentRfqs, "Sent sourcing events", "blue", "\u2197")}
        ${statCard("Quoted value", received ? money(quotedValue) : "Not available", received ? "Total received quotations" : "No supplier pricing yet", "amber", "\u25c8")}
      </section>

      <section class="panel table-panel quotation-panel quotation-panel--pending">
        <div class="panel-heading"><div><span class="eyebrow">SUPPLIER RESPONSES</span><h2>Awaiting quotation</h2><p>Record commercial responses exactly as received. ProcurePilot does not invent supplier pricing.</p></div></div>
        <div class="table-wrap"><table><thead><tr><th>RFQ</th><th>Supplier</th><th>Requested item</th><th>Quantity</th><th>Deadline</th><th>Action</th></tr></thead><tbody>
          ${state.pendingQuotations.length ? state.pendingQuotations.map(q => `<tr><td><strong>${escapeHTML(q.rfq_number)}</strong><small class="table-subline">${escapeHTML(q.request_number)}</small></td><td><strong>${escapeHTML(q.supplier_name)}</strong><small class="table-subline">${escapeHTML(q.supplier_code)} \u00b7 ${escapeHTML(q.supplier_email)}</small></td><td>${escapeHTML(q.item_name)}</td><td>${escapeHTML(q.quantity)} ${escapeHTML(q.currency)}</td><td>${formatDate(q.response_deadline)}</td><td><span class="status status--muted">Awaiting supplier response</span></td></tr>`).join("") : `<tr><td colspan="6" class="empty-cell"><strong>${received ? "No supplier responses pending" : "No sent RFQs awaiting responses"}</strong><br><small>${received ? "Every invited supplier currently has a recorded response." : "Send an RFQ first, then record supplier responses here."}</small></td></tr>`}
        </tbody></table></div>
      </section>

      <section class="panel table-panel quotation-comparison-queue">
        <div class="panel-heading"><div><span class="eyebrow">COMMERCIAL REVIEW</span><h2>Quotation comparison</h2><p>Compare supplier responses for the same RFQ using the commercial facts captured from each quotation.</p></div></div>
        <div class="comparison-queue-list">${buildQuotationComparisonQueue()}</div>
      </section>

      <section class="panel table-panel quotation-panel quotation-panel--recorded">
        <div class="panel-heading"><div><span class="eyebrow">RECEIVED COMMERCIALS</span><h2>Recorded quotations</h2><p>Supplier-provided prices, delivery commitments, validity, and tax are retained as sourcing evidence.</p></div></div>
        <div class="table-wrap"><table><thead><tr><th>RFQ</th><th>Supplier</th><th>Unit price</th><th>Total</th><th>Delivery</th><th>Valid until</th><th>Action</th></tr></thead><tbody>
          ${state.quotations.length ? state.quotations.map(q => `<tr><td><strong>${escapeHTML(q.rfq_number)}</strong><small class="table-subline">${escapeHTML(q.request_number)}</small></td><td><strong>${escapeHTML(q.vendor_name)}</strong><small class="table-subline">${escapeHTML(q.vendor_code)}</small></td><td>${q.items?.length ? `${q.items.length} itemized lines` : money(q.unit_price, q.currency)}<small class="table-subline">${q.items?.length ? q.items.map(i => `${escapeHTML(i.item_name)}: ${escapeHTML(i.quantity)} @ ${money(i.unit_price, q.currency)}`).join(" · ") : `Legacy package: ${escapeHTML(q.quoted_quantity)} quoted`}</small></td><td><strong>${money(q.total_amount, q.currency)}</strong><small class="table-subline">Tax ${money(q.tax_amount, q.currency)}</small></td><td>${escapeHTML(q.delivery_days)} days</td><td>${requestRequiredDate(q.valid_until)}</td></tr>`).join("") : `<tr><td colspan="6" class="empty-cell"><strong>No quotations recorded yet</strong><br><small>Supplier responses will appear here after they are entered.</small></td></tr>`}
        </tbody></table></div>
      </section>`;
    els.content.querySelectorAll("[data-compare-rfq]").forEach(button => button.addEventListener("click", () => { state.comparisonRfqId = button.dataset.compareRfq; navigate("quotation-comparison"); }));
    els.content.querySelectorAll("[data-select-rfq]").forEach(button => button.addEventListener("click", () => { state.selectionRfqId = button.dataset.selectRfq; navigate("supplier-selection"); }));
  }

  function buildQuotationComparisonQueue() {
    const groups = new Map();
    state.quotations.forEach(q => {
      if (!groups.has(q.rfq_id)) groups.set(q.rfq_id, { rfq_id: q.rfq_id, rfq_number: q.rfq_number, request_number: q.request_number, request_title: q.request_title, request_status: q.request_status, received: 0, pending: 0 });
      groups.get(q.rfq_id).received += 1;
    });
    state.pendingQuotations.forEach(q => {
      if (!groups.has(q.rfq_id)) groups.set(q.rfq_id, { rfq_id: q.rfq_id, rfq_number: q.rfq_number, request_number: q.request_number, request_title: q.request_title, request_status: q.request_status, received: 0, pending: 0 });
      groups.get(q.rfq_id).pending += 1;
    });
    const rows = [...groups.values()].sort((a,b) => a.rfq_number.localeCompare(b.rfq_number));
    if (!rows.length) return `<div class="comparison-empty"><strong>No sent RFQs have quotation activity yet.</strong><small>Send an RFQ and record at least one supplier response to open a comparison.</small></div>`;
    const active = rows.filter(g => g.request_status === "SOURCING");
    const historical = rows.filter(g => g.request_status !== "SOURCING");
    const renderGroup = (items, archived) => items.map(g => {
      const ready = g.received > 0;
      const total = g.received + g.pending;
      return `<article class="comparison-queue-item"><div class="comparison-queue-copy"><span class="code-chip">${escapeHTML(g.rfq_number)}</span><strong>${escapeHTML(g.request_title)}</strong><small>${escapeHTML(g.request_number)} · ${g.received} received · ${g.pending} awaiting · ${total} invited · ${escapeHTML(g.request_status || "Unknown")}</small></div><div class="comparison-queue-action">${ready ? `<button class="button button--ghost button--small" data-compare-rfq="${g.rfq_id}">${archived ? "View comparison" : "Compare quotations"}</button>` : `<span class="status status--muted">Awaiting responses</span>`}</div></article>`;
    }).join("");
    return `<h3 class="comparison-group-title">Active sourcing (${active.length})</h3>${renderGroup(active, false) || `<p class="muted">No active sourcing comparisons.</p>`}
    <h3 class="comparison-group-title">Historical / approved sourcing (${historical.length})</h3>${renderGroup(historical, true) || `<p class="muted">No historical comparisons.</p>`}`;
  }

  async function renderQuotationComparison(rfqId) {
    if (!hasPermission("sourcing.manage")) {
      els.content.innerHTML = emptyState("Comparison unavailable", "Your account does not have permission to review supplier quotations.", "Go to quotations", () => navigate("quotes"));
      return;
    }
    if (!rfqId) {
      els.content.innerHTML = emptyState("No RFQ selected", "Choose an RFQ with recorded supplier quotations to compare commercial responses.", "Go to quotations", () => navigate("quotes"));
      return;
    }
    if (navigator.onLine === false) {
      els.content.innerHTML = emptyState("You're offline", "Quotation comparison needs a connection to load current supplier responses.", "Try again", () => renderQuotationComparison(rfqId));
      return;
    }
    let slowNotice;
    const slowTimer = window.setTimeout(() => {
      slowNotice = document.createElement("div");
      slowNotice.className = "inline-state inline-state--slow";
      slowNotice.innerHTML = "<span>\u25cc</span><div><strong>Still loading comparison</strong><small>The connection is taking longer than usual. No sourcing changes have been made.</small></div>";
      els.content.prepend(slowNotice);
    }, 900);
    try {
      const comparison = await api(`/quotations/compare/${rfqId}`);
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      drawQuotationComparison(comparison);
    } catch (err) {
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      els.content.innerHTML = emptyState("Comparison could not be loaded", err.message, "Back to quotations", () => navigate("quotes"));
    }
  }

  function drawQuotationComparison(comparison) {
    const rows = comparison.rows || [];
    const received = comparison.received_quotation_count;
    const pending = comparison.pending_response_count;
    const statusCopy = pending ? `${received} of ${comparison.invited_supplier_count} supplier responses recorded · ${pending} awaiting` : `All ${received} invited supplier responses recorded`;
    els.content.innerHTML = `${pageHeader("SOURCING · COMMERCIAL REVIEW", "Quotation Comparison", "Review supplier-provided commercial terms side-by-side before the separate supplier selection workflow.", `<button class="button button--ghost" data-back-quotes>← Back to quotations</button>`)}
      <section class="metric-grid">
        ${statCard("Invited suppliers", comparison.invited_supplier_count, "Suppliers included in this RFQ", "green", "\u25eb")}
        ${statCard("Responses received", received, received ? "Recorded supplier quotations" : "No quotations recorded", "blue", "\u2713")}
        ${statCard("Awaiting responses", pending, pending ? "Supplier responses still open" : "No responses pending", pending ? "amber" : "green", "\u231b")}
        ${statCard("RFQ currency", escapeHTML(comparison.request_currency), "Commercial values shown as received", "violet", "\u25c8")}
      </section>
      <section class="panel comparison-context"><div><span class="eyebrow">RFQ ${escapeHTML(comparison.rfq_number)}</span><h2>${escapeHTML(comparison.request_title)}</h2><p>${escapeHTML(comparison.request_number)}${comparison.request_category ? ` · ${escapeHTML(comparison.request_category)}` : ""}</p></div><div class="comparison-context-meta"><span class="status status--muted">${escapeHTML(statusCopy)}</span><small>Response deadline · ${formatDate(comparison.response_deadline)}</small></div></section>
      ${received < 2 ? `<section class="inline-state comparison-notice"><span>\u25cf</span><div><strong>Comparison is available with ${received} recorded response${received === 1 ? "" : "s"}.</strong><small>${pending ? "Additional supplier responses will appear here when recorded. Supplier selection remains a separate workflow." : "Record additional supplier responses when available for a fuller commercial comparison."}</small></div></section>` : ""}
      <section class="panel table-panel comparison-table-panel"><div class="panel-heading"><div><span class="eyebrow">COMMERCIAL FACTS</span><h2>Supplier response comparison</h2><p>Values below come from recorded supplier quotations. No supplier is automatically selected.</p></div></div><div class="table-wrap"><table><thead><tr><th>Supplier</th><th>Response</th><th>Quoted quantity</th><th>Unit price</th><th>Tax</th><th>Total</th><th>Delivery</th><th>Valid until</th><th>Action</th></tr></thead><tbody>${rows.length ? rows.map(row => comparisonRowHTML(row, comparison.rfq_id, comparison.request_status === "SOURCING")).join("") : `<tr><td colspan="9" class="empty-cell"><strong>No supplier quotations recorded</strong><br><small>Return to Quotations and record a supplier response before comparing commercial terms.</small></td></tr>`}</tbody></table></div></section>`;
    els.content.querySelector("[data-back-quotes]")?.addEventListener("click", () => navigate("quotes"));
    els.content.querySelectorAll("[data-select-rfq]").forEach(button => button.addEventListener("click", () => { state.selectionRfqId = button.dataset.selectRfq; navigate("supplier-selection"); }));
  }

  function comparisonRowHTML(row, rfqId, canSelect) {
    const received = row.quotation_id != null;
    return `<tr class="${received ? "" : "comparison-row--pending"}"><td><strong>${escapeHTML(row.supplier_name)}</strong><small class="table-subline">${escapeHTML(row.supplier_code)} · ${escapeHTML(row.supplier_email)}</small></td><td>${received ? `<span class="status status--success">Received</span><small class="table-subline">${formatDate(row.received_at)}</small>` : `<span class="status status--muted">Awaiting response</span>`}</td><td>${received ? (row.items?.length ? `${row.items.length} lines` : `${escapeHTML(row.quoted_quantity)} package`) : "—"}</td><td>${received ? (row.items?.length ? row.items.map(i=>`${escapeHTML(i.item_name)}: ${escapeHTML(i.quantity)} × ${money(i.unit_price, row.currency)}`).join("<br>") : money(row.unit_price, row.currency)) : "—"}</td><td>${received ? money(row.tax_amount, row.currency) : "—"}</td><td>${received ? `<strong>${money(row.total_amount, row.currency)}</strong>` : "—"}</td><td>${received ? `${escapeHTML(row.delivery_days)} days` : "—"}</td><td>${received ? requestRequiredDate(row.valid_until) : "—"}</td><td>${received && canSelect ? `<button class="button button--primary button--small" data-select-rfq="${rfqId}" data-select-supplier="${row.rfq_supplier_id}">Select supplier</button>` : `<span class="muted">${received ? "Historical · read only" : "Awaiting quotation"}</span>`}</td></tr>`;
  }

  async function renderSupplierSelection(rfqId) {
    if (!hasPermission("sourcing.manage")) {
      els.content.innerHTML = emptyState("Supplier selection unavailable", "Your account does not have permission to complete sourcing decisions.", "Go to quotations", () => navigate("quotes"));
      return;
    }
    if (!rfqId) {
      els.content.innerHTML = emptyState("No RFQ selected", "Choose an RFQ with recorded supplier quotations before completing supplier selection.", "Go to quotations", () => navigate("quotes"));
      return;
    }
    if (navigator.onLine === false) {
      els.content.innerHTML = emptyState("You're offline", "Supplier selection needs a connection to load the latest sourcing evidence.", "Try again", () => renderSupplierSelection(rfqId));
      return;
    }
    let slowNotice;
    const slowTimer = window.setTimeout(() => {
      slowNotice = document.createElement("div");
      slowNotice.className = "inline-state inline-state--slow";
      slowNotice.innerHTML = "<span>◌</span><div><strong>Still loading supplier selection</strong><small>The connection is taking longer than usual. No sourcing changes have been made.</small></div>";
      els.content.prepend(slowNotice);
    }, 900);
    try {
      const comparison = await api(`/quotations/compare/${rfqId}`);
      let selection = null;
      try { selection = await api(`/supplier-selections/rfq/${rfqId}`); } catch (err) { if (!String(err.message).includes("No supplier has been selected")) throw err; }
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      drawSupplierSelection(comparison, selection);
    } catch (err) {
      window.clearTimeout(slowTimer); if (slowNotice) slowNotice.remove();
      els.content.innerHTML = emptyState("Supplier selection could not be loaded", err.message, "Back to comparison", () => navigate("quotation-comparison"));
    }
  }

  function drawSupplierSelection(comparison, selection) {
    const receivedRows = (comparison.rows || []).filter(row => row.quotation_id != null);
    const pending = comparison.pending_response_count || 0;
    if (selection) {
      els.content.innerHTML = `${pageHeader("SOURCING · DECISION RECORDED", "Supplier Selection", "The sourcing decision for this RFQ has already been recorded.", `<button class="button button--ghost" data-back-comparison>← Back to comparison</button>`)}
        <section class="selection-confirmed panel"><div class="selection-confirmed-icon">✓</div><div><span class="eyebrow">SUPPLIER SELECTED</span><h2>${escapeHTML(selection.supplier_name)}</h2><p>${escapeHTML(selection.supplier_code)} · ${escapeHTML(selection.rfq_number)} · selected ${formatDate(selection.selected_at)}</p></div><span class="status status--success">Recorded</span></section>
        <section class="selection-grid"><article class="panel"><div class="panel-heading"><div><span class="eyebrow">SELECTED COMMERCIALS</span><h2>Quotation evidence</h2><p>The selected supplier's recorded quotation is retained with the sourcing decision.</p></div></div><div class="selection-facts"><span><small>Quoted quantity</small><strong>${escapeHTML(selection.quoted_quantity)}</strong></span><span><small>Unit price</small><strong>${money(selection.unit_price, selection.currency)}</strong></span><span><small>Total</small><strong>${money(selection.total_amount, selection.currency)}</strong></span><span><small>Delivery</small><strong>${escapeHTML(selection.delivery_days)} days</strong></span><span><small>Valid until</small><strong>${requestRequiredDate(selection.valid_until)}</strong></span></div></article><article class="panel"><div class="panel-heading"><div><span class="eyebrow">DECISION RECORD</span><h2>Selection rationale</h2><p>Captured when Procurement completed the sourcing decision.</p></div></div><div class="selection-rationale">${escapeHTML(selection.rationale)}</div></article></section>`;
      els.content.querySelector("[data-back-comparison]")?.addEventListener("click", () => { state.comparisonRfqId = comparison.rfq_id; navigate("quotation-comparison"); });
      return;
    }
    if (!receivedRows.length) {
      els.content.innerHTML = emptyState("No quotations available", "Supplier selection opens after at least one supplier quotation has been recorded for this RFQ.", "Back to comparison", () => navigate("quotation-comparison"));
      return;
    }
    const responseCopy = pending ? `${receivedRows.length} quotation${receivedRows.length === 1 ? "" : "s"} received · ${pending} supplier response${pending === 1 ? "" : "s"} still pending` : `${receivedRows.length} supplier quotation${receivedRows.length === 1 ? "" : "s"} received`;
    els.content.innerHTML = `${pageHeader("SOURCING · DECISION", "Supplier Selection", "Review the recorded commercial evidence and record the supplier chosen by Procurement.", `<button class="button button--ghost" data-back-comparison>← Back to comparison</button>`)}
      <section class="panel selection-context"><div><span class="eyebrow">RFQ ${escapeHTML(comparison.rfq_number)}</span><h2>${escapeHTML(comparison.request_title)}</h2><p>${escapeHTML(comparison.request_number)}${comparison.request_category ? ` · ${escapeHTML(comparison.request_category)}` : ""}</p></div><div class="selection-context-meta"><span class="status status--muted">${escapeHTML(responseCopy)}</span><small>Response deadline · ${formatDate(comparison.response_deadline)}</small></div></section>
      ${pending ? `<section class="inline-state selection-notice"><span>◌</span><div><strong>Some supplier responses are still pending.</strong><small>You can record a selection from the quotations already received. The system will not select a supplier automatically.</small></div></section>` : ""}
      <section class="panel selection-candidates"><div class="panel-heading"><div><span class="eyebrow">ELIGIBLE QUOTATIONS</span><h2>Suppliers with recorded responses</h2><p>Select a supplier only after reviewing the commercial evidence below.</p></div></div><div class="selection-candidate-list">${receivedRows.map(row => `<article class="selection-candidate"><div class="selection-candidate-main"><div class="selection-candidate-title"><span class="selection-avatar">${escapeHTML(initials(row.supplier_name))}</span><div><strong>${escapeHTML(row.supplier_name)}</strong><small>${escapeHTML(row.supplier_code)} · quotation received ${formatDate(row.received_at)}</small></div></div><div class="selection-facts"><span><small>Unit price</small><strong>${money(row.unit_price, row.currency)}</strong></span><span><small>Total</small><strong>${money(row.total_amount, row.currency)}</strong></span><span><small>Delivery</small><strong>${escapeHTML(row.delivery_days)} days</strong></span><span><small>Valid until</small><strong>${requestRequiredDate(row.valid_until)}</strong></span></div></div><button class="button button--primary selection-action" data-select-supplier="${row.rfq_supplier_id}">Select supplier</button></article>`).join("")}</div></section>`;
    els.content.querySelector("[data-back-comparison]")?.addEventListener("click", () => { state.comparisonRfqId = comparison.rfq_id; navigate("quotation-comparison"); });
    els.content.querySelectorAll("[data-select-supplier]").forEach(button => button.addEventListener("click", () => openSupplierSelection(comparison, button.dataset.selectSupplier)));
  }

  function openSupplierSelection(comparison, rfqSupplierId) {
    const row = (comparison.rows || []).find(item => item.rfq_supplier_id === rfqSupplierId && item.quotation_id != null);
    if (!row) return;
    modal({
      title: `Select ${row.supplier_name}`,
      submitLabel: "Confirm selection",
      body: `<div class="quote-context"><span class="eyebrow">RFQ ${escapeHTML(comparison.rfq_number)}</span><strong>${escapeHTML(row.supplier_name)}</strong><small>${escapeHTML(row.supplier_code)} · quotation received ${formatDate(row.received_at)}</small></div><div class="selection-modal-facts"><span><small>Unit price</small><strong>${money(row.unit_price, row.currency)}</strong></span><span><small>Total</small><strong>${money(row.total_amount, row.currency)}</strong></span><span><small>Delivery</small><strong>${escapeHTML(row.delivery_days)} days</strong></span><span><small>Valid until</small><strong>${requestRequiredDate(row.valid_until)}</strong></span></div><label class="field-span-2">Selection rationale<textarea name="rationale" minlength="10" maxlength="2000" required placeholder="Explain why Procurement selected this supplier. Consider specification fit, commercial terms, delivery, quality, or other documented factors."></textarea><small>This decision is retained in the sourcing audit trail.</small></label>`,
      onSubmit: async fd => {
        const rationale = String(fd.get("rationale") || "").trim();
        if (rationale.length < 10) throw new Error("Selection rationale must be at least 10 characters.");
        await api("/supplier-selections", { method: "POST", body: JSON.stringify({ rfq_id: comparison.rfq_id, rfq_supplier_id: rfqSupplierId, rationale }) });
        state.selectionRfqId = comparison.rfq_id;
        toast(`Supplier selected: ${row.supplier_name}.`);
        await renderSupplierSelection(comparison.rfq_id);
      }
    });
  }

  async function loadReceivableOrders() {
    try {
      return await api("/goods-receipts/expected-deliveries");
    } catch (err) {
      return api("/goods-receipts/eligible-orders");
    }
  }

  function receiptStatusPill(status) {
    const map = { DRAFT: ["DRAFT", "amber"], POSTED: ["POSTED", "green"] };
    const [label, tone] = map[status] || [String(status || "UNKNOWN").replaceAll("_", " "), "blue"];
    return `<span class="status status--${tone}">${escapeHTML(label)}</span>`;
  }

  function receivingStatusPill(status) {
    const map = {
      EXPECTED: ["EXPECTED", "blue"],
      PARTIALLY_RECEIVED: ["PARTIALLY RECEIVED", "amber"],
      FULLY_RECEIVED: ["FULLY RECEIVED", "green"],
    };
    const [label, tone] = map[status] || [String(status || "UNKNOWN").replaceAll("_", " "), "blue"];
    return `<span class="status status--${tone}">${escapeHTML(label)}</span>`;
  }

  function openCreateGoodsReceipt(po) {
    if (!po?.items?.length) return toast("This purchase order has no remaining quantities to receive.", "error");
    const itemRows = po.items.map(item => `
      <div class="receiving-line">
        <div class="receiving-line__info"><strong>${escapeHTML(item.name)}</strong><small>Ordered ${escapeHTML(item.ordered_quantity)} · Received ${escapeHTML(item.received_quantity)} · Remaining ${escapeHTML(item.remaining_quantity)}</small></div>
        <label>Receive<input name="received_${item.purchase_order_item_id}" type="number" min="0" max="${escapeHTML(item.remaining_quantity)}" step="0.01" value="${escapeHTML(item.remaining_quantity)}"></label>
        <label>Accept<input name="accepted_${item.purchase_order_item_id}" type="number" min="0" step="0.01" value="${escapeHTML(item.remaining_quantity)}"></label>
        <label>Reject<input name="rejected_${item.purchase_order_item_id}" type="number" min="0" step="0.01" value="0"></label>
        <label class="field-span-2">Rejection reason<input name="reason_${item.purchase_order_item_id}" maxlength="500" placeholder="Required only if rejecting quantity"></label>
      </div>`).join("");
    modal({
      title: `Receive against ${po.po_number}`,
      submitLabel: "Create draft receipt",
      body: `<div class="po-context"><span class="eyebrow">ISSUED PURCHASE ORDER</span><strong>${escapeHTML(po.po_number)} · ${escapeHTML(po.request_number)}</strong><small>${escapeHTML(po.supplier_name)} · ${escapeHTML(po.supplier_code)} · ${escapeHTML(po.currency)}</small></div><div class="form-grid"><label>Receipt date<input name="receipt_date" type="date" required value="${new Date().toISOString().slice(0,10)}"></label><label>Delivery reference<input name="delivery_reference" maxlength="120" placeholder="Supplier delivery note / challan"></label><label class="field-span-2">Notes<textarea name="notes" maxlength="2000" placeholder="Receiving observations, packaging condition, etc."></textarea></label></div><div class="receiving-lines">${itemRows}</div><div class="approval-note">Accepted + rejected quantity must equal received quantity. A rejection reason is required for rejected quantity.</div>`,
      onSubmit: async fd => {
        const items = [];
        for (const item of po.items) {
          const received = Number(fd.get(`received_${item.purchase_order_item_id}`));
          const accepted = Number(fd.get(`accepted_${item.purchase_order_item_id}`));
          const rejected = Number(fd.get(`rejected_${item.purchase_order_item_id}`));
          if (!Number.isFinite(received) || received <= 0) continue;
          if (!Number.isFinite(accepted) || accepted < 0 || !Number.isFinite(rejected) || rejected < 0) throw new Error(`Enter valid accepted/rejected quantities for ${item.name}.`);
          if (Math.abs((accepted + rejected) - received) > 0.0001) throw new Error(`Accepted + rejected must equal received for ${item.name}.`);
          if (received > Number(item.remaining_quantity)) throw new Error(`Receipt quantity for ${item.name} exceeds the remaining quantity.`);
          const reason = String(fd.get(`reason_${item.purchase_order_item_id}`) || "").trim();
          if (rejected > 0 && !reason) throw new Error(`A rejection reason is required for ${item.name}.`);
          items.push({ purchase_order_item_id: item.purchase_order_item_id, received_quantity: received, accepted_quantity: accepted, rejected_quantity: rejected, rejection_reason: reason || null });
        }
        if (!items.length) throw new Error("Receive at least one item quantity.");
        const receipt = await api("/goods-receipts", { method: "POST", body: JSON.stringify({ purchase_order_id: po.purchase_order_id, receipt_date: fd.get("receipt_date"), delivery_reference: String(fd.get("delivery_reference") || "").trim() || null, notes: String(fd.get("notes") || "").trim() || null, items }) });
        state.goodsReceiptId = receipt.id;
        toast(`${receipt.receipt_number} created as a draft receipt.`);
        await navigate("goods-receipt-detail");
      }
    });
  }

  async function renderExpectedDeliveries() {
    if (!canViewReceiving()) { els.content.innerHTML = emptyState("Receiving unavailable", "Your account is not authorized to view receiving activity.", "Go to home", () => navigate("home")); return; }
    try {
      const orders = await loadReceivableOrders();
      const canManage = canManageReceiving();
      const rows = orders.map(po => {
        const searchable = `${po.po_number} ${po.request_number} ${po.supplier_name} ${po.supplier_code}`.toLowerCase();
        const status = po.receiving_status || "EXPECTED";
        return `<tr data-delivery-row data-search="${escapeHTML(searchable)}" data-receiving-status="${escapeHTML(status)}"><td><strong>${escapeHTML(po.po_number)}</strong><small>${escapeHTML(po.request_number)}</small></td><td>${escapeHTML(po.supplier_name)}<small>${escapeHTML(po.supplier_code)}</small></td><td>${po.required_date ? requestRequiredDate(po.required_date) : "Not set"}</td><td>${receivingStatusPill(status)}</td><td>${po.items.length}</td><td>${po.items.reduce((n,i)=>n+Number(i.remaining_quantity),0)}</td><td>${canManage ? `<button class="button button--primary button--small" data-receive-po="${po.purchase_order_id}">Record receipt</button>` : `<span class="muted">View only</span>`}</td></tr>`;
      }).join("");
      els.content.innerHTML = `${pageHeader("RECEIVING", "Expected Deliveries", "Issued purchase orders with quantities still waiting to be received.", `<button class="button button--ghost" data-refresh-deliveries>Refresh</button>`)}
        <section class="metric-grid">${statCard("Open deliveries", orders.length, "Issued POs with remaining quantities", "blue", "◫")}${statCard("Open lines", orders.reduce((n,p)=>n+p.items.length,0), "PO lines awaiting receipt", "amber", "□")}${statCard("Units remaining", orders.reduce((n,p)=>n+p.items.reduce((x,i)=>x+Number(i.remaining_quantity),0),0), "Across open PO lines", "green", "↳")}</section>
        <section class="panel receiving-toolbar"><div class="receiving-toolbar__search"><label>Search receiving queue<input type="search" data-delivery-search placeholder="PO, request, supplier"></label></div><label>Receiving status<select data-delivery-status><option value="ALL">All statuses</option><option value="EXPECTED">Expected</option><option value="PARTIALLY_RECEIVED">Partially received</option></select></label></section>
        ${orders.length ? tablePanel("Receiving queue", "Start a receipt when goods arrive against an issued purchase order.", `<table><thead><tr><th>PO</th><th>Supplier</th><th>Required</th><th>Receiving status</th><th>Open lines</th><th>Remaining qty</th><th></th></tr></thead><tbody>${rows}<tr data-delivery-no-match hidden><td colspan="7"><div class="table-empty">No deliveries match the current search or status filter.</div></td></tr></tbody></table>`) : `<section class="panel empty-state-card"><div class="future-icon">✓</div><h2>No deliveries awaiting receipt</h2><p>Issued purchase orders with outstanding quantities will appear here.</p><span class="pill">Issued PO → Receive → Post</span></section>`}`;
      const applyFilters = () => {
        const query = String(els.content.querySelector("[data-delivery-search]")?.value || "").trim().toLowerCase();
        const status = els.content.querySelector("[data-delivery-status]")?.value || "ALL";
        let visible = 0;
        els.content.querySelectorAll("[data-delivery-row]").forEach(row => {
          const match = (!query || row.dataset.search.includes(query)) && (status === "ALL" || row.dataset.receivingStatus === status);
          row.hidden = !match;
          if (match) visible += 1;
        });
        const empty = els.content.querySelector("[data-delivery-no-match]");
        if (empty) empty.hidden = visible !== 0;
      };
      els.content.querySelector("[data-refresh-deliveries]")?.addEventListener("click", () => renderExpectedDeliveries());
      els.content.querySelector("[data-delivery-search]")?.addEventListener("input", applyFilters);
      els.content.querySelector("[data-delivery-status]")?.addEventListener("change", applyFilters);
      els.content.querySelectorAll("[data-receive-po]").forEach(b => b.addEventListener("click", async () => { try { const po = (await loadReceivableOrders()).find(x=>x.purchase_order_id===b.dataset.receivePo); openCreateGoodsReceipt(po); } catch(err) { toast(err.message,"error"); } }));
      applyFilters();
    } catch (err) { els.content.innerHTML = emptyState("Expected deliveries could not be loaded", err.message, "Try again", () => renderExpectedDeliveries()); }
  }

  async function renderGoodsReceipts() {
    if (!canViewReceiving()) { els.content.innerHTML = emptyState("Goods receipts unavailable", "Your account is not authorized to view receiving documents.", "Go to home", () => navigate("home")); return; }
    try {
      const receipts = await api("/goods-receipts");
      const rows = receipts.map(r => {
        const searchable = `${r.receipt_number} ${r.po_number} ${r.delivery_reference || ""}`.toLowerCase();
        return `<tr data-receipt-row data-search="${escapeHTML(searchable)}" data-receipt-status="${escapeHTML(r.status)}"><td><strong>${escapeHTML(r.receipt_number)}</strong></td><td>${escapeHTML(r.po_number)}</td><td>${requestRequiredDate(r.receipt_date)}</td><td>${receiptStatusPill(r.status)}</td><td>${escapeHTML(r.delivery_reference || "—")}</td><td><button class="button button--ghost button--small" data-open-receipt="${r.id}">Review</button></td></tr>`;
      }).join("");
      els.content.innerHTML = `${pageHeader("RECEIVING", "Goods Receipts", "Receipt history and receiving evidence captured against issued purchase orders.", `<button class="button button--ghost" data-refresh-receipts>Refresh</button>`)}
        <section class="metric-grid">${statCard("Receipts", receipts.length, "Receiving documents", "blue", "▣")}${statCard("Draft", receipts.filter(r=>r.status==="DRAFT").length, "Not yet posted", "amber", "◇")}${statCard("Posted", receipts.filter(r=>r.status==="POSTED").length, "Available as receipt evidence", "green", "✓")}</section>
        <section class="panel receiving-toolbar"><div class="receiving-toolbar__search"><label>Search receipt history<input type="search" data-receipt-search placeholder="Receipt, PO, delivery reference"></label></div><label>Receipt status<select data-receipt-status-filter><option value="ALL">All statuses</option><option value="DRAFT">Draft</option><option value="POSTED">Posted</option></select></label></section>
        ${receipts.length ? tablePanel("Receipt history", "Trace each receipt to its purchase order, receiving date, and posting state.", `<table><thead><tr><th>Receipt</th><th>PO</th><th>Date</th><th>Status</th><th>Delivery reference</th><th></th></tr></thead><tbody>${rows}<tr data-receipt-no-match hidden><td colspan="6"><div class="table-empty">No receipts match the current search or status filter.</div></td></tr></tbody></table>`) : `<section class="panel empty-state-card"><div class="future-icon">▣</div><h2>No goods receipts yet</h2><p>Use Expected Deliveries to record goods received against an issued purchase order.</p>${canManageReceiving() ? `<button class="button button--primary" data-nav="deliveries">Open expected deliveries</button>` : ""}</section>`}`;
      const applyFilters = () => {
        const query = String(els.content.querySelector("[data-receipt-search]")?.value || "").trim().toLowerCase();
        const status = els.content.querySelector("[data-receipt-status-filter]")?.value || "ALL";
        let visible = 0;
        els.content.querySelectorAll("[data-receipt-row]").forEach(row => {
          const match = (!query || row.dataset.search.includes(query)) && (status === "ALL" || row.dataset.receiptStatus === status);
          row.hidden = !match;
          if (match) visible += 1;
        });
        const empty = els.content.querySelector("[data-receipt-no-match]");
        if (empty) empty.hidden = visible !== 0;
      };
      els.content.querySelector("[data-refresh-receipts]")?.addEventListener("click", () => renderGoodsReceipts());
      els.content.querySelector("[data-receipt-search]")?.addEventListener("input", applyFilters);
      els.content.querySelector("[data-receipt-status-filter]")?.addEventListener("change", applyFilters);
      els.content.querySelectorAll("[data-open-receipt]").forEach(b => { b.addEventListener("click", () => { state.goodsReceiptId=b.dataset.openReceipt; navigate("goods-receipt-detail"); }); });
      els.content.querySelector("[data-nav=deliveries]")?.addEventListener("click",()=>navigate("deliveries"));
      applyFilters();
    } catch (err) { els.content.innerHTML = emptyState("Goods receipts could not be loaded", err.message, "Try again", () => renderGoodsReceipts()); }
  }

  async function renderGoodsReceiptDetail(receiptId) {
    if (!canViewReceiving()) { els.content.innerHTML = emptyState("Access restricted", "You do not have permission to view goods receipts.", "Return home", () => navigate("home")); return; }
    if (!receiptId) return navigate("receipts");
    try {
      const receipt = await api(`/goods-receipts/${receiptId}`);
      const canPost = canManageReceiving() && receipt.status === "DRAFT";
      // The history endpoint is PO-scoped; load it using the PO id from the receipt.
      const poHistory = await api(`/goods-receipts/purchase-orders/${receipt.purchase_order_id}/history`).catch(() => []);
      els.content.innerHTML = `${pageHeader("GOODS RECEIPT", receipt.receipt_number, `${receipt.po_number} · ${receipt.receipt_date}`, `<button class="button button--ghost" data-back-receipts>Back to receipts</button>`)}
        <section class="detail-layout"><div class="detail-main"><section class="panel"><div class="panel-heading"><div><span class="eyebrow">RECEIVING EVIDENCE</span><h2>Received quantities</h2><p>Quantities captured for this receiving document.</p></div>${receiptStatusPill(receipt.status)}</div><div class="table-wrap"><table><thead><tr><th>Item</th><th>Received</th><th>Accepted</th><th>Rejected</th><th>Reason</th></tr></thead><tbody>${receipt.items.map(item=>`<tr><td>${escapeHTML(item.item_name || item.purchase_order_item_id)}</td><td>${escapeHTML(item.received_quantity)}</td><td>${escapeHTML(item.accepted_quantity)}</td><td>${escapeHTML(item.rejected_quantity)}</td><td>${escapeHTML(item.rejection_reason || "—")}</td></tr>`).join("")}</tbody></table></div></section>
        <section class="panel"><div class="panel-heading"><div><span class="eyebrow">PURCHASE ORDER HISTORY</span><h2>Receipt history</h2><p>All receiving documents posted or drafted against ${escapeHTML(receipt.po_number)}.</p></div></div>${poHistory.length ? `<div class="table-wrap"><table><thead><tr><th>Receipt</th><th>Date</th><th>Status</th><th>Delivery reference</th></tr></thead><tbody>${poHistory.map(h=>`<tr><td><strong>${escapeHTML(h.receipt_number)}</strong></td><td>${requestRequiredDate(h.receipt_date)}</td><td>${receiptStatusPill(h.status)}</td><td>${escapeHTML(h.delivery_reference || "—")}</td></tr>`).join("")}</tbody></table></div>` : `<div class="table-empty">No receipt history is available for this purchase order.</div>`}</section></div>
        <aside class="detail-side"><section class="panel"><div class="panel-heading"><div><span class="eyebrow">DOCUMENT</span><h2>Receipt details</h2></div></div><div class="detail-facts"><div><span>Purchase order</span><strong>${escapeHTML(receipt.po_number)}</strong></div><div><span>Delivery reference</span><strong>${escapeHTML(receipt.delivery_reference || "—")}</strong></div><div><span>Received by</span><strong>${escapeHTML(receipt.received_by_name || receipt.received_by_user_id)}</strong></div><div><span>Posted</span><strong>${receipt.posted_at ? formatDate(receipt.posted_at) : "Not posted"}</strong></div></div>${receipt.notes ? `<div class="approval-note">${escapeHTML(receipt.notes)}</div>` : ""}${canPost ? `<button class="button button--primary button--full" data-post-receipt title="Post receipt">Post goods receipt</button>` : ""}</section></aside></section>`;
      els.content.querySelector("[data-back-receipts]")?.addEventListener("click",()=>navigate("receipts"));
      els.content.querySelector("[data-post-receipt]")?.addEventListener("click", async () => { const button=els.content.querySelector("[data-post-receipt]"); button.disabled=true; try { await api(`/goods-receipts/${receipt.id}/post`,{method:"POST"}); toast(`${receipt.receipt_number} posted successfully.`); await renderGoodsReceiptDetail(receipt.id); } catch(err) { toast(err.message,"error"); button.disabled=false; } });
    } catch (err) { els.content.innerHTML = emptyState("Goods receipt could not be loaded", err.message, "Back to receipts", () => navigate("receipts")); }
  }

  function invoiceStatusPill(status) {
    const labels = { RECEIVED: "RECEIVED", VALIDATING: "VALIDATING", MATCHING: "MATCHING", EXCEPTION: "EXCEPTION", READY_FOR_PAYMENT: "READY FOR FINANCE", PAID: "PAID" };
    return `<span class="status status--${String(status).toLowerCase()}" title="Invoice processing status">${labels[status] || escapeHTML(status)}</span>`;
  }

  function invoiceDateValue(dateObj = new Date()) {
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, "0");
    const d = String(dateObj.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function invoiceFormLine(poItem) {
    return `<div class="invoice-line" data-invoice-line data-po-item-id="${poItem.purchase_order_item_id}">
      <div><strong>${escapeHTML(poItem.name)}</strong><small>PO quantity ${escapeHTML(poItem.quantity)} · ${money(poItem.unit_price)}</small></div>
      <input name="line_quantity_${poItem.purchase_order_item_id}" type="number" min="0.01" step="0.01" value="${escapeHTML(poItem.quantity)}" required>
      <input name="line_unit_price_${poItem.purchase_order_item_id}" type="number" min="0" step="0.01" value="${escapeHTML(poItem.unit_price)}" required>
      <input name="line_total_${poItem.purchase_order_item_id}" type="number" min="0" step="0.01" value="${escapeHTML(poItem.line_total)}" required>
    </div>`;
  }

  async function renderInvoices() {
    if (!canViewInvoices()) { els.content.innerHTML = emptyState("Invoices unavailable", "Your account is not authorized to view AP invoice activity.", "Go to home", () => navigate("home")); return; }
    try {
      const invoices = await api("/invoices");
      const canCreate = canManageInvoices();
      const rows = invoices.map(i => `<tr data-invoice-row data-search="${escapeHTML(`${i.invoice_number} ${i.po_number} ${i.supplier_name} ${i.supplier_code}`.toLowerCase())}" data-invoice-status="${escapeHTML(i.status)}"><td><strong>${escapeHTML(i.invoice_number)}</strong></td><td>${escapeHTML(i.po_number)}</td><td>${escapeHTML(i.supplier_name)}<small>${escapeHTML(i.supplier_code)}</small></td><td>${formatDate(i.invoice_date)}</td><td>${formatDate(i.due_date)}</td><td><strong>${money(i.total_amount, i.currency)}</strong></td><td>${invoiceStatusPill(i.status)}</td><td><button class="button button--ghost button--small" data-open-invoice="${i.id}">Review</button></td></tr>`).join("");
      els.content.innerHTML = `${pageHeader("ACCOUNTS PAYABLE", "Invoices", "Capture supplier invoices against issued purchase orders and move them through AP intake and validation.", `${canCreate ? `<button class="button button--primary" data-create-invoice>+ Record invoice</button>` : ""}`)}
        <section class="metric-grid">${statCard("Invoices received", invoices.length, "Supplier invoices captured", "blue", "▧")}${statCard("Validating", invoices.filter(i=>i.status==="VALIDATING").length, "Invoices under AP validation", "amber", "◇")}${statCard("Matching", invoices.filter(i=>i.status==="MATCHING").length, "Ready for 3-way matching", "violet", "↔")}${statCard("Exceptions", invoices.filter(i=>i.status==="EXCEPTION").length, "Invoices needing intervention", "red", "△")}</section>
        <section class="panel invoice-toolbar"><div><label>Search invoice history<input type="search" data-invoice-search placeholder="Invoice, PO, supplier"></label></div><label>Invoice status<select data-invoice-status-filter><option value="ALL">All statuses</option><option value="RECEIVED">Received</option><option value="VALIDATING">Validating</option><option value="MATCHING">Matching</option><option value="EXCEPTION">Exception</option><option value="READY_FOR_PAYMENT">Ready for finance</option><option value="PAID">Paid</option></select></label></section>
        ${invoices.length ? tablePanel("AP invoice register", "Trace each supplier invoice to its purchase order, supplier, amount, and processing status.", `<table><thead><tr><th>Invoice</th><th>PO</th><th>Supplier</th><th>Invoice date</th><th>Due date</th><th>Total</th><th>Status</th><th></th></tr></thead><tbody>${rows}<tr data-invoice-no-match hidden><td colspan="8"><div class="table-empty">No invoices match the current search or status filter.</div></td></tr></tbody></table>`) : `<section class="panel empty-state-card"><div class="future-icon">▧</div><h2>No supplier invoices yet</h2><p>Record an invoice against an issued purchase order to begin the AP workflow.</p>${canCreate ? `<button class="button button--primary" data-create-invoice>Record first invoice</button>` : ""}</section>`}`;
      const applyFilters = () => { const q=String(els.content.querySelector("[data-invoice-search]")?.value||"").trim().toLowerCase(); const status=els.content.querySelector("[data-invoice-status-filter]")?.value||"ALL"; let visible=0; els.content.querySelectorAll("[data-invoice-row]").forEach(row=>{const show=(!q||row.dataset.search.includes(q))&&(status==="ALL"||row.dataset.invoiceStatus===status); row.hidden=!show; if(show) visible++;}); const empty=els.content.querySelector("[data-invoice-no-match]"); if(empty) empty.hidden=visible!==0; };
      els.content.querySelector("[data-invoice-search]")?.addEventListener("input", applyFilters);
      els.content.querySelector("[data-invoice-status-filter]")?.addEventListener("change", applyFilters);
      els.content.querySelectorAll("[data-open-invoice]").forEach(b=>b.addEventListener("click",()=>{state.invoiceId=b.dataset.openInvoice; navigate("invoice-detail");}));
      els.content.querySelectorAll("[data-create-invoice]").forEach(b=>b.addEventListener("click", openCreateInvoice));
      applyFilters();
    } catch(err) { els.content.innerHTML = emptyState("Invoices could not be loaded", err.message, "Try again", () => renderInvoices()); }
  }

  async function openCreateInvoice() {
    if (!canManageInvoices()) return toast("You do not have permission to record supplier invoices.", "error");
    try {
      const purchaseOrders = await api("/invoices/purchase-orders");
      if (!purchaseOrders.length) return toast("No issued purchase orders are available for invoice capture.", "error");
      const first = purchaseOrders[0];
      const today = new Date();
      const due = new Date(today); due.setDate(due.getDate() + Number(first.payment_terms_days || 0));
      const poOptions = purchaseOrders.map(po=>`<option value="${po.purchase_order_id}">${escapeHTML(po.po_number)} · ${escapeHTML(po.supplier_name)} · ${money(po.total_amount, po.currency)}</option>`).join("");
      const lineMarkup = first.items.map(invoiceFormLine).join("");
      modal({ title: "Record supplier invoice", submitLabel: "Record invoice", body: `<div class="invoice-context"><span class="eyebrow">AP INTAKE</span><strong>Supplier invoice</strong><small>Capture the supplier document without performing the 3-way match yet.</small></div><div class="form-grid"><label>Invoice number<input name="invoice_number" required maxlength="80" placeholder="INV-2026-001"></label><label>Purchase order<select name="purchase_order_id" data-invoice-po required>${poOptions}</select></label><label>Invoice date<input name="invoice_date" type="date" value="${invoiceDateValue(today)}" required></label><label>Due date<input name="due_date" type="date" value="${invoiceDateValue(due)}" required></label><label>Currency<input name="currency" data-invoice-currency value="${escapeHTML(first.currency)}" minlength="3" maxlength="3" required></label><label>Tax amount<input name="tax_amount" data-invoice-tax type="number" min="0" step="0.01" value="${(Number(first.total_amount)-first.items.reduce((s,i)=>s+Number(i.line_total),0)).toFixed(2)}" required></label><label>Subtotal<input name="subtotal" data-invoice-subtotal type="number" min="0" step="0.01" value="${escapeHTML(first.items.reduce((s,i)=>s+Number(i.line_total),0).toFixed(2))}" required></label><label>Total<input name="total_amount" data-invoice-total type="number" min="0" step="0.01" value="${Number(first.total_amount).toFixed(2)}" required></label></div><section class="invoice-lines-panel"><div class="panel-heading"><div><span class="eyebrow">INVOICE LINES</span><h3>PO-backed line items</h3><p>Each invoice line remains traceable to a purchase-order line for 3-way matching.</p></div></div><div class="invoice-lines" data-invoice-lines>${lineMarkup}</div></section><label class="field-span-2">Notes<textarea name="notes" maxlength="2000" placeholder="Optional AP intake notes"></textarea></label>`, onSubmit: async fd => {
        const po = purchaseOrders.find(x=>x.purchase_order_id===fd.get("purchase_order_id"));
        const items = po.items.map(item=>({ purchase_order_item_id:item.purchase_order_item_id, description:item.name, quantity:Number(fd.get(`line_quantity_${item.purchase_order_item_id}`)), unit_price:Number(fd.get(`line_unit_price_${item.purchase_order_item_id}`)), line_total:Number(fd.get(`line_total_${item.purchase_order_item_id}`)) }));
        const invoice = await api("/invoices", {method:"POST", body:JSON.stringify({ invoice_number:String(fd.get("invoice_number")).trim(), vendor_id:po.vendor_id, purchase_order_id:po.purchase_order_id, invoice_date:fd.get("invoice_date"), due_date:fd.get("due_date"), currency:String(fd.get("currency")).toUpperCase(), subtotal:Number(fd.get("subtotal")), tax_amount:Number(fd.get("tax_amount")), total_amount:Number(fd.get("total_amount")), notes:String(fd.get("notes")||"").trim()||null, items })});
        state.invoiceId=invoice.id; toast(`${invoice.invoice_number} received into AP.`); await navigate("invoice-detail");
      }});
      const poSelect=els.modalRoot.querySelector("[data-invoice-po]");
      const refreshLines=()=>{const po=purchaseOrders.find(x=>x.purchase_order_id===poSelect.value); if(!po)return; els.modalRoot.querySelector("[data-invoice-lines]").innerHTML=po.items.map(invoiceFormLine).join(""); els.modalRoot.querySelector("[data-invoice-currency]").value=po.currency; const subtotal=po.items.reduce((s,i)=>s+Number(i.line_total),0).toFixed(2); els.modalRoot.querySelector("[data-invoice-subtotal]").value=subtotal; els.modalRoot.querySelector("[data-invoice-tax]").value=(Number(po.total_amount)-Number(subtotal)).toFixed(2); els.modalRoot.querySelector("[data-invoice-total]").value=(Number(subtotal)+Number(els.modalRoot.querySelector("[data-invoice-tax]").value||0)).toFixed(2); };
      poSelect?.addEventListener("change",()=>{
        refreshLines();
        const po=purchaseOrders.find(x=>x.purchase_order_id===poSelect.value);
        if (!po) return;
        const dueDate=new Date(); dueDate.setDate(dueDate.getDate()+Number(po.payment_terms_days||0));
        els.modalRoot.querySelector("[name=due_date]").value=invoiceDateValue(dueDate);
      });
      els.modalRoot.querySelector("[data-invoice-tax]")?.addEventListener("input",()=>{const subtotal=Number(els.modalRoot.querySelector("[data-invoice-subtotal]").value||0); const tax=Number(els.modalRoot.querySelector("[data-invoice-tax]").value||0); els.modalRoot.querySelector("[data-invoice-total]").value=(subtotal+tax).toFixed(2);});
    } catch(err) { toast(err.message,"error"); }
  }

  async function renderInvoiceDetail(invoiceId) {
    if (!canViewInvoices()) { els.content.innerHTML = emptyState("Invoice unavailable", "Your account is not authorized to view supplier invoices.", "Go to home", () => navigate("home")); return; }
    if (!invoiceId) return navigate("invoices");
    try {
      const invoice=await api(`/invoices/${invoiceId}`);
      const canValidate=canManageInvoices() && invoice.status === "RECEIVED";
      const canSendToMatching=canManageInvoices() && invoice.status === "VALIDATING";
      els.content.innerHTML=`${pageHeader("ACCOUNTS PAYABLE", invoice.invoice_number, `${invoice.po_number} · ${invoice.supplier_name}`, `<button class="button button--ghost" data-back-invoices>Back to invoices</button>`)}
        <section class="detail-layout"><div class="detail-main"><section class="panel"><div class="panel-heading"><div><span class="eyebrow">INVOICE EVIDENCE</span><h2>Invoice lines</h2><p>Supplier invoice values captured against the purchase-order lines.</p></div>${invoiceStatusPill(invoice.status)}</div><div class="table-wrap"><table><thead><tr><th>Item</th><th>Quantity</th><th>Unit price</th><th>Line total</th></tr></thead><tbody>${invoice.items.map(i=>`<tr><td>${escapeHTML(i.description)}</td><td>${escapeHTML(i.quantity)}</td><td>${money(i.unit_price, invoice.currency)}</td><td>${money(i.line_total, invoice.currency)}</td></tr>`).join("")}</tbody></table></div></section><section class="panel"><div class="panel-heading"><div><span class="eyebrow">COMMERCIAL TOTALS</span><h2>Invoice amount</h2><p>Captured supplier document totals; matching is a separate control.</p></div></div><div class="detail-facts detail-facts--grid"><div><span>Subtotal</span><strong>${money(invoice.subtotal,invoice.currency)}</strong></div><div><span>Tax</span><strong>${money(invoice.tax_amount,invoice.currency)}</strong></div><div><span>Total</span><strong>${money(invoice.total_amount,invoice.currency)}</strong></div><div><span>Due date</span><strong>${formatDate(invoice.due_date)}</strong></div></div></section></div><aside class="detail-side"><section class="panel"><div class="panel-heading"><div><span class="eyebrow">AP WORKFLOW</span><h2>Processing state</h2></div></div><div class="detail-facts"><div><span>Supplier</span><strong>${escapeHTML(invoice.supplier_name)}</strong></div><div><span>PO</span><strong>${escapeHTML(invoice.po_number)}</strong></div><div><span>Invoice date</span><strong>${formatDate(invoice.invoice_date)}</strong></div><div><span>Status</span><strong>${invoiceStatusPill(invoice.status)}</strong></div><div><span>Validated</span><strong>${invoice.validated_at ? formatDate(invoice.validated_at) : "Not yet"}</strong></div></div>${invoice.notes?`<div class="approval-note">${escapeHTML(invoice.notes)}</div>`:""}${canValidate?`<button class="button button--primary button--full" data-validate-invoice>Validate invoice</button>`:""}${canSendToMatching?`<button class="button button--primary button--full" data-send-matching>Send to 3-way matching</button>`:""}</section></aside></section>`;
      els.content.querySelector("[data-back-invoices]")?.addEventListener("click",()=>navigate("invoices"));
      els.content.querySelector("[data-validate-invoice]")?.addEventListener("click",async b=>{b.disabled=true;try{await api(`/invoices/${invoice.id}/validate`,{method:"POST"});toast(`${invoice.invoice_number} moved to validation.`);await renderInvoiceDetail(invoice.id);}catch(err){toast(err.message,"error");b.disabled=false;}});
      els.content.querySelector("[data-send-matching]")?.addEventListener("click",async b=>{b.disabled=true;try{await api(`/invoices/${invoice.id}/send-to-matching`,{method:"POST"});toast(`${invoice.invoice_number} is ready for 3-way matching.`);await renderInvoiceDetail(invoice.id);}catch(err){toast(err.message,"error");b.disabled=false;}});
    } catch(err) { els.content.innerHTML=emptyState("Invoice could not be loaded",err.message,"Back to invoices",()=>navigate("invoices")); }
  }

  async function renderPurchaseOrders() {
    if (!hasPermission("sourcing.manage")) {
      els.content.innerHTML = emptyState("Access restricted", "You do not have permission to manage purchase orders.", "Return home", () => navigate("home"));
      return;
    }
    try {
      const [orders, selections] = await Promise.all([api("/purchase-orders"), api("/supplier-selections")]);
      const requestResults = await Promise.all((selections || []).map(async selection => {
        try { return [selection.request_id, await api(`/purchase-requests/${selection.request_id}`)]; } catch { return [selection.request_id, null]; }
      }));
      const requestMap = Object.fromEntries(requestResults);
      const orderSelectionIds = new Set((orders || []).map(po => po.supplier_selection_id));
      const ready = (selections || []).filter(s => requestMap[s.request_id]?.status === "APPROVED" && !orderSelectionIds.has(s.id));
      els.content.innerHTML = `${pageHeader("PURCHASING", "Purchase Orders", "Create and review purchasing documents generated from approved supplier selections.", `<button class="button button--ghost" data-refresh-po>Refresh</button>`)}
        <div class="metrics-grid">
          ${statCard("Purchase orders", orders.length, "Generated purchasing documents", "blue", "◈")}
          ${statCard("Draft", orders.filter(po => po.status === "DRAFT").length, "Awaiting review", "amber", "◇")}
          ${statCard("Ready to issue", orders.filter(po => po.status === "PENDING_RELEASE").length, "Ready to be formally issued", "violet", "◌")}
          ${statCard("Ready to create", ready.length, "Approved selections without a PO", "green", "✓")}
          ${statCard("Issued", orders.filter(po => po.status === "ISSUED").length, "Released to suppliers", "violet", "↗")}
        </div>
        ${orders.length ? tablePanel("Purchase order register", "Live purchasing documents and their commercial traceability.", `<table><thead><tr><th>PO</th><th>Request</th><th>Supplier</th><th>Total</th><th>Required</th><th>Status</th><th></th></tr></thead><tbody>${orders.map(po => `<tr><td><strong>${escapeHTML(po.po_number)}</strong></td><td>${escapeHTML(po.request_number)}</td><td>${escapeHTML(po.supplier_name)}<small>${escapeHTML(po.supplier_code)}</small></td><td><strong>${money(po.total_amount, po.currency)}</strong></td><td>${formatDate(po.required_date)}</td><td><span class="status status--${String(po.status).toLowerCase()}" title="${escapeHTML(po.status === "PENDING_RELEASE" ? "PO is ready to be formally issued to the supplier." : po.status === "DRAFT" ? "PO is being prepared." : po.status === "ISSUED" ? "PO has been formally issued to the supplier." : "")}">${escapeHTML(po.status === "PENDING_RELEASE" ? "READY TO ISSUE" : po.status.replaceAll("_", " "))}</span></td><td><button class="button button--ghost button--small" data-open-po="${po.id}">Review</button></td></tr>`).join("")}</tbody></table>`) : `<section class="panel empty-state-card"><div class="future-icon">◈</div><h2>No purchase orders yet</h2><p>Purchase orders appear here after an approved supplier selection is converted into a purchasing document.</p><span class="pill">Approved sourcing → PO</span></section>`}
        ${ready.length ? tablePanel("Approved selections ready for PO", "These supplier selections have completed the mandatory approval chain and can now enter purchasing.", `<table><thead><tr><th>Request</th><th>Supplier</th><th>Quoted total</th><th>Delivery</th><th></th></tr></thead><tbody>${ready.map(s => `<tr><td><strong>${escapeHTML(s.request_number)}</strong><small>${escapeHTML(s.request_title)}</small></td><td>${escapeHTML(s.supplier_name)}<small>${escapeHTML(s.supplier_code)}</small></td><td><strong>${money(s.total_amount, s.currency)}</strong></td><td>${escapeHTML(s.delivery_days)} days</td><td><button class="button button--primary button--small" data-create-po="${s.id}">Create PO</button></td></tr>`).join("")}</tbody></table>`) : `<section class="panel compact-empty"><strong>No approved selections are waiting for PO creation.</strong><p>Complete sourcing and the mandatory approval chain before purchasing begins.</p></section>`}`;
      els.content.querySelector("[data-refresh-po]")?.addEventListener("click", () => renderPurchaseOrders());
      els.content.querySelectorAll("[data-open-po]").forEach(b => b.addEventListener("click", () => { state.purchaseOrderId = b.dataset.openPo; navigate("purchase-order-detail"); }));
      els.content.querySelectorAll("[data-create-po]").forEach(b => b.addEventListener("click", () => openCreatePurchaseOrder(b.dataset.createPo)));
    } catch (err) {
      els.content.innerHTML = emptyState("Purchase orders could not be loaded", err.message, "Try again", () => renderPurchaseOrders());
    }
  }

  async function openCreatePurchaseOrder(selectionId) {
    try {
      const selection = await api(`/supplier-selections/${selectionId}`);
      const request = await api(`/purchase-requests/${selection.request_id}`);
      if (request.status !== "APPROVED") throw new Error(`This purchase request is not approved (current status: ${request.status}).`);
      modal({
        title: `Create ${selection.request_number} purchase order`, submitLabel: "Create draft PO",
        body: `<div class="po-context"><span class="eyebrow">APPROVED REQUEST</span><strong>${escapeHTML(selection.request_number)} · ${escapeHTML(selection.request_title)}</strong><small>${escapeHTML(selection.supplier_name)} · ${escapeHTML(selection.supplier_code)}</small></div><div class="po-commercial-grid"><span><small>Currency</small><strong>${escapeHTML(selection.currency)}</strong></span><span><small>Quoted total</small><strong>${money(selection.total_amount, selection.currency)}</strong></span><span><small>Delivery</small><strong>${escapeHTML(selection.delivery_days)} days</strong></span><span><small>Valid until</small><strong>${formatDate(selection.valid_until)}</strong></span></div><div class="po-field-block"><div class="po-field-heading"><div><label for="po-payment-terms">Payment terms</label><small>Days from supplier invoice / agreed payment trigger.</small></div><span class="po-field-badge">Required</span></div><div class="po-input-with-suffix"><input id="po-payment-terms" name="payment_terms_days" type="number" min="0" max="3650" value="30" required aria-describedby="po-payment-terms-help"><span>days</span></div><small id="po-payment-terms-help" class="po-field-help">Use the agreed commercial payment period for this supplier.</small></div><div class="po-field-block po-notes-field"><div class="po-field-heading"><div><label for="po-purchasing-notes">Purchasing notes</label><small>Optional instructions for the purchasing team.</small></div><span class="po-field-badge po-field-badge--optional">Optional</span></div><textarea id="po-purchasing-notes" name="notes" maxlength="2000" rows="4" placeholder="Add internal instructions, delivery coordination notes, or other purchasing context…" aria-describedby="po-purchasing-notes-help"></textarea><div class="po-field-meta"><small id="po-purchasing-notes-help">Supplier and commercial facts are inherited from the selected quotation and cannot be changed here.</small><span>Max 2,000 characters</span></div></div>`,
        onSubmit: async fd => { const paymentTermsDays = Number.parseInt(String(fd.get("payment_terms_days") ?? ""), 10); if (!Number.isInteger(paymentTermsDays) || paymentTermsDays < 0 || paymentTermsDays > 3650) throw new Error("Payment terms must be between 0 and 3650 days."); const po = await api("/purchase-orders", { method: "POST", body: JSON.stringify({ supplier_selection_id: selectionId, payment_terms_days: paymentTermsDays, notes: String(fd.get("notes") || "").trim() || null }) }); state.purchaseOrderId = po.id; toast(`${po.po_number} created as draft · ${po.payment_terms_days} day payment terms.`); await navigate("purchase-order-detail"); }
      });
    } catch (err) { toast(err.message, "error"); }
  }

  async function renderPurchaseOrderDetail(poId) {
    if (!hasPermission("sourcing.manage")) { els.content.innerHTML = emptyState("Access restricted", "You do not have permission to view purchase orders.", "Return home", () => navigate("home")); return; }
    if (!poId) { els.content.innerHTML = emptyState("No purchase order selected", "Choose a purchase order from the Purchasing workspace.", "Back to purchasing", () => navigate("purchase-orders")); return; }
    try {
      const po = await api(`/purchase-orders/${poId}`);
      els.content.innerHTML = `${pageHeader("PURCHASE ORDER", po.po_number, "Purchasing document generated from an approved supplier selection.", `<div class="po-detail-actions"><button class="button button--ghost" data-back-po>Back to purchase orders</button>${(po.status === "DRAFT" || (po.status === "PENDING_RELEASE" && hasRole("PROCUREMENT_HEAD"))) ? `<button class="button button--ghost" data-edit-po-terms>Correct payment terms</button>` : ""}${po.status === "DRAFT" ? `<button class="button button--primary" data-submit-po-release>Submit for release</button>` : ""}${po.status === "PENDING_RELEASE" && hasRole("PROCUREMENT_HEAD") ? `<button class="button button--primary" data-release-po>Issue PO</button>` : ""}${po.status === "ISSUED" && hasPermission("sourcing.manage") && po.supplier_notification_status !== "SENT" ? `<button class="button button--ghost" data-retry-po-notification>${po.supplier_notification_status === "FAILED" ? "Retry supplier email" : "Send to supplier"}</button>` : ""}</div>`)}
        <div class="po-detail-grid"><section class="panel"><div class="panel-heading"><div><span class="eyebrow">DOCUMENT STATUS</span><h2><span class="status status--${String(po.status).toLowerCase()}">${escapeHTML(po.status === "PENDING_RELEASE" ? "READY TO ISSUE" : po.status.replaceAll("_", " "))}</span></h2><p>${escapeHTML(po.status === "PENDING_RELEASE" ? "This PO has completed review and is awaiting formal issue to the supplier." : po.status === "DRAFT" ? "This PO is being prepared for release." : po.status === "ISSUED" ? "This PO has been formally issued to the supplier." : "")}</p>${po.status === "ISSUED" ? `<div class="po-notification-status po-notification-status--${escapeHTML(String(po.supplier_notification_status || "NOT_SENT").toLowerCase())}"><strong>Supplier notification:</strong> ${escapeHTML(po.supplier_notification_status === "SENT" ? `Sent ${po.supplier_notification_sent_at ? formatDate(po.supplier_notification_sent_at) : ""}` : po.supplier_notification_status === "FAILED" ? "Not sent — delivery failed. You can retry." : "Pending")}</div>` : ""}<p>PO date ${formatDate(po.po_date)} · Required ${formatDate(po.required_date)}</p></div></div><div class="po-facts"><span><small>Supplier</small><strong>${escapeHTML(po.supplier_name)}</strong><em>${escapeHTML(po.supplier_code)}</em></span><span><small>Request</small><strong>${escapeHTML(po.request_number)}</strong></span><span><small>Currency</small><strong>${escapeHTML(po.currency)}</strong></span><span><small>Delivery</small><strong>${escapeHTML(po.delivery_days)} days</strong></span><span><small>Payment terms</small><strong>${escapeHTML(po.payment_terms_days)} days</strong></span></div></section><section class="panel"><div class="panel-heading"><div><span class="eyebrow">COMMERCIAL EVIDENCE</span><h2>Selected quotation</h2><p>The values below are inherited from the supplier quotation.</p></div></div><div class="po-total-card"><small>Total</small><strong>${money(po.total_amount, po.currency)}</strong><span>Subtotal ${money(po.subtotal, po.currency)} · Tax ${money(po.tax_amount, po.currency)}</span></div></section></div>
        <section class="panel table-panel"><div class="panel-heading"><div><span class="eyebrow">LINE ITEMS</span><h2>Purchase order items</h2><p>Request and quotation evidence carried into the purchasing document.</p></div></div><div class="table-wrap"><table><thead><tr><th>Item</th><th>Quantity</th><th>Unit price</th><th>Line total</th><th>Specifications</th></tr></thead><tbody>${po.items.map(item => `<tr><td><strong>${escapeHTML(item.name)}</strong><small>${escapeHTML(item.description || "")}</small></td><td>${escapeHTML(item.quantity)}</td><td>${money(item.unit_price, po.currency)}</td><td><strong>${money(item.line_total, po.currency)}</strong></td><td>${item.specifications ? escapeHTML(item.specifications.notes || Object.entries(item.specifications).map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : value}`).join(" · ")) : "—"}</td></tr>`).join("")}</tbody></table></div></section>
        <section class="panel po-trace"><div class="panel-heading"><div><span class="eyebrow">TRACEABILITY</span><h2>Procurement chain</h2><p>This PO is downstream of the sourcing and approval evidence already completed.</p></div></div><div class="po-chain"><span>Purchase Request</span><b>→</b><span>RFQ</span><b>→</b><span>Supplier Quotation</span><b>→</b><span>Supplier Selection</span><b>→</b><span>Mandatory Approvals</span><b>→</b><strong>Purchase Order</strong></div>${po.notes ? `<div class="po-notes"><small>Purchasing notes</small><p>${escapeHTML(po.notes)}</p></div>` : ""}</section>`;
      els.content.querySelector("[data-back-po]")?.addEventListener("click", () => navigate("purchase-orders"));
      els.content.querySelector("[data-edit-po-terms]")?.addEventListener("click", () => modal({
        title: `Correct payment terms — ${po.po_number}`, submitLabel: "Save audited correction",
        body: `<div class="approval-note">Correction available before issuance only. The original PO and correction will be retained in the audit trail.</div><label>Payment terms (days)<input type="number" name="payment_terms_days" min="0" max="3650" value="${po.payment_terms_days}" required></label><label>Reason for change<textarea name="explanation" minlength="10" maxlength="500" required placeholder="Explain the supplier agreement / correction"></textarea></label>`,
        onSubmit: async fd => { await api(`/purchase-orders/${po.id}/payment-terms`, { method: "PATCH", body: JSON.stringify({payment_terms_days: Number(fd.get("payment_terms_days")), explanation: String(fd.get("explanation")).trim()}) }); toast("Payment terms corrected and audited."); await renderPurchaseOrderDetail(po.id); }
      }));
      els.content.querySelector("[data-submit-po-release]")?.addEventListener("click", () => openPurchaseOrderTransition(po.id, "submit-release"));
      els.content.querySelector("[data-release-po]")?.addEventListener("click", () => openPurchaseOrderTransition(po.id, "release"));
      els.content.querySelector("[data-retry-po-notification]")?.addEventListener("click", () => {
        const actionLabel = po.supplier_notification_status === "FAILED" ? "Retry supplier email" : "Send to supplier";
        modal({
          title: po.supplier_notification_status === "FAILED" ? "Retry supplier notification?" : "Send purchase order to supplier?",
          submitLabel: actionLabel,
          body: `<div class="po-transition-callout"><strong>${po.supplier_notification_status === "FAILED" ? "Retry the supplier PO email." : "Send this issued purchase order to the supplier."}</strong><p>The email will be sent to <strong>${escapeHTML(po.supplier_name)}</strong>.. The PO itself is already issued and will not change state.</p></div>`,
          onSubmit: async () => {
            const button = els.content.querySelector("[data-retry-po-notification]");
            if (button) button.disabled = true;
            const result = await api(`/purchase-orders/${po.id}/notify-supplier`, { method: "POST" });
            toast(result.supplier_notification_status === "SENT" ? "Supplier PO email sent successfully." : "Supplier PO email could not be sent.", result.supplier_notification_status === "SENT" ? "success" : "error");
            await renderPurchaseOrderDetail(po.id);
          }
        });
      });
    } catch (err) { els.content.innerHTML = emptyState("Purchase order could not be loaded", err.message, "Back to purchasing", () => navigate("purchase-orders")); }
  }

  function openPurchaseOrderTransition(poId, action) {
    const isRelease = action === "release";
    const title = isRelease ? "Issue purchase order?" : "Submit purchase order for release?";
    const body = isRelease
      ? `<div class="po-transition-callout"><strong>Issue this purchase order to the supplier.</strong><p>This is the final purchasing action. Once issued, the PO becomes an active purchasing document and the issue time is recorded in the audit trail.</p></div>`
      : `<div class="po-transition-callout"><strong>Move this draft into release review.</strong><p>The PO will become read-only for the release step and remain pending until an authorized procurement user issues it.</p></div>`;
    modal({
      title, submitLabel: isRelease ? "Issue PO" : "Submit for release",
      body,
      onSubmit: async () => {
        const po = await api(`/purchase-orders/${poId}/${action}`, { method: "POST" });
        toast(isRelease ? `${po.po_number} issued successfully.` : `${po.po_number} submitted for release.`);
        await navigate("purchase-order-detail", { po: po.id });
      }
    });
  }

  function matchResultPill(result) {
    const meta = result === "MATCHED" ? ["MATCHED", "green"] : ["EXCEPTION", "red"];
    return `<span class="status status--${meta[1]}" title="3-way match result">${meta[0]}</span>`;
  }

  function matchCheck(label, pass, detail) {
    return `<div class="match-check match-check--${pass ? "pass" : "fail"}"><span>${pass ? "✓" : "!"}</span><div><strong>${escapeHTML(label)}</strong><small>${escapeHTML(detail)}</small></div></div>`;
  }

  async function renderThreeWayMatching() {
    if (!canViewInvoices()) { els.content.innerHTML = emptyState("Matching unavailable", "Your account is not authorized to review invoice matching.", "Go to home", () => navigate("home")); return; }
    try {
      const queue = await api("/invoice-matching");
      const matchedCount = 0;
      els.content.innerHTML = `${pageHeader("ACCOUNTS PAYABLE", "3-Way Matching", "Compare purchase order, goods receipt, and supplier invoice evidence before finance finalization.", `<button class="button button--ghost" data-refresh-matching>Refresh</button>`)}
        <section class="metric-grid">
          ${statCard("Ready for matching", queue.length, "Invoices awaiting evaluation", "violet", "↔")}
          ${statCard("Exact controls", queue.length, "Quantity and price checked", "blue", "✓")}
          ${statCard("Exceptions", matchedCount, "New match exceptions", "red", "△")}
        </section>
        ${queue.length ? tablePanel("Matching queue", "Invoices in MATCHING are evaluated against their purchase order and posted goods receipts.", `<table><thead><tr><th>Invoice</th><th>PO</th><th>Supplier</th><th>Invoice date</th><th>Total</th><th>Status</th><th></th></tr></thead><tbody>${queue.map(i=>`<tr><td><strong>${escapeHTML(i.invoice_number)}</strong></td><td>${escapeHTML(i.po_number)}</td><td>${escapeHTML(i.supplier_name)}</td><td>${formatDate(i.invoice_date)}</td><td><strong>${money(i.total_amount,i.currency)}</strong></td><td><span class="status status--violet">MATCHING</span></td><td><button class="button button--primary button--small" data-open-matching="${i.invoice_id}">Review match</button></td></tr>`).join("")}</tbody></table>`) : `<section class="panel empty-state-card"><div class="future-icon">↔</div><h2>No invoices awaiting matching</h2><p>Invoices enter this queue after AP validation. The next step is to compare PO, receipt, and invoice evidence.</p><span class="pill">PO + Receipt + Invoice</span></section>`}`;
      els.content.querySelector("[data-refresh-matching]")?.addEventListener("click", renderThreeWayMatching);
      els.content.querySelectorAll("[data-open-matching]").forEach(b=>b.addEventListener("click",()=>{state.matchingInvoiceId=b.dataset.openMatching;navigate("matching-detail");}));
    } catch (err) { els.content.innerHTML = emptyState("Matching queue could not be loaded", err.message, "Try again", () => renderThreeWayMatching()); }
  }

  async function renderThreeWayMatchingDetail(invoiceId) {
    if (!canViewInvoices()) { els.content.innerHTML = emptyState("Matching unavailable", "Your account is not authorized to review invoice matching.", "Go to home", () => navigate("home")); return; }
    if (!invoiceId) return navigate("matching");
    try {
      const [invoice, match] = await Promise.all([api(`/invoices/${invoiceId}`), api(`/invoice-matching/${invoiceId}`)]);
      const canRun = canManageInvoices() && invoice.status === "MATCHING";
      const lineResults = match?.line_results || [];
      const checks = lineResults.length ? lineResults.map(line => `
        <div class="match-line-card">
          <div class="match-line-title"><div><span class="eyebrow">PO LINE</span><strong>${escapeHTML(line.description)}</strong></div><span class="match-line-result">${line.quantity_pass && line.receipt_pass && line.price_pass ? "MATCH" : "VARIANCE"}</span></div>
          <div class="match-evidence-grid">
            <div><span>PO</span><strong>${escapeHTML(line.po_quantity)} × ${money(line.po_unit_price, invoice.currency)}</strong></div>
            <div><span>Receipt</span><strong>${escapeHTML(line.accepted_quantity)} accepted / ${escapeHTML(line.received_quantity)} received</strong></div>
            <div><span>Invoice</span><strong>${escapeHTML(line.invoice_quantity)} × ${money(line.invoice_unit_price, invoice.currency)}</strong></div>
          </div>
          <div class="match-checks">${matchCheck("Quantity vs PO", line.quantity_pass, `Variance ${line.quantity_variance}`)}${matchCheck("Quantity vs receipt", line.receipt_pass, `Accepted quantity ${line.accepted_quantity}`)}${matchCheck("Unit price", line.price_pass, `Variance ${money(line.price_variance, invoice.currency)}`)}</div>
        </div>`).join("") : `<div class="inline-state"><span>↔</span><div><strong>Ready to evaluate</strong><small>Run the match to compare the current PO, posted receipts, and invoice.</small></div></div>`;
      const resultBlock = match ? `<section class="panel match-result-panel match-result-panel--${match.result === "MATCHED" ? "pass" : "fail"}"><div class="panel-heading"><div><span class="eyebrow">MATCH RESULT</span><h2>${match.result === "MATCHED" ? "Ready for finance finalization" : "Match exception"}</h2><p>${escapeHTML(match.exception_reason || "All configured 3-way controls passed.")}</p></div>${matchResultPill(match.result)}</div><div class="match-summary-grid"><div><span>PO quantity</span><strong>${match.po_quantity}</strong></div><div><span>Accepted receipt</span><strong>${match.accepted_quantity}</strong></div><div><span>Invoice quantity</span><strong>${match.invoice_quantity}</strong></div><div><span>Price variance</span><strong>${money(match.price_variance, invoice.currency)}</strong></div></div></section>` : "";
      els.content.innerHTML = `${pageHeader("3-WAY MATCHING", invoice.invoice_number, `${invoice.po_number} · ${invoice.supplier_name}`, `<button class="button button--ghost" data-back-matching>Back to matching</button>`)}
        ${resultBlock}
        <section class="match-three-column">
          <article class="panel match-source-card"><span class="eyebrow">PURCHASE ORDER</span><h2>${escapeHTML(invoice.po_number)}</h2><p>${escapeHTML(invoice.supplier_name)}</p><div class="detail-facts"><div><span>Invoice-linked PO</span><strong>${escapeHTML(invoice.po_number)}</strong></div><div><span>Currency</span><strong>${escapeHTML(invoice.currency)}</strong></div></div></article>
          <article class="panel match-source-card"><span class="eyebrow">GOODS RECEIPT</span><h2>Posted evidence</h2><p>Accepted quantities are the billable receiving evidence.</p><div class="detail-facts"><div><span>Receipt state</span><strong>POSTED</strong></div><div><span>Control</span><strong>Accepted quantity</strong></div></div></article>
          <article class="panel match-source-card"><span class="eyebrow">SUPPLIER INVOICE</span><h2>${escapeHTML(invoice.invoice_number)}</h2><p>${escapeHTML(invoice.supplier_name)}</p><div class="detail-facts"><div><span>Total</span><strong>${money(invoice.total_amount,invoice.currency)}</strong></div><div><span>Status</span><strong>${invoiceStatusPill(invoice.status)}</strong></div></div></article>
        </section>
        <section class="panel match-lines-panel"><div class="panel-heading"><div><span class="eyebrow">CONTROL EVIDENCE</span><h2>Line-by-line comparison</h2><p>Quantity is checked against both the PO and accepted receipt; unit price is checked against the PO.</p></div>${canRun ? `<button class="button button--primary" data-run-match>Run 3-way match</button>` : ""}</div><div class="match-lines">${checks}</div></section>`;
      els.content.querySelector("[data-back-matching]")?.addEventListener("click",()=>navigate("matching"));
      els.content.querySelector("[data-run-match]")?.addEventListener("click",async b=>{b.disabled=true;try{await api(`/invoice-matching/${invoice.id}/run`,{method:"POST"});toast(`${invoice.invoice_number} match evaluated.`);await renderThreeWayMatchingDetail(invoice.id);}catch(err){toast(err.message,"error");b.disabled=false;}});
    } catch (err) { els.content.innerHTML = emptyState("Matching record could not be loaded", err.message, "Back to matching", () => navigate("matching")); }
  }

  async function renderPaymentFinalization() {
    if (!canFinalizePayment()) { els.content.innerHTML = emptyState("Payment controls unavailable", "Your account is not authorized to finalize supplier payments.", "Go to home", () => navigate("home")); return; }
    try {
      const queue = await api("/invoice-matching/payment-queue");
      const ready = queue.filter(i => i.status === "READY_FOR_PAYMENT");
      const paid = queue.filter(i => i.status === "PAID");
      const rows = queue.map(i => `<tr><td><strong>${escapeHTML(i.invoice_number)}</strong><small class="table-subline">${escapeHTML(i.supplier_name)}</small></td><td>${escapeHTML(i.po_number)}</td><td>${money(i.total_amount, i.currency)}</td><td>${formatDate(i.due_date)}</td><td>${invoiceStatusPill(i.status)}</td><td>${i.status === "READY_FOR_PAYMENT" ? `<button class="button button--primary button--small" data-finalize-payment="${i.id}">Finalize payment</button>` : `<span class="code-chip">${escapeHTML(i.payment_reference || "PAID")}</span>`}</td></tr>`).join("");
      els.content.innerHTML = `${pageHeader("FINANCE CONTROL", "Payment Finalization", "Finalize supplier payments only after a successful 3-way match.", `<button class="button button--ghost" data-refresh-payment>Refresh</button>`)}
        <section class="metric-grid">${statCard("Ready for finance", ready.length, "Cleared by 3-way match", "green", "✓")}${statCard("Paid", paid.length, "Finalized payments", "blue", "₹")}</section>
        ${queue.length ? tablePanel("Finance payment queue", "Review the invoice, purchase order, amount, and due date before recording the final payment action.", `<table><thead><tr><th>Invoice</th><th>PO</th><th>Amount</th><th>Due</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table>`) : `<section class="panel empty-state-card"><div class="future-icon">₹</div><h2>No invoices ready for finance</h2><p>Invoices appear here after AP validation, goods receipt posting, and a successful 3-way match.</p></section>`}`;
      els.content.querySelector("[data-refresh-payment]")?.addEventListener("click", () => renderPaymentFinalization());
      els.content.querySelectorAll("[data-finalize-payment]").forEach(b => b.addEventListener("click", async () => {
        const invoiceId = b.dataset.finalizePayment;
        const invoice = queue.find(i => String(i.id) === String(invoiceId));
        if (!invoice) return;
        if (!window.confirm(`Finalize payment of ${money(invoice.total_amount, invoice.currency)} for ${invoice.invoice_number}?`)) return;
        b.disabled = true;
        try { const result = await api(`/invoice-matching/${invoiceId}/finalize-payment`, {method:"POST"}); toast(`${result.invoice_number} finalized · ${result.payment_reference}.`); await renderPaymentFinalization(); }
        catch (err) { toast(err.message, "error"); b.disabled = false; }
      }));
    } catch (err) { els.content.innerHTML = emptyState("Payment queue could not be loaded", err.message, "Try again", () => renderPaymentFinalization()); }
  }

  function renderFutureWorkspace(view) {
    const map = {
      "my-requests": ["My Requests", "Track purchase requests assigned to your account."], "new-request": ["New Purchase Request", "Create a structured request for goods or services."],
      approvals: ["Approvals", "Review decisions that require your authorization."], team: ["Team Activity", "See procurement activity relevant to your team."], requests: ["Requests", "Review and progress purchase requests."],
      rfqs: ["RFQs", "Manage sourcing events and supplier outreach."], quotes: ["Quotations", "Compare supplier responses and commercial terms."], "purchase-orders": ["Purchase Orders", "Create and review purchasing documents."], exceptions: ["Exceptions", "Review operational exceptions that need intervention."],
      analytics: ["Command Center", "Monitor procurement performance, flow, and risk."], invoices: ["Invoices", "Review invoice intake and processing status."], matching: ["3-Way Matching", "Compare purchase order, receipt, and invoice evidence."],
      payment: ["Payment Finalization", "Finalize supplier payments after successful 3-way matching."], deliveries: ["Expected Deliveries", "Track deliveries awaiting receipt confirmation."], receipts: ["Goods Receipts", "Record and review received goods or services."],
    };
    const [title, copy] = map[view] || ["Workspace", "Your ProcurePilot workspace."];
    els.content.innerHTML = `${pageHeader("WORKSPACE", title, copy)}
      <section class="panel future-panel"><div class="future-icon">\u2726</div><h2>No live records yet</h2><p>This workspace is available to your role, but there are no operational records to display here yet.</p><div class="pill-row"><span class="pill">Secure access</span><span class="pill">Role-aware</span><span class="pill">RBAC enforced</span><span class="pill">Auditable</span></div></section>`;
  }

  function tablePanel(title, copy, table) { return `<section class="panel table-panel"><div class="panel-heading"><div><span class="eyebrow">LIVE DATABASE DATA</span><h2>${escapeHTML(title)}</h2><p>${escapeHTML(copy)}</p></div></div><div class="table-wrap">${table}</div></section>`; }
  function emptyTableRow(cols, text) { return `<tr><td colspan="${cols}" class="empty-cell">${escapeHTML(text)}</td></tr>`; }
  function departmentName(id) { return state.departments.find(d => d.id === id)?.name || "\u2014"; }
  function actorIcon(type) { return type === "HUMAN" ? "\u25cf" : type === "SYSTEM" ? "\u2699" : "\u2699"; }
  function humanizeAction(action) { return action.toLowerCase().split("_").map(w => w[0]?.toUpperCase()+w.slice(1)).join(" "); }
  function detailSummary(details) { if (!details) return "\u2014"; const entries = Object.entries(details).slice(0,2); return entries.length ? entries.map(([k,v]) => `<span class="detail-chip"><b>${escapeHTML(k)}</b>: ${escapeHTML(Array.isArray(v) ? v.join(", ") : v)}</span>`).join(" ") : "\u2014"; }
  function auditRow(a) { return `<div class="audit-row"><span class="audit-actor audit-actor--${a.actor_type.toLowerCase()}">${actorIcon(a.actor_type)}</span><div><strong>${humanizeAction(a.action)}</strong><small>${escapeHTML(a.actor_type)} \u00b7 ${escapeHTML(a.entity_type)}</small></div><time>${relativeTime(a.created_at)}</time></div>`; }
  function relativeTime(value) { const diff = Date.now()-new Date(value).getTime(); const m=Math.floor(diff/60000); if(m<1)return"now"; if(m<60)return`${m}m ago`; const h=Math.floor(m/60); if(h<24)return`${h}h ago`; return`${Math.floor(h/24)}d ago`; }
  function emptyState(title, copy, label, retry) { window.__ppRetry = retry; return `<section class="panel future-panel"><div class="future-icon">!</div><h2>${escapeHTML(title)}</h2><p>${escapeHTML(copy)}</p><button class="button button--primary" onclick="window.__ppRetry()">${escapeHTML(label)}</button></section>`; }

  function wireCommonActions() {
    els.content.querySelectorAll("[data-nav]").forEach(el => el.addEventListener("click", () => navigate(el.dataset.nav)));
    els.content.querySelector("[data-action=create-user]")?.addEventListener("click", openCreateUser);
    els.content.querySelector("[data-action=create-budget]")?.addEventListener("click", openCreateBudget);
    els.content.querySelector("[data-action=create-vendor]")?.addEventListener("click", openCreateVendor);
    els.content.querySelector("[data-action=refresh-audit]")?.addEventListener("click", () => renderAudit());
  }

  function wireDepartmentActions() {
    wireCommonActions();
    els.content.querySelector("[data-action=create-department]")?.addEventListener("click", openCreateDepartment);
    els.content.querySelectorAll("[data-edit-department]").forEach(el => el.addEventListener("click", () => openEditDepartment(el.dataset.editDepartment)));
  }

  function openCreateDepartment() {
    modal({ title: "Create department", submitLabel: "Create department", body: `<div class="form-grid"><label>Code<input name="code" required minlength="2" maxlength="32" placeholder="LEGAL"></label><label>Name<input name="name" required minlength="2" maxlength="120" placeholder="Legal & Compliance"></label></div><label class="check-row"><input name="is_active" type="checkbox" checked> Active department</label>`, onSubmit: async fd => { await api("/admin/master-data/departments", { method:"POST", body: JSON.stringify({ code: fd.get("code"), name: fd.get("name"), is_active: fd.get("is_active") === "on" }) }); toast("Department created and audited."); await renderDepartments(); } });
  }

  function openEditDepartment(id) {
    const d = state.departments.find(x => x.id === id); if (!d) return;
    modal({ title: `Edit ${d.code}`, submitLabel: "Save changes", body: `<label>Name<input name="name" required value="${escapeHTML(d.name)}"></label><label class="check-row"><input name="is_active" type="checkbox" ${d.is_active ? "checked" : ""}> Active department</label>`, onSubmit: async fd => { await api(`/admin/master-data/departments/${id}`, { method:"PATCH", body: JSON.stringify({ name: fd.get("name"), is_active: fd.get("is_active") === "on" }) }); toast("Department updated and audited."); await renderDepartments(); } });
  }

  function openCreateVendor() {
    modal({ title: "Create supplier", submitLabel: "Create supplier", body: `<div class="form-grid"><label>Vendor code<input name="vendor_code" required minlength="2" maxlength="40" placeholder="VEND-004"></label><label>Legal name<input name="legal_name" required minlength="2" maxlength="200" placeholder="NorthStar Systems Pvt Ltd"></label><label>Contact person<input name="contact_person" maxlength="160" placeholder="Priya Sharma"></label><label>Email<input name="email" type="email" required placeholder="rfq@northstar.example"></label><label>Phone<input name="phone" maxlength="40" placeholder="+91 98765 43210"></label><label>Payment terms (days)<input name="payment_terms_days" type="number" min="0" max="365" value="30" required></label><label class="field-span-2">Capabilities / categories<input name="capabilities" maxlength="500" placeholder="Industrial raw materials, polymers, precision components"></label><label class="field-span-2">Address<textarea name="address" maxlength="500" placeholder="Supplier registered / operating address"></textarea></label><label>Reliability score<input name="reliability_score" type="number" min="0" max="100" step="0.01" value="75" required></label></div><label class="check-row"><input name="is_active" type="checkbox" checked> Eligible / active supplier</label>`, onSubmit: async fd => { await api("/admin/master-data/vendors", { method:"POST", body: JSON.stringify({ vendor_code: fd.get("vendor_code"), legal_name: fd.get("legal_name"), contact_person: fd.get("contact_person") || null, email: fd.get("email"), phone: fd.get("phone") || null, address: fd.get("address") || null, capabilities: fd.get("capabilities") || null, payment_terms_days: Number(fd.get("payment_terms_days")), reliability_score: Number(fd.get("reliability_score")), is_active: fd.get("is_active") === "on" }) }); toast("Supplier created and audited."); await renderVendors(); } });
  }

  function openEditVendor(id) {
    const v = state.vendors.find(x => x.id === id); if (!v) return;
    if (!hasPermission("master_data.manage")) return toast("You can view suppliers, but you do not have permission to edit them.", "error");
    modal({ title: `Edit ${v.vendor_code}`, submitLabel: "Save changes", body: `<div class="form-grid"><label>Legal name<input name="legal_name" required value="${escapeHTML(v.legal_name)}"></label><label>Contact person<input name="contact_person" value="${escapeHTML(v.contact_person || "")}"></label><label>Email<input name="email" type="email" required value="${escapeHTML(v.email)}"></label><label>Phone<input name="phone" value="${escapeHTML(v.phone || "")}"></label><label>Payment terms (days)<input name="payment_terms_days" type="number" min="0" max="365" value="${v.payment_terms_days}" required></label><label>Reliability score<input name="reliability_score" type="number" min="0" max="100" step="0.01" value="${v.reliability_score}" required></label><label class="field-span-2">Capabilities / categories<input name="capabilities" maxlength="500" value="${escapeHTML(v.capabilities || "")}"></label><label class="field-span-2">Address<textarea name="address" maxlength="500">${escapeHTML(v.address || "")}</textarea></label></div><label class="check-row"><input name="is_active" type="checkbox" ${v.is_active ? "checked" : ""}> Eligible / active supplier</label>`, onSubmit: async fd => { await api(`/admin/master-data/vendors/${id}`, { method:"PATCH", body: JSON.stringify({ legal_name: fd.get("legal_name"), contact_person: fd.get("contact_person") || null, email: fd.get("email"), phone: fd.get("phone") || null, address: fd.get("address") || null, capabilities: fd.get("capabilities") || null, payment_terms_days: Number(fd.get("payment_terms_days")), reliability_score: Number(fd.get("reliability_score")), is_active: fd.get("is_active") === "on" }) }); toast("Supplier updated and audited."); await renderVendors(); } });
  }

  function openCreateBudget() {
    if (!state.departments.length) { toast("Create a department first.", "error"); return; }
    modal({ title: "Create budget", submitLabel: "Create budget", body: `<div class="form-grid"><label>Department<select name="department_id" required>${state.departments.map(d=>`<option value="${d.id}">${escapeHTML(d.code)} \u00b7 ${escapeHTML(d.name)}</option>`).join("")}</select></label><label>Fiscal year<input name="fiscal_year" type="number" min="2020" max="2100" value="${new Date().getFullYear()}" required></label><label>Currency<input name="currency" value="INR" minlength="3" maxlength="3" required></label><label>Allocated amount<input name="allocated_amount" type="number" min="0" step="0.01" required></label><label>Consumed amount<input name="consumed_amount" type="number" min="0" step="0.01" value="0" required></label></div><label class="check-row"><input name="is_active" type="checkbox" checked> Active budget</label>`, onSubmit: async fd => { await api("/admin/master-data/budgets", { method:"POST", body: JSON.stringify({ department_id: fd.get("department_id"), fiscal_year: Number(fd.get("fiscal_year")), currency: String(fd.get("currency")).toUpperCase(), allocated_amount: Number(fd.get("allocated_amount")), consumed_amount: Number(fd.get("consumed_amount")), is_active: fd.get("is_active") === "on" }) }); toast("Budget created and audited."); await renderBudgets(); } });
  }

  function openCreateUser() {
    if (!hasPermission("users.manage")) return toast("You do not have permission to manage users.", "error");
    const roles = state.roles.length ? state.roles : [];
    modal({ title: "Create user", submitLabel: "Create user", body: `<div class="form-grid"><label>Full name<input name="full_name" required minlength="2" placeholder="Aarav Patel"></label><label>Email<input name="email" type="email" required placeholder="aarav@company.com"></label><label>Temporary password<input name="password" type="password" required minlength="12" placeholder="12+ characters"></label><label>Department<select name="department_id"><option value="">No department</option>${state.departments.map(d=>`<option value="${d.id}">${escapeHTML(d.name)}</option>`).join("")}</select></label></div><fieldset><legend>Roles</legend><div class="role-checkbox-grid">${roles.map(r=>`<label class="check-row"><input type="checkbox" name="role_codes" value="${escapeHTML(r.code)}"> ${escapeHTML(r.name)}</label>`).join("")}</div></fieldset>`, onSubmit: async fd => { const role_codes = fd.getAll("role_codes"); await api("/admin/users", { method:"POST", body: JSON.stringify({ email: fd.get("email"), full_name: fd.get("full_name"), password: fd.get("password"), department_id: fd.get("department_id") || null, role_codes, is_active: true }) }); toast("User created and audited."); await renderUsers(); } });
  }

  function handleGlobalSearch() {
    const q = els.search.value.trim().toLowerCase();
    if (!q) return;
    const nav = [...els.nav.querySelectorAll("[data-view]")];
    const hit = nav.find(b => b.textContent.toLowerCase().includes(q));
    if (hit) { navigate(hit.dataset.view); els.search.value = ""; }
    else toast("Search currently navigates available modules.", "error");
  }

  async function init() {
    if (!token()) return window.location.replace("/login");
    try {
      state.user = await api("/auth/me");
      setUserChrome();
      buildNavigation();
      refreshNotificationIndicator();
      els.loading.hidden = true; els.shell.hidden = false;

      let initialView = routeStateFromLocation();
      if (!viewAllowedForCurrentUser(initialView)) {
        state.selectedRequestId = null;
        state.editingRequestId = null;
        state.comparisonRfqId = null;
        state.selectionRfqId = null;
        state.goodsReceiptId = null;
        state.approvalId = null; state.approvalRequestId = null;
        initialView = "home";
      }
      syncRoute(initialView, { replace: true });
      await navigate(initialView, { syncUrl: false });
    } catch (err) {
      sessionStorage.removeItem(TOKEN_KEY);
      window.location.replace("/login");
    }
  }

  window.addEventListener("popstate", async () => {
    state.selectedRequestId = null;
    state.editingRequestId = null;
    state.comparisonRfqId = null;
    state.selectionRfqId = null;
    state.goodsReceiptId = null;
    state.matchingInvoiceId = null;
    state.approvalId = null; state.approvalRequestId = null;
    const view = routeStateFromLocation();
    const target = viewAllowedForCurrentUser(view) ? view : "home";
    await navigate(target, { syncUrl: false });
  });

  els.logout.addEventListener("click", () => { sessionStorage.removeItem(TOKEN_KEY); window.location.replace("/login"); });
  els.notificationButton?.addEventListener("click", openNotifications);
  els.mobileMenu.addEventListener("click", () => els.sidebar.classList.toggle("is-open"));
  els.search.addEventListener("keydown", event => { if (event.key === "Enter") handleGlobalSearch(); });
  document.addEventListener("keydown", event => { if (event.key === "/" && document.activeElement !== els.search) { event.preventDefault(); els.search.focus(); } });

  init();
})();
