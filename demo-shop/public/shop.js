async function boot() {
  const cfg = await (await fetch("/api/config")).json();
  const banner = document.getElementById("banner");
  if (cfg.banner) {
    banner.hidden = false;
    banner.textContent = cfg.banner;
  }
  const page = window.__PAGE__;
  if (page === "catalog") renderCatalog(cfg);
  if (page === "product") renderProduct(cfg);
  if (page === "checkout") renderCheckout(cfg);
  if (page === "subscribe") renderSubscribe(cfg);
  if (page === "thanks") renderThanks();
}

function renderCatalog(cfg) {
  const app = document.getElementById("app");
  app.innerHTML = `<h1>Roastery bags</h1><p class="muted">Three coffees, one club. Invented brand, real checkout path.</p><div class="grid"></div>`;
  const grid = app.querySelector(".grid");
  for (const p of cfg.products.filter((x) => x.kind === "one_off")) {
    const paused = (cfg.paused_products || []).includes(p.id);
    grid.insertAdjacentHTML(
      "beforeend",
      `<article class="card"><h2>${p.name}</h2><p class="muted">${p.blurb}</p><p class="price">$${p.price}</p>
       <a class="btn" href="/checkout/${p.id}">${paused ? "Paused" : "Buy"}</a></article>`
    );
  }
}

function productFrom(cfg) {
  const id = document.querySelector("[data-product]")?.dataset.product;
  return cfg.products.find((p) => p.id === id) || cfg.products[0];
}

function renderProduct(cfg) {
  const p = productFrom(cfg);
  document.getElementById("app").innerHTML = `<article class="card"><h1>${p.name}</h1><p>${p.blurb}</p><p class="price">$${p.price}</p><a class="btn" href="/checkout/${p.id}">Checkout</a></article>`;
}

async function renderCheckout(cfg) {
  const p = productFrom(cfg);
  const paused = (cfg.paused_products || []).includes(p.id);
  const app = document.getElementById("app");
  app.innerHTML = `<article class="card"><h1>Checkout — ${p.name}</h1><p class="price">$${p.price} ${cfg.currency || "USD"}</p>
    <div id="pay"></div><p id="err" class="err"></p></article>`;
  if (paused) {
    document.getElementById("err").textContent = "This product is paused.";
    return;
  }
  if (cfg.paypal_environment === "SANDBOX" && cfg.paypal_client_id) {
    await renderPaypalV6(cfg, p);
  } else {
    const btn = document.createElement("button");
    btn.id = "mock-pay";
    btn.textContent = "Pay (mock)";
    document.getElementById("pay").appendChild(btn);
    btn.onclick = async () => {
      const created = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: p.id }),
      });
      const order = await created.json();
      const cap = await fetch(`/api/orders/${order.id}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: p.id }),
      });
      const result = await cap.json();
      if (result.ok) location.href = "/thanks";
      else document.getElementById("err").textContent = result.error_code || "Payment failed";
    };
  }
}

async function renderPaypalV6(cfg, p) {
  await new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://www.paypal.com/web-sdk/v6/core";
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
  const sdk = await window.paypal.createInstance({
    clientId: cfg.paypal_client_id,
    components: ["paypal-payments"],
    pageType: "checkout",
  });
  const methods = await sdk.findEligibleMethods({ currencyCode: cfg.currency || "USD" });
  const host = document.getElementById("pay");
  host.innerHTML = `<paypal-button id="paypal-btn" type="pay" class="paypal-gold" hidden></paypal-button>`;
  const btn = document.getElementById("paypal-btn");
  if (methods.isEligible("paypal")) btn.hidden = false;
  const session = sdk.createPayPalOneTimePaymentSession({
    onApprove: async ({ orderId }) => {
      const cap = await fetch(`/api/orders/${orderId}/capture`, { method: "POST" });
      const result = await cap.json();
      if (result.ok) location.href = "/thanks";
      else document.getElementById("err").textContent = result.error_code || "Capture failed";
    },
  });
  btn.addEventListener("click", async () => {
    const created = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: p.id }),
    }).then((r) => r.json());
    await session.start({ presentationMode: "auto" }, Promise.resolve({ orderId: created.orderId || created.id }));
  });
}

function renderSubscribe(cfg) {
  const paused = cfg.plan_signups_paused;
  document.getElementById("app").innerHTML = `<article class="card"><h1>Coffee Club</h1>
    <p>One bag a month. $${cfg.products.find((p) => p.kind === "subscription")?.price || "14.00"}.</p>
    <button id="join" ${paused ? "disabled" : ""}>${paused ? "Sign-ups paused" : "Join (mock)"}</button>
    <p id="err" class="err"></p></article>`;
  document.getElementById("join").onclick = async () => {
    const res = await fetch("/api/subscribe", { method: "POST" });
    if (res.ok) location.href = "/thanks";
    else document.getElementById("err").textContent = (await res.json()).error || "Could not subscribe";
  };
}

function renderThanks() {
  document.getElementById("app").innerHTML = `<article class="card"><h1>Thank you</h1><p class="muted">The roastery has your order.</p><a href="/">Back to the shop</a></article>`;
}

boot();
