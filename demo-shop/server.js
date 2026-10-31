"use strict";

/**
 * Lumen Coffee Co. — fictional demo shop.
 * MOCK: "Pay (mock)" hits this server; chaos flags decide success.
 * SANDBOX: PayPal JS SDK v6 buttons + Orders REST on this server.
 */

const express = require("express");
const path = require("path");
const products = require("./products");

const PORT = Number(process.env.SHOP_PORT || 3000);
const FLATLINE = process.env.FLATLINE_API_URL || "http://localhost:8000";
const PAYPAL_ENV = (process.env.PAYPAL_ENVIRONMENT || "MOCK").toUpperCase();
const CLIENT_ID = process.env.PAYPAL_CLIENT_ID || "";
const CLIENT_SECRET = process.env.PAYPAL_CLIENT_SECRET || "";
const PLAN_ID = process.env.PAYPAL_SANDBOX_PLAN_ID || "P-COFFEECLUB";
const API_BASE = "https://api-m.sandbox.paypal.com";

if (PAYPAL_ENV !== "MOCK" && PAYPAL_ENV !== "SANDBOX") {
  console.error(
    `PAYPAL_ENVIRONMENT=${PAYPAL_ENV} is not allowed. Use MOCK or SANDBOX. Live PayPal is impossible.`
  );
  process.exit(1);
}

const orders = new Map();
let cachedConfig = { currency: "USD", paused_products: [], plan_signups_paused: false, banner: "", chaos: {} };
let cachedAt = 0;

async function shopConfig() {
  if (Date.now() - cachedAt < 2_000) return cachedConfig;
  try {
    const res = await fetch(`${FLATLINE}/api/shop/config`);
    if (res.ok) {
      cachedConfig = await res.json();
      cachedAt = Date.now();
    }
  } catch (err) {
    console.warn("config fetch failed", err.message);
  }
  return cachedConfig;
}

async function telemetry(body) {
  try {
    await fetch(`${FLATLINE}/api/telemetry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, at: new Date().toISOString() }),
    });
  } catch (err) {
    console.warn("telemetry failed", err.message);
  }
}

async function sandboxToken() {
  const basic = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString("base64");
  const res = await fetch(`${API_BASE}/v1/oauth2/token`, {
    method: "POST",
    headers: { Authorization: `Basic ${basic}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials",
  });
  if (!res.ok) throw new Error(`token ${res.status}`);
  return (await res.json()).access_token;
}

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use("/static", express.static(path.join(__dirname, "public")));

app.get("/api/config", async (_req, res) => {
  const cfg = await shopConfig();
  res.json({
    ...cfg,
    paypal_environment: PAYPAL_ENV,
    paypal_client_id: CLIENT_ID,
    plan_id: PLAN_ID,
    products,
  });
});

app.get("/api/products", (_req, res) => res.json(products));

