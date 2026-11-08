/**
 * Record the eight demo clips against the running stack.
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

const toMp4 = (src, dest) => {
  const r = spawnSync(
    "ffmpeg",
    ["-y", "-i", src, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", dest],
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

const agentsDone = async (playbook, timeoutMs = 300000) => {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const { items } = await api(`/api/incidents?playbook=${playbook}`);
    if (items?.length) {
      const detail = await api(`/api/incidents/${items[0].id}`);
      if (detail.proposals?.length) {
        console.log(`agents done for ${playbook}:`, detail.steps.map((s) => s.model).join(", "));
        return detail;
      }
    }
    await sleep(3000);
  }
  throw new Error(`agents did not finish ${playbook}`);
};

const injectAndWait = async (chaosBody, playbook) => {
  await api("/api/chaos", { chaos: chaosBody, note: `clips: ${playbook}` });
  return agentsDone(playbook);
};

const firstIncident = async (page) => {
  const res = await page.request.get(`${DASH}/api/incidents`);
  const data = await res.json();
  if (!data.items?.length) throw new Error("no incidents");
  return data.items[0].id;
};

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
  try {
    await fn(page);
  } finally {
    await context.close();
  }
  const files = readdirSync(dir).filter((f) => f.endsWith(".webm"));
  if (!files.length) throw new Error(`no video for ${name}`);
  toMp4(join(dir, files[0]), join(OUT, name));
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

  await maybe("02-shop-failing.mp4", async (page) => {
    await page.goto(SHOP, { waitUntil: "networkidle" });
    await sleep(600);
    const pay = page.getByRole("button", { name: /Pay/i }).first();
    if (await pay.count()) {
      await pay.click();
      await sleep(1800);
    } else {
      await sleep(2000);
    }
  });

  await maybe("03-incident-opens.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/overview`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Revenue health" }).waitFor();
    await sleep(2500);
  });

  const have = (name) => skipExisting && existsSync(join(OUT, name));
  if (!(have("04-incident-detail.mp4") && have("05-approve.mp4"))) {
    await agentsDone("checkout_failure_spike");
  }

  await maybe("04-incident-detail.mp4", async (page) => {
    await login(page);
    const id = await firstIncident(page);
    await page.goto(`${DASH}/#/incident/${id}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: /checkout|Root cause|Proposals/i }).first().waitFor();
    await sleep(800);
    await page.evaluate(() => window.scrollTo(0, 280));
    await sleep(1800);
    await page.evaluate(() => window.scrollTo(0, 560));
    await sleep(1600);
  });

  await maybe("05-approve.mp4", async (page) => {
    await login(page);
    const id = await firstIncident(page);
    await page.goto(`${DASH}/#/incident/${id}`, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Approve" }).first().waitFor();
    await page.evaluate(() => window.scrollTo(0, 360));
    await sleep(700);
    await page.getByRole("button", { name: "Approve" }).first().click();
    await sleep(1800);
  });

  if (!(skipExisting && existsSync(join(OUT, "06-refund-wave.mp4")))) {
    await injectAndWait({ inject: "refund_wave" }, "refund_wave");
  }
  await maybe("06-refund-wave.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/chaos`, { waitUntil: "networkidle" });
    await sleep(3000); // the video trims these first 3 seconds
    const res = await page.request.get(`${DASH}/api/incidents`);
    const items = (await res.json()).items;
    const refund = items.find((i) => i.playbook === "refund_wave") ?? items[0];
    await page.goto(`${DASH}/#/incident/${refund.id}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: /refund|Proposals/i }).first().waitFor();
    await sleep(700);
    await page.evaluate(() => window.scrollTo(0, 360));
    await sleep(2200);
  });

  if (!(skipExisting && existsSync(join(OUT, "07-renewals.mp4")))) {
    await injectAndWait({ inject: "renewal_failures" }, "subscription_renewal_failures");
  }
  await maybe("07-renewals.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/chaos`, { waitUntil: "networkidle" });
    await sleep(3000); // the video trims these first 3 seconds
    const res = await page.request.get(`${DASH}/api/incidents`);
    const items = (await res.json()).items;
    const renewal = items.find((i) => i.playbook === "subscription_renewal_failures") ?? items[0];
    await page.goto(`${DASH}/#/incident/${renewal.id}`, { waitUntil: "networkidle" });
    await sleep(700);
    await page.evaluate(() => window.scrollTo(0, 360));
    await sleep(2200);
  });

  await maybe("08-audit-log.mp4", async (page) => {
    await login(page);
    await page.goto(`${DASH}/#/audit`, { waitUntil: "networkidle" });
    await sleep(2800);
  });
} finally {
  await browser.close();
}

if (existsSync(join(OUT, "_reset.mp4"))) rmSync(join(OUT, "_reset.mp4"));
console.log("done");
