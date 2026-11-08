import type { CaptionSegment } from "./components/CaptionTrack";
import { getTimeline, SceneIndex } from "./timeline";

/**
 * Narration, timed relative to the start of each scene (seconds). Each segment
 * fits two caption lines at 34 px. These double as the voiceover script.
 * Timings come from the generated voice (scripts/audio-v2/build-voiceover-v2.py → narration.json).
 */
export type Narration = { scene: SceneIndex; from: number; to: number; text: string };

export const NARRATION: Narration[] = [
  // S1
  { scene: 0, from: 0.30, to: 4.05, text: "Friday night. Checkout starts failing... and nobody notices." },
  { scene: 0, from: 4.05, to: 6.66, text: "Shops monitor their servers. Not their money." },
  // S2
  { scene: 1, from: 0.25, to: 3.45, text: "Broken checkouts. Refund waves. Failed renewals." },
  { scene: 1, from: 3.45, to: 9.95, text: "One estimate: failed payments could cost subscription companies over $129 billion in 2025." },
  // S3
  { scene: 2, from: 0.30, to: 4.55, text: "So I built Flatline: an on-call AI agent for PayPal revenue." },
  { scene: 2, from: 4.55, to: 7.95, text: "It diagnoses and fixes... but never moves money without asking." },
  // Checkout demo
  { scene: 3, from: 0.30, to: 5.15, text: "Let's break something. I ship a config that switches this US shop to euros." },
  { scene: 3, from: 5.15, to: 11.75, text: "Here's the checkout: euros, on a US shop. Captures fail, and a warning banner is already up." },
  { scene: 3, from: 11.75, to: 16.15, text: "Within seconds, the incident is open, with the money at risk per hour." },
  { scene: 3, from: 16.15, to: 21.55, text: "The AI agents take over. The Diagnostician reads PayPal through MCP..." },
  { scene: 3, from: 21.55, to: 27.15, text: "...compares the config versions with the errors, and finds it: a config change switched the shop to euros." },
  { scene: 3, from: 27.15, to: 31.35, text: "The banner went up on its own. The rollback waits for me." },
  { scene: 3, from: 31.35, to: 34.55, text: "One click... approved!" },
  { scene: 3, from: 34.55, to: 38.35, text: "Failures drop back to baseline, and the Verifier confirms it." },
  { scene: 3, from: 38.35, to: 39.95, text: "Resolved!" },
  { scene: 3, from: 39.95, to: 44.52, text: "Detected in seconds, diagnosed from evidence, fixed with one approval." },
  // How it works
  { scene: 4, from: 0.30, to: 6.75, text: "Under the hood: agents only read. A policy proxy, in plain code, decides. Only the executor writes." },
  { scene: 4, from: 6.75, to: 12.24, text: "Safe fixes run on their own, money waits for a human, and anything else is refused." },
  // Refund wave
  { scene: 5, from: 0.30, to: 2.25, text: "Next, a refund wave." },
  { scene: 5, from: 2.25, to: 9.25, text: "The agents trace it to one product, Ethiopia Yirgacheffe, and propose pausing its sales. That needs my approval." },
  { scene: 5, from: 9.25, to: 14.15, text: "Now I red-team it, and slip a forbidden bulk refund in next to their proposals." },
  { scene: 5, from: 14.15, to: 17.75, text: "Refused! Bulk refunds aren't in the catalog. Full stop." },
  { scene: 5, from: 17.75, to: 19.65, text: "Whoever asks, the code decides." },
  // Renewals
  { scene: 6, from: 0.30, to: 3.75, text: "Then four Coffee Club renewals fail within an hour." },
  { scene: 6, from: 3.75, to: 8.15, text: "The Diagnostician reads the real plan from PayPal, through MCP." },
  { scene: 6, from: 8.15, to: 13.15, text: "The plan is healthy. It's the subscribers' payments, so reminders go out automatically." },
  { scene: 6, from: 13.15, to: 16.90, text: "The agent does the legwork. I keep the final say on money." },
  // Trust
  { scene: 7, from: 0.25, to: 4.95, text: "And it's built to be trusted. It only runs in the PayPal sandbox." },
  { scene: 7, from: 4.95, to: 7.15, text: "Agents never hold write credentials." },
  { scene: 7, from: 7.15, to: 8.95, text: "Unknown actions are forbidden." },
  { scene: 7, from: 8.95, to: 12.95, text: "And every single step lands in the audit log: who did what, and why." },
  { scene: 7, from: 12.95, to: 14.71, text: "Nothing happens in the dark." },
  // Built with
  { scene: 8, from: 0.25, to: 5.35, text: "Built on PayPal's REST APIs, MCP server, and JavaScript SDK..." },
  { scene: 8, from: 5.35, to: 9.95, text: "with Gemini or a local Qwen model, Python, FastAPI and React." },
  // Close
  { scene: 9, from: 0.25, to: 2.43, text: "Flatline. On call for your revenue!" },
];

export const getCaptionSegments = (fps: number, scale: number): CaptionSegment[] => {
  const tl = getTimeline(fps, scale);
  return NARRATION.map((n) => ({
    from: tl.sceneStart[n.scene] + Math.round(n.from * scale * fps),
    to: tl.sceneStart[n.scene] + Math.round(n.to * scale * fps),
    text: n.text,
  }));
};

