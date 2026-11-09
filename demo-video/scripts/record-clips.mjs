/**
 * Record the demo clips against the running stack.
 * Viewport 1600×900 matches CLIP_W/CLIP_H used for callout coordinates.
 */
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import { mkdirSync, rmSync, existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dirname, "..");

// Passcode and inject token come from the repo's .env, like the stack itself.
const dotenv = {};
const envFile = join(ROOT, "..", ".env");
if (existsSync(envFile)) {
  for (const line of readFileSync(envFile, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
    if (m) dotenv[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}
const env = (key, fallback) => process.env[key] ?? dotenv[key] ?? fallback;

const DASH = "http://127.0.0.1:8000";
const SHOP = "http://127.0.0.1:3000";
const PASS = env("DASHBOARD_PASSCODE", "demo-judge");
const TOKEN = env("INJECT_TOKEN", "change-me");
const HEADERS = { "x-passcode": PASS, "x-inject-token": TOKEN, "content-type": "application/json" };
const TMP = join(ROOT, "out", "clip-raw");
const OUT = join(ROOT, "public", "clips");
const W = 1600;
const H = 900;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const toMp4 = (src, dest, startSec = 0) => {
  const trim = startSec > 0 ? ["-ss", startSec.toFixed(2)] : [];
  const r = spawnSync(
    "ffmpeg",
    ["-y", ...trim, "-i", src, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", dest],
    { stdio: "inherit" },
  );
  if (r.status !== 0) throw new Error(`ffmpeg failed for ${src}`);
};

const login = async (page) => {
  await page.goto(`${DASH}/#/overview`, { waitUntil: "networkidle" });
  if (await page.getByRole("button", { name: "Log In" }).count()) {
    await page.getByLabel(/passcode/i).fill(PASS);
    await page.getByLabel(/inject|token/i).fill(TOKEN);
    await page.getByRole("button", { name: "Log In" }).click();
    await page.getByRole("link", { name: "Overview" }).waitFor({ timeout: 8000 });
  }
};

const chaos = async (page, label) => {
  await page.goto(`${DASH}/#/chaos`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: label }).waitFor();
  const card = page.getByRole("heading", { name: label }).locator("..");
  await card.getByRole("button").first().click();
  await page.locator(".result-bar").waitFor({ timeout: 15000 });
};

// Live agents take a while; wait off camera so the clips stay short.
const api = async (path, body) => {
  const res = await fetch(`${DASH}${path}`, {
    method: body ? "POST" : "GET",
    headers: HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
};

// Proposal ids already on this playbook's recent incidents, so a fresh run can be told apart.
const proposalIds = async (playbook) => {
  const { items } = await api(`/api/incidents?playbook=${playbook}`);
  const ids = new Set();
  for (const item of (items ?? []).slice(0, 3)) {
    const detail = await api(`/api/incidents/${item.id}`);
    for (const p of detail.proposals ?? []) ids.add(p.id);
  }
  return ids;
};

const agentsDone = async (playbook, before = new Set(), timeoutMs = 300000) => {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const { items } = await api(`/api/incidents?playbook=${playbook}`);
    if (items?.length) {
      const detail = await api(`/api/incidents/${items[0].id}`);
      if ((detail.proposals ?? []).some((p) => !before.has(p.id))) {
        console.log(`agents done for ${playbook}:`, detail.steps.map((s) => s.model).join(", "));
        return detail;
      }
    }
    await sleep(3000);
  }
  throw new Error(
    `agents did not finish ${playbook}. A ${playbook} incident from the last 30 minutes absorbs new events: wait, then run again.`,
  );
};

const injectAndWait = async (chaosBody, playbook) => {
  const before = await proposalIds(playbook);
  // Each scenario starts from a clean shop (no banner, USD), like a merchant who
  // closed the last incident, and after a pause so free tier models have recovered.
  await api("/api/chaos", { reset: true, note: "clips: reset between scenarios" });
  await sleep(20000);
  await api("/api/chaos", { chaos: chaosBody, note: `clips: ${playbook}` });
  return agentsDone(playbook, before);
};

// Scroll so a section heading (h2/h3) sits near the top of the viewport.
const scrollToHeading = async (page, text, smooth = true) => {
  await page.evaluate(
    ([t, sm]) => {
      const h = [...document.querySelectorAll("h2, h3")].find((el) => el.textContent.trim().startsWith(t));
      if (h) window.scrollTo({ top: h.getBoundingClientRect().top + window.scrollY - 70, behavior: sm ? "smooth" : "auto" });
    },
    [text, smooth],
  );
};
const scrollToBottom = (page, smooth = true) =>
  page.evaluate((sm) => window.scrollTo({ top: document.body.scrollHeight, behavior: sm ? "smooth" : "auto" }), smooth);

// The newest incident of a playbook (the checkout clips must not pick up a later scenario).
let checkoutId = null;
const latestIncident = async (playbook) => {
  const { items } = await api(`/api/incidents?playbook=${playbook}`);
  if (!items?.length) throw new Error(`no ${playbook} incident`);
  return items[0].id;
};
const checkoutIncident = async () => checkoutId ?? latestIncident("checkout_failure_spike");

const record = async (browser, name, fn) => {
  const dir = join(TMP, name);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 1,
    recordVideo: { dir, size: { width: W, height: H } },
  });
  const page = await context.newPage();
  const startedAt = Date.now();
  let result;
  try {
    result = await fn(page);
  } finally {
    await context.close();
  }
  const files = readdirSync(dir).filter((f) => f.endsWith(".webm"));
  if (!files.length) throw new Error(`no video for ${name}`);
  // A clip can return { readyAt } to cut the page-loading time off its start.
  const startSec = result?.readyAt ? Math.max(0, (result.readyAt - startedAt) / 1000 - 0.2) : 0;
  toMp4(join(dir, files[0]), join(OUT, name), startSec);
  console.log("wrote", name);
};

mkdirSync(OUT, { recursive: true });
rmSync(TMP, { recursive: true, force: true });
mkdirSync(TMP, { recursive: true });

const browser = await chromium.launch({ headless: true });

const skipExisting = process.argv.includes("--resume");

try {
  if (!skipExisting) {
    await record(browser, "_reset.mp4", async (page) => {
      await login(page);
      await chaos(page, "Reset all chaos");
      await sleep(400);
    });
  }

  const maybe = async (name, fn) => {
    if (skipExisting && existsSync(join(OUT, name))) {
      console.log("skip", name);
      return;
    }
    await record(browser, name, fn);
  };

  const checkoutBefore = await proposalIds("checkout_failure_spike");
  await maybe("01-chaos-bad-currency.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/chaos`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Ship bad currency config" }).waitFor();
    await sleep(800);
    const card = page.getByRole("heading", { name: "Ship bad currency config" }).locator("..");
    await card.getByRole("button").first().click();
    await page.locator(".result-bar").waitFor({ timeout: 15000 });
    await sleep(1200);
  });

  // The banner is set by the agents (shop.banner.set, auto), so film the shop after they finish.
  const have = (name) => skipExisting && existsSync(join(OUT, name));
  if (!(have("02-shop-failing.mp4") && have("04-incident-detail.mp4") && have("05-approve.mp4"))) {
    const done = have("01-chaos-bad-currency.mp4")
      ? await injectAndWait({ bad_currency: true }, "checkout_failure_spike") // resumed run
      : await agentsDone("checkout_failure_spike", checkoutBefore);
    checkoutId = done.id;
  }

  await maybe("02-shop-failing.mp4", async (page) => {
    // The checkout page: the agents' warning banner, the price now in EUR on a USD
    // shop, and the real PayPal JS SDK v6 button from the sandbox.
    await page.goto(`${SHOP}/checkout/house-blend`, { waitUntil: "networkidle" });
    await page.locator("#paypal-btn:not([hidden])").waitFor({ timeout: 20000 }).catch(() => {
      console.log("PayPal button did not show; recording the page anyway");
    });
    await sleep(600);
    const readyAt = Date.now();
    await sleep(3000);
    return { readyAt };
  });

  await maybe("03-incident-opens.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/overview`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Revenue health" }).waitFor();
    const readyAt = Date.now();
    await sleep(4500);
    return { readyAt };
  });


  await maybe("04-incident-detail.mp4", async (page) => {
    // Three holds the video zooms into: the agent timeline (models, latencies, PayPal
    // reads through MCP), the root cause with its evidence, then the proposals.
    await login(page);
    const id = await checkoutIncident();
    await page.goto(`${DASH}/#/incident/${id}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Agent timeline" }).waitFor();
    await scrollToBottom(page, false);
    await sleep(500);
    const readyAt = Date.now();
    await sleep(5000);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await sleep(5500);
    await scrollToHeading(page, "Proposals");
    await sleep(5000);
    return { readyAt };
  });

  await maybe("05-approve.mp4", async (page) => {
    await login(page);
    const id = await checkoutIncident();
    await page.goto(`${DASH}/#/incident/${id}`, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Approve" }).first().waitFor();
    await scrollToHeading(page, "Proposals", false);
    await sleep(500);
    const readyAt = Date.now();
    await sleep(900);
    const card = page.locator(".card", { has: page.locator("code", { hasText: "shop.config.rollback" }) }).first();
    await card.getByRole("button", { name: "Approve" }).click();
    // Hold until the rollback shows as executed, then a beat longer.
    await card.locator(".badge.executed").first().waitFor({ timeout: 15000 }).catch(() => {
      console.log("rollback did not show as executed within 15 s");
    });
    await sleep(1600);
    return { readyAt };
  });

  if (!(skipExisting && existsSync(join(OUT, "06-refund-wave.mp4")))) {
    await injectAndWait({ inject: "refund_wave" }, "refund_wave");
  }
  await maybe("06-refund-wave.mp4", async (page) => {
    await login(page);
    const res = await page.request.get(`${DASH}/api/incidents`);
    const items = (await res.json()).items;
    const refund = items.find((i) => i.playbook === "refund_wave") ?? items[0];
    await page.goto(`${DASH}/#/incident/${refund.id}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Proposals" }).waitFor();
    await sleep(400);
    const readyAt = Date.now();
    await sleep(2500); // root cause at the top
    await scrollToHeading(page, "Proposals");
    await sleep(10000); // pause sales waits for approval; the red-team probe is refused
    return { readyAt };
  });

  if (!(skipExisting && existsSync(join(OUT, "07-renewals.mp4")))) {
    await injectAndWait({ inject: "renewal_failures" }, "subscription_renewal_failures");
  }
  await maybe("07-renewals.mp4", async (page) => {
    await login(page);
    const res = await page.request.get(`${DASH}/api/incidents`);
    const items = (await res.json()).items;
    const renewal = items.find((i) => i.playbook === "subscription_renewal_failures") ?? items[0];
    await page.goto(`${DASH}/#/incident/${renewal.id}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Agent timeline" }).waitFor();
    await scrollToBottom(page, false);
    await sleep(500);
    const readyAt = Date.now();
    await sleep(5000); // the Diagnostician read the real plan through MCP
    await scrollToHeading(page, "Proposals");
    await sleep(6500); // reminder auto, capture waits for approval
    return { readyAt };
  });

  await maybe("08-audit-log.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/audit`, { waitUntil: "networkidle" });
    await sleep(2800);
  });

  await maybe("09-transactions.mp4", async (page) => {
    // The AG Grid transactions view: newest events first, injected ones badged
    // "simulated", then a server side search for the failing captures.
    await login(page);
    await page.goto(`${DASH}/#/transactions`, { waitUntil: "networkidle" });
    await page.locator(".ag-row").first().waitFor({ timeout: 15000 });
    await sleep(800);
    const readyAt = Date.now();
    await sleep(2600);
    await page.locator("#qf").click();
    await page.keyboard.type("CURRENCY_MISMATCH", { delay: 45 });
    await page.keyboard.press("Enter");
    await sleep(3200);
    return { readyAt };
  });
} finally {
  await browser.close();
}

if (existsSync(join(OUT, "_reset.mp4"))) rmSync(join(OUT, "_reset.mp4"));
console.log("done");
