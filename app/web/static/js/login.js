(() => {
  const TOKEN_KEY = "procurepilot_access_token";
  const form = document.querySelector("#login-form");
  const email = document.querySelector("#email");
  const password = document.querySelector("#password");
  const button = document.querySelector("#login-button");
  const error = document.querySelector("#login-error");
  const toggle = document.querySelector("#toggle-password");

  if (sessionStorage.getItem(TOKEN_KEY)) {
    window.location.replace("/app");
    return;
  }

  toggle.addEventListener("click", () => {
    const show = password.type === "password";
    password.type = show ? "text" : "password";
    toggle.textContent = show ? "Hide" : "Show";
    toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;

    if (!email.value.trim() || !password.value) {
      error.textContent = "Enter your email and password.";
      error.hidden = false;
      return;
    }

    button.disabled = true;
    button.textContent = "Signing in…";

    const body = new URLSearchParams();
    body.set("username", email.value.trim());
    body.set("password", password.value);

    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "Sign in failed.");
      }

      sessionStorage.setItem(TOKEN_KEY, payload.access_token);
      window.location.replace("/app");
    } catch (err) {
      error.textContent = err.message || "Unable to sign in.";
      error.hidden = false;
      button.disabled = false;
      button.textContent = "Sign in to ProcurePilot";
    }
  });
})();
