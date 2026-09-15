const status = document.getElementById("login-status");
const error = document.getElementById("login-error");
const retry = document.getElementById("retry-login");
retry.addEventListener("click", () => location.reload());

async function signIn(response) {
  status.textContent = "正在驗證帳號…";
  error.textContent = "";
  document.getElementById("google-button").hidden = true;
  try {
    const result = await fetch("/auth/google", {
      method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-Recon-Request": "1"},
      body: JSON.stringify({credential: response.credential})
    });
    if (!result.ok) {
      if (result.status === 403) throw new Error("此帳號無法使用工作區，或登入驗證已過期。請重新登入擁有者帳號。");
      throw new Error("登入驗證失敗，請重新嘗試。");
    }
    // Keep only a validated run ID; never accept an arbitrary redirect URL.
    const run = new URLSearchParams(location.search).get("run");
    location.replace("/workspace" + (run && /^[a-f0-9-]{36}$/.test(run) ? "?run=" + encodeURIComponent(run) : ""));
  } catch (failure) {
    status.textContent = "";
    error.textContent = failure.message;
    retry.hidden = false;
  }
}

async function start() {
  try {
    const response = await fetch("/auth/config", {credentials: "same-origin", cache: "no-store"});
    if (!response.ok) throw new Error("網站尚未完成 Google 登入設定，請擁有者設定後重新部署。");
    const config = await response.json();
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.onload = resolve;
      script.onerror = () => reject(new Error("無法載入 Google 登入，請稍後再試。"));
      document.head.append(script);
    });
    google.accounts.id.initialize({client_id: config.client_id, nonce: config.nonce,
      callback: signIn, auto_select: false, ux_mode: "popup"});
    google.accounts.id.renderButton(document.getElementById("google-button"),
      {theme: "outline", size: "large", text: "signin_with", locale: "zh_TW"});
    status.textContent = "請選擇擁有者 Google 帳號。";
  } catch (failure) {
    status.textContent = "";
    error.textContent = failure.message;
    retry.hidden = false;
  }
}
start();
