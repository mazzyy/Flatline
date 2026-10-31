import type { CaptionSegment } from "./components/CaptionTrack";
import { getTimeline, SceneIndex } from "./timeline";
import { product } from "./theme";

/**
 * Narration, timed relative to the start of each scene (seconds). Each segment
 * fits two caption lines at 34 px. These double as the voiceover script.
 * Timings come from the generated voice (scripts/build-voiceover-v2.py → narration.json).
 */
export type Narration = { scene: SceneIndex; from: number; to: number; text: string };

export const NARRATION: Narration[] = [
  // S1
  { scene: 0, from: 0.30, to: 4.97, text: "Friday night. Checkout starts failing... one error, then ten, then a hundred!" },
  { scene: 0, from: 5.25, to: 8.75, text: "And nobody notices. Because nobody is on call for revenue!" },
  { scene: 0, from: 8.75, to: 11.28, text: "Shops monitor their servers... not their money." },
  // S2
  { scene: 1, from: 0.25, to: 3.55, text: "A broken checkout. A refund wave. A failing renewal." },
  { scene: 1, from: 3.55, to: 8.78, text: "Every hour nobody notices, money quietly leaks away. Look at that number climb!" },
  { scene: 1, from: 9.25, to: 15.37, text: "And most merchants? They only find out days later, from a payout report, or an angry customer!" },
  // S3
  { scene: 2, from: 0.25, to: 1.55, text: `That's why I built ${product.name}!` },
  { scene: 2, from: 1.55, to: 4.55, text: "An on-call SRE agent, for your PayPal revenue." },
  { scene: 2, from: 4.55, to: 7.52, text: "It detects, diagnoses, and fixes... safely." },
  { scene: 2, from: 7.55, to: 11.42, text: "Like a teammate who never sleeps, and never moves money without asking." },
  // S4
  { scene: 3, from: 0.35, to: 4.65, text: `Here's how it works. ${product.name} listens to PayPal webhooks and checkout telemetry.` },
  { scene: 3, from: 4.65, to: 8.15, text: "The moment a metric breaks its baseline... boom! Incident open." },
  { scene: 3, from: 8.15, to: 10.95, text: "Four agents jump in. Triage scopes the damage." },
  { scene: 3, from: 10.95, to: 15.95, text: "The Diagnostician finds the root cause, reading PayPal data through MCP." },
  { scene: 3, from: 15.95, to: 17.65, text: "The Remediator proposes a fix." },
  { scene: 3, from: 17.65, to: 21.55, text: "Every proposal hits a policy proxy. Plain code, not a prompt!" },
  { scene: 3, from: 21.55, to: 25.02, text: "Agents read. Code decides. Only the executor writes!" },
  // S5
  { scene: 4, from: 0.25, to: 3.95, text: "Okay, let's break something! I'm shipping a bad currency config." },
  { scene: 4, from: 3.95, to: 7.25, text: "Euros, on a US-dollar shop. What could possibly go wrong?" },
  { scene: 4, from: 7.25, to: 10.75, text: "Checkouts start failing, and within seconds, the incident is open!" },
  { scene: 4, from: 10.75, to: 13.33, text: "And look! The shop already shows a warning banner." },
  { scene: 4, from: 13.95, to: 17.02, text: "Triage scopes it, and the Diagnostician goes hunting..." },
  { scene: 4, from: 17.15, to: 20.15, text: "Found it! Config version two set the wrong currency." },
  { scene: 4, from: 20.25, to: 22.47, text: "The banner? Already handled, automatically." },
  { scene: 4, from: 23.15, to: 25.66, text: "But rolling back the config? That needs me." },
  { scene: 4, from: 25.85, to: 27.44, text: "One click... approved!" },
  { scene: 4, from: 29.15, to: 32.75, text: "Failures drop right back to baseline, and the Verifier confirms it." },
  { scene: 4, from: 32.75, to: 33.79, text: "Resolved!" },
  // S6
  { scene: 5, from: 0.15, to: 1.75, text: "Next up: a refund wave!" },
  { scene: 5, from: 1.75, to: 6.43, text: "One product, the Ethiopia Yirgacheffe, is behind most of the refunds." },
  { scene: 5, from: 6.65, to: 11.28, text: "So it proposes pausing sales of that product, and that waits for my approval." },
  { scene: 5, from: 11.55, to: 14.20, text: "Then it gets bold... and tries a bulk refund!" },
  { scene: 5, from: 14.35, to: 17.12, text: "Refused! Bulk refunds are forbidden, full stop." },
  { scene: 5, from: 19.25, to: 21.58, text: "The agent asked. The policy said no." },
  { scene: 5, from: 21.75, to: 24.00, text: "Agents can ask... but code decides!" },
  // S7
  { scene: 6, from: 0.25, to: 3.13, text: "Now, four subscription renewals fail within an hour." },
  { scene: 6, from: 3.35, to: 5.63, text: "A payment reminder goes out automatically." },
  { scene: 6, from: 5.95, to: 9.42, text: "But capturing the outstanding balance? That waits for a human." },
  { scene: 6, from: 9.45, to: 13.38, text: "Small fixes run on their own. Money only moves with a human!" },
  // S8
  { scene: 7, from: 0.25, to: 4.47, text: "And it's built to be trusted. It only runs in the PayPal sandbox." },
  { scene: 7, from: 4.95, to: 7.10, text: "Agents never hold write credentials." },
  { scene: 7, from: 7.15, to: 8.83, text: "Unknown actions are forbidden." },
  { scene: 7, from: 8.95, to: 12.95, text: "And every single step lands in the audit log: who did what, and why." },
  { scene: 7, from: 12.95, to: 14.56, text: "Nothing happens in the dark." },
  // S9
  { scene: 8, from: 0.25, to: 5.35, text: "Built on PayPal's REST APIs, MCP server, and JavaScript SDK..." },
  { scene: 8, from: 5.35, to: 9.13, text: "with Azure OpenAI, Python, FastAPI and React." },
  // S10
  { scene: 9, from: 0.25, to: 2.28, text: `${product.name}. On call for your revenue!` },
];

export const getCaptionSegments = (fps: number, scale: number): CaptionSegment[] => {
  const tl = getTimeline(fps, scale);
  return NARRATION.map((n) => ({
    from: tl.sceneStart[n.scene] + Math.round(n.from * scale * fps),
    to: tl.sceneStart[n.scene] + Math.round(n.to * scale * fps),
    text: n.text,
  }));
};

/** Plain-text script for recording the voiceover. */
export const SCRIPT = NARRATION.map((n) => n.text).join("\n");
