/**
 * Build a 170s voiceover aligned to the burned-in captions, then mux it
 * onto a clone of out/demo-video.mp4.
 */
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = join(import.meta.dirname, "..");
const TMP = join(ROOT, "out", "vo-parts");
const VOICE = "Daniel";
const RATE = 180; // words/min; clear, not rushed
const TOTAL = 170;

const SCENES = [0, 12, 28, 40, 65, 100, 125, 140, 155, 165];

const LINES = [
  { scene: 0, from: 0.6, to: 5.6, text: "Every online shop monitors its servers." },
  { scene: 0, from: 6.0, to: 11.4, text: "Almost none monitor their money." },
  { scene: 1, from: 0.4, to: 6.2, text: "When a checkout breaks on a Friday evening, or refunds suddenly spike," },
  { scene: 1, from: 6.4, to: 14.6, text: "most merchants find out days later, from a payout report or an angry customer." },
  { scene: 2, from: 0.8, to: 8.5, text: "This is Flatline: an on-call S.R.E. agent for your PayPal revenue." },
  { scene: 3, from: 0.4, to: 4.4, text: "It listens to PayPal webhooks and checkout telemetry." },
  { scene: 3, from: 4.6, to: 8.2, text: "When a metric breaks its baseline, four agents take over." },
  { scene: 3, from: 8.4, to: 10.6, text: "Triage scopes the incident." },
  { scene: 3, from: 10.8, to: 15.6, text: "The Diagnostician reads PayPal data through a read-only M.C.P. server and finds the root cause." },
  { scene: 3, from: 15.8, to: 18.0, text: "The Remediator proposes fixes." },
  { scene: 3, from: 18.2, to: 22.2, text: "And every proposal goes through a policy proxy written in plain code, not a prompt." },
  { scene: 3, from: 22.4, to: 24.8, text: "Only the executor behind it can write." },
  { scene: 4, from: 0.4, to: 4.2, text: "Let's break something. I ship a bad currency config." },
  { scene: 4, from: 7.2, to: 12.4, text: "Checkouts start failing, and within seconds an incident opens." },
  { scene: 4, from: 14.4, to: 20.4, text: "The Diagnostician points to the exact config version that caused it, with evidence." },
  { scene: 4, from: 20.6, to: 23.6, text: "A warning banner goes up automatically." },
  { scene: 4, from: 23.8, to: 26.4, text: "The rollback needs my approval." },
  { scene: 4, from: 27.2, to: 33.6, text: "I approve, failures stop, and the Verifier confirms recovery." },
  { scene: 5, from: 0.4, to: 2.8, text: "Now a refund wave." },
  { scene: 5, from: 3.0, to: 9.0, text: "The agent finds one product behind most of the refunds and proposes pausing it." },
  { scene: 5, from: 10.0, to: 13.0, text: "It also tries a bulk refund." },
  { scene: 5, from: 13.8, to: 16.6, text: "The policy says no." },
  { scene: 5, from: 19.8, to: 23.8, text: "Agents can ask; code decides." },
  { scene: 6, from: 0.4, to: 6.2, text: "For failed subscription renewals, a reminder goes out on its own." },
  { scene: 6, from: 6.6, to: 12.4, text: "Capturing the outstanding balance waits for a human." },
  { scene: 7, from: 0.4, to: 4.8, text: "It runs only in the PayPal sandbox," },
  { scene: 7, from: 5.0, to: 8.6, text: "agents never hold write credentials," },
  { scene: 7, from: 8.8, to: 13.4, text: "and every step is in the audit log." },
  { scene: 8, from: 0.4, to: 8.4, text: "Built on PayPal's REST A.P.I.s, M.C.P. server and JavaScript S.D.K., with Azure-hosted models." },
  { scene: 9, from: 0.3, to: 4.2, text: "Flatline. On call for your revenue." },
];

const run = (cmd, args) => {
  const r = spawnSync(cmd, args, { stdio: ["ignore", "pipe", "pipe"] });
  if (r.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")}\n${r.stderr?.toString()}`);
  }
  return r;
};

const duration = (file) => {
  const r = spawnSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", file], {
    encoding: "utf8",
  });
  return parseFloat(r.stdout.trim());
};

rmSync(TMP, { recursive: true, force: true });
mkdirSync(TMP, { recursive: true });
mkdirSync(join(ROOT, "public", "audio"), { recursive: true });
mkdirSync(join(ROOT, "out"), { recursive: true });

const inputs = [];
const filters = [];

for (let i = 0; i < LINES.length; i++) {
  const line = LINES[i];
  const start = SCENES[line.scene] + line.from;
  const slot = line.to - line.from;
  const aiff = join(TMP, `${String(i).padStart(2, "0")}.aiff`);
  const wav = join(TMP, `${String(i).padStart(2, "0")}.wav`);
  run("say", ["-v", VOICE, "-r", String(RATE), "-o", aiff, line.text]);
  run("ffmpeg", ["-y", "-i", aiff, "-ar", "48000", "-ac", "1", wav]);
  let d = duration(wav);
  let src = wav;
  if (d > slot - 0.08) {
    const speed = Math.min(1.35, d / (slot - 0.08));
    const fit = join(TMP, `${String(i).padStart(2, "0")}-fit.wav`);
    run("ffmpeg", ["-y", "-i", wav, "-filter:a", `atempo=${speed.toFixed(3)}`, fit]);
    src = fit;
    d = duration(fit);
  }
  console.log(`${i.toString().padStart(2, "0")}  ${start.toFixed(1).padStart(6)}s  ${d.toFixed(2)}s / ${slot.toFixed(1)}s  ${line.text.slice(0, 64)}`);
  const delayMs = Math.round(start * 1000);
  inputs.push("-i", src);
  filters.push(`[${i}:a]adelay=${delayMs}|${delayMs},apad=whole_dur=${TOTAL}[a${i}]`);
}

const mixInputs = LINES.map((_, i) => `[a${i}]`).join("");
filters.push(`${mixInputs}amix=inputs=${LINES.length}:normalize=0:duration=longest,volume=2.4[out]`);

const filterPath = join(TMP, "filter.txt");
writeFileSync(filterPath, filters.join(";\n"));

const mixed = join(ROOT, "public", "audio", "voiceover.mp3");
run("ffmpeg", [
  "-y",
  ...inputs,
  "-filter_complex_script",
  filterPath,
  "-map",
  "[out]",
  "-ar",
  "48000",
  "-ac",
  "1",
  "-b:a",
  "192k",
  mixed,
]);

const silentMaster = join(ROOT, "out", "demo-video.mp4");
const voiced = join(ROOT, "out", "demo-video-vo.mp4");
run("ffmpeg", [
  "-y",
  "-i",
  silentMaster,
  "-i",
  mixed,
  "-c:v",
  "copy",
  "-c:a",
  "aac",
  "-b:a",
  "192k",
  "-map",
  "0:v:0",
  "-map",
  "1:a:0",
  "-shortest",
  voiced,
]);

console.log("voiceover", mixed);
console.log("clone", voiced);
