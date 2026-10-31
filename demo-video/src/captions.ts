import type { CaptionSegment } from "./components/CaptionTrack";
import { getTimeline, SceneIndex } from "./timeline";
import { product } from "./theme";

/**
 * Narration, timed relative to the start of each scene (seconds). Each segment
 * fits two caption lines at 34 px. These double as the voiceover script.
 */
export type Narration = { scene: SceneIndex; from: number; to: number; text: string };

export const NARRATION: Narration[] = [
  // S1
  { scene: 0, from: 0.6, to: 5.6, text: "Every online shop monitors its servers." },
  { scene: 0, from: 6.0, to: 11.4, text: "Almost none monitor their money." },
  // S2
  { scene: 1, from: 0.4, to: 6.2, text: "When a checkout breaks on a Friday evening, or refunds suddenly spike," },
  { scene: 1, from: 6.4, to: 14.6, text: "most merchants find out days later, from a payout report or an angry customer." },
  // S3
  { scene: 2, from: 0.8, to: 8.5, text: `This is ${product.name}: an on-call SRE agent for your PayPal revenue.` },
  // S4
  { scene: 3, from: 0.4, to: 4.4, text: "It listens to PayPal webhooks and checkout telemetry." },
  { scene: 3, from: 4.6, to: 8.2, text: "When a metric breaks its baseline, four agents take over." },
  { scene: 3, from: 8.4, to: 10.6, text: "Triage scopes the incident." },
  { scene: 3, from: 10.8, to: 15.6, text: "The Diagnostician reads PayPal data through a read-only MCP server and finds the root cause." },
  { scene: 3, from: 15.8, to: 18.0, text: "The Remediator proposes fixes." },
  { scene: 3, from: 18.2, to: 22.2, text: "And every proposal goes through a policy proxy written in plain code, not a prompt." },
  { scene: 3, from: 22.4, to: 24.8, text: "Only the executor behind it can write." },
  // S5
  { scene: 4, from: 0.4, to: 4.2, text: "Let's break something. I ship a bad currency config." },
  { scene: 4, from: 7.2, to: 12.4, text: "Checkouts start failing, and within seconds an incident opens." },
  { scene: 4, from: 14.4, to: 20.4, text: "The Diagnostician points to the exact config version that caused it, with evidence." },
  { scene: 4, from: 20.6, to: 23.6, text: "A warning banner goes up automatically." },
  { scene: 4, from: 23.8, to: 26.4, text: "The rollback needs my approval." },
  { scene: 4, from: 27.2, to: 33.6, text: "I approve, failures stop, and the Verifier confirms recovery." },
  // S6
  { scene: 5, from: 0.4, to: 2.8, text: "Now a refund wave." },
  { scene: 5, from: 3.0, to: 9.0, text: "The agent finds one product behind most of the refunds and proposes pausing it." },
  { scene: 5, from: 10.0, to: 13.0, text: "It also tries a bulk refund." },
  { scene: 5, from: 13.8, to: 16.6, text: "The policy says no." },
  { scene: 5, from: 19.8, to: 23.8, text: "Agents can ask; code decides." },
  // S7
  { scene: 6, from: 0.4, to: 6.2, text: "For failed subscription renewals, a reminder goes out on its own." },
  { scene: 6, from: 6.6, to: 12.4, text: "Capturing the outstanding balance waits for a human." },
  // S8
  { scene: 7, from: 0.4, to: 4.8, text: "It runs only in the PayPal sandbox," },
  { scene: 7, from: 5.0, to: 8.6, text: "agents never hold write credentials," },
  { scene: 7, from: 8.8, to: 13.4, text: "and every step is in the audit log." },
  // S9
  { scene: 8, from: 0.4, to: 8.4, text: "Built on PayPal's REST APIs, MCP server and JavaScript SDK, with Azure-hosted models." },
  // S10
  { scene: 9, from: 0.3, to: 4.2, text: `${product.name}. On call for your revenue.` },
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