app.post("/api/orders", async (req, res) => {
  const started = Date.now();
  const cfg = await shopConfig();
  const product = products.find((p) => p.id === req.body.product_id) || products[0];
  if ((cfg.paused_products || []).includes(product.id)) {
    return res.status(409).json({ error: "product_paused" });
  }
  const currency = cfg.chaos && cfg.chaos.bad_currency ? "EUR" : cfg.currency || "USD";
  const order = {
    id: `ORD-${Date.now()}`,
    product_id: product.id,
    amount: product.price,
    currency,
    status: "CREATED",
  };

  if (PAYPAL_ENV === "SANDBOX" && CLIENT_ID) {
    try {
      const token = await sandboxToken();
      const body = {
        intent: "CAPTURE",
        purchase_units: [
          {
            custom_id: product.id,
            amount: { currency_code: currency, value: product.price },
          },
        ],
      };
      const created = await fetch(`${API_BASE}/v2/checkout/orders`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await created.json();
      order.id = data.id || order.id;
      order.paypal = data;
    } catch (err) {
      await telemetry({
        type: "checkout.create",
        ok: false,
        error_code: "CREATE_FAILED",
        product_id: product.id,
        amount: product.price,
        currency,
        latency_ms: Date.now() - started,
      });
      return res.status(502).json({ error: err.message });
    }
  }

  orders.set(order.id, order);
  await telemetry({
    type: "checkout.create",
    ok: true,
    order_id: order.id,
    product_id: product.id,
    amount: product.price,
    currency,
    latency_ms: Date.now() - started,
  });
  res.json({ orderId: order.id, id: order.id, amount: order.amount, currency });
});

app.post("/api/orders/:id/capture", async (req, res) => {
  const started = Date.now();
  const cfg = await shopConfig();
  const order = orders.get(req.params.id) || { id: req.params.id, product_id: req.body.product_id, amount: "18.00", currency: cfg.currency || "USD" };
  const chaos = cfg.chaos || {};
  let ok = true;
  let error_code = null;
  let paypal = null;

  if (PAYPAL_ENV === "MOCK") {
    if (chaos.mock_response) {
      ok = false;
      error_code = chaos.mock_response;
    } else if (chaos.bad_currency || order.currency !== (cfg.currency || "USD")) {
      ok = false;
      error_code = "CURRENCY_MISMATCH";
    }
    order.status = ok ? "COMPLETED" : "DECLINED";
  } else {
    try {
      const token = await sandboxToken();
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };
      if (chaos.mock_response) {
        headers["PayPal-Mock-Response"] = JSON.stringify({ mock_application_codes: chaos.mock_response });
      }
      const captured = await fetch(`${API_BASE}/v2/checkout/orders/${req.params.id}/capture`, {
        method: "POST",
        headers,
      });
      paypal = await captured.json();
      ok = captured.ok && paypal.status === "COMPLETED";
      if (!ok) {
        error_code =
          (paypal.details && paypal.details[0] && paypal.details[0].issue) ||
          paypal.name ||
          "CAPTURE_FAILED";
      }
    } catch (err) {
      ok = false;
      error_code = "CAPTURE_FAILED";
      paypal = { error: err.message };
    }
  }

  await telemetry({
    type: "checkout.capture",
    ok,
    error_code,
    order_id: order.id,
    product_id: order.product_id,
    amount: order.amount,
    currency: order.currency,
    latency_ms: Date.now() - started,
  });
  res.status(ok ? 200 : 422).json({ ok, error_code, order, paypal });
});

app.post("/api/subscribe", async (req, res) => {
  const cfg = await shopConfig();
  if (cfg.plan_signups_paused) {
    return res.status(409).json({ error: "plan_signups_paused" });
  }
  const sub = { id: `I-MOCK-${Date.now()}`, plan_id: PLAN_ID, status: "ACTIVE" };
  await telemetry({
    type: "subscription.activated",
    ok: true,
    plan_id: PLAN_ID,
    amount: "14.00",
    currency: cfg.currency || "USD",
  });
  res.json(sub);
});

function page(name, extra = "") {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Lumen Coffee Co.</title>
  <link rel="stylesheet" href="/static/shop.css"/>
</head>
<body>
  <div id="banner" class="banner" hidden></div>
  <header>
    <a class="brand" href="/">Lumen Coffee Co.</a>
    <nav>
      <a href="/">Shop</a>
      <a href="/subscribe">Coffee Club</a>
    </nav>
  </header>
  <main id="app">${extra}</main>
  <script>window.__PAGE__=${JSON.stringify(name)};</script>
  <script src="/static/shop.js"></script>
</body>
</html>`;
}

app.get("/", (_req, res) => res.send(page("catalog")));
app.get("/product/:id", (req, res) => res.send(page("product", `<div data-product="${req.params.id}"></div>`)));
app.get("/checkout/:id", (req, res) => res.send(page("checkout", `<div data-product="${req.params.id}"></div>`)));
app.get("/subscribe", (_req, res) => res.send(page("subscribe")));
app.get("/thanks", (_req, res) => res.send(page("thanks")));

app.listen(PORT, () => {
  console.log(`Lumen Coffee Co. on http://localhost:${PORT} (${PAYPAL_ENV})`);
});
