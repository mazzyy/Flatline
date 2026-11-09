import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath } from "@remotion/paths";
import { Background } from "../components/Background";
import { AgentNode } from "../components/AgentNode";
import { Chip } from "../components/Chip";
import { Highlight } from "../components/Highlight";
import { LowerThird } from "../components/LowerThird";
import { CamKey, ClipBeat, StageFrame, VIEW, VIEW_LIFT, cameraAt, cameraStyle } from "../components/Stage";
import { colors, fonts, layout, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";

export { CLIP_H, CLIP_W } from "../components/Stage";

/**
 * Boxes inside the clips (clip pixels, 1600x900: left, top, right, bottom), measured on the live
 * recording. Re-measure after re-recording: `node scripts/record-clips.mjs` changes them.
 */
export const S5_BOXES = {
  chaosInject: { x0: 1021, y0: 323, x1: 1117, y1: 371 },
  chaosResult: { x0: 224, y0: 812, x1: 1376, y1: 850 },
  shopPrice: { x0: 350, y0: 236, x1: 470, y1: 272 },
  shopPayPal: { x0: 352, y0: 276, x1: 728, y1: 330 },
  shopBanner: { x0: 360, y0: 4, x1: 1240, y1: 40 },
  overviewTile: { x0: 224, y0: 421, x1: 596, y1: 549 },
  overviewIncident: { x0: 224, y0: 648, x1: 1376, y1: 700 },
  agentRows: { x0: 224, y0: 664, x1: 1376, y1: 826 },
  paypalRead: { x0: 255, y0: 745, x1: 720, y1: 773 },
  rootCause: { x0: 224, y0: 233, x1: 1376, y1: 592 },
  bannerCard: { x0: 224, y0: 116, x1: 1376, y1: 300 },
  rollbackCard: { x0: 224, y0: 316, x1: 1376, y1: 523 },
  approve: { x0: 244, y0: 462, x1: 356, y1: 506 },
  executedCard: { x0: 224, y0: 516, x1: 1376, y1: 729 },
  // 10-shop-fixed.mp4: no banner, so the page sits 44 px higher than in 02
  fixedPrice: { x0: 350, y0: 192, x1: 470, y1: 228 },
  fixedPayPal: { x0: 352, y0: 232, x1: 728, y1: 286 },
};

/** Clip lengths in seconds (after the recorder trims page loading). */
export const CLIP_SECONDS: Record<string, number> = {
  "01-chaos-bad-currency.mp4": 2.56,
  "02-shop-failing.mp4": 4.36,
  "03-incident-opens.mp4": 4.68,
  "04-incident-detail.mp4": 16.12,
  "05-approve.mp4": 2.88,
  "10-shop-fixed.mp4": 3.8,
};

// Beats in scene seconds (scene starts at 26 s in the film).
const A = { from: 0, to: 5.0 }; // chaos panel
const B = { from: 5.0, to: 11.6 }; // shop checkout in EUR, with the agents' banner
const C = { from: 11.6, to: 16.0 }; // overview: incident open
const D = { from: 16.0, to: 31.4 }; // incident: timeline, root cause, proposals
const E = { from: 31.4, to: 34.6 }; // the Approve click; the rollback shows as executed a moment later
const F = { from: 34.6, to: 45.0 }; // recovery
const FIX = { from: 34.6, to: 38.0 }; // the same checkout after the rollback (when 10-shop-fixed.mp4 exists)

// One resting view for every clip: no zooming. The page scrolls on its own and
// highlights point at whatever the narration names.
const CAM: CamKey[] = [VIEW(0)];

export const S5Checkout: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();

  const sec = frame / t(1);
  const cam = cameraAt(CAM, sec);
  const inBeat = (b: { from: number; to: number }) => frame >= t(b.from) - 8 && frame < t(b.to) + 8;
  const beatFade = (b: { from: number; to: number }) => Math.min(ease(frame, t(b.from) - 4, 8), 1 - ease(frame, t(b.to) - 4, 8));
  // A beat's title shows for its first seconds, then gets out of the way of the page.
  const label = (b: { from: number; to: number }) => beatFade(b) * (1 - ease(frame, t(b.from + 2.3), 10));
  const H = (box: keyof typeof S5_BOXES, from: number, to: number, text: string, color: string = colors.accent, side: "above" | "below" | "right" | "inside" = "above") => (
    <Highlight box={S5_BOXES[box]} from={t(from)} to={t(to)} label={text} color={color} labelSide={side} />
  );

  const stage = (b: { from: number; to: number }, name: string, url: string, startAt = 0, playAt = b.from) => (
    <div style={{ position: "absolute", inset: 0, opacity: beatFade(b) }}>
      <StageFrame url={url} delay={t(b.from) - 4}>
        <ClipBeat name={name} available={Boolean(clips[name])} from={t(playAt)} clipSeconds={CLIP_SECONDS[name]} startAt={startAt} />
      </StageFrame>
    </div>
  );

  // Recovery chart (beat F), in local SVG coordinates
  const chart = { x: layout.marginX, y: 300, w: 1000, h: 300 };
  const base = chart.h - 50;
  const chartD = `M 0 ${base} L 240 ${base - 4} L 330 40 L 520 48 L 640 56 L 760 ${base - 6} L ${chart.w} ${base - 2}`;
  const chartP = ease(frame, t(F.from + 0.4), t(2.6));
  const chartEvolved = evolvePath(chartP, chartD);
  const approveX = 760;
  // With the real after shot the drawn chart goes, and the Verifier card follows it, centred.
  const fixed = Boolean(clips["10-shop-fixed.mp4"]);
  const R = fixed ? { from: FIX.to, to: F.to } : F;
  const rt = (off: number, fixedOff: number) => t(R.from + (fixed ? fixedOff : off));
  const colW = 620;
  const colX = fixed ? (1920 - colW) / 2 : 1180;
  const stageEnd = fixed ? FIX.to : F.from;

  return (
    <AbsoluteFill>
      <Background glow={frame < t(F.from) ? "critical" : "ok"} glowStrength={0.12} />

      {frame < t(stageEnd) + 8 ? (
        <div style={{ position: "absolute", inset: 0, ...cameraStyle(cam, VIEW_LIFT) }}>
          {inBeat(A) ? stage(A, "01-chaos-bad-currency.mp4", "localhost:8000/#/chaos", 0.75, 0.7) : null}
          {inBeat(B) ? stage(B, "02-shop-failing.mp4", "localhost:3000/checkout · PayPal sandbox") : null}
          {inBeat(C) ? stage(C, "03-incident-opens.mp4", "localhost:8000/#/overview") : null}
          {inBeat(D) ? stage(D, "04-incident-detail.mp4", "localhost:8000/#/incident") : null}
          {inBeat(E) ? stage(E, "05-approve.mp4", "localhost:8000/#/incident") : null}
          {fixed && inBeat(FIX) ? stage(FIX, "10-shop-fixed.mp4", "localhost:3000/checkout · PayPal sandbox") : null}

          {/* What to look at, in step with the narration (scene seconds). */}
          {inBeat(A) ? H("chaosInject", 0.6, 2.3, "Inject: EUR on a USD shop", colors.warn, "right") : null}
          {inBeat(A) ? H("chaosResult", 2.6, 4.7, "6 synthetic events, labelled as injected") : null}
          {inBeat(B) ? H("shopPrice", 6.0, 7.6, "EUR on a USD shop", colors.critical, "right") : null}
          {inBeat(B) ? H("shopPayPal", 7.6, 9.1, "the real PayPal button, sandbox", colors.accent, "right") : null}
          {inBeat(B) ? H("shopBanner", 9.1, 11.3, "banner written by the agents", colors.ok, "below") : null}
          {inBeat(C) ? H("overviewTile", 12.6, 14.2, "checkout failures · breach", colors.critical, "right") : null}
          {inBeat(C) ? H("overviewIncident", 14.2, 15.8, "money at risk per hour", colors.critical) : null}
          {inBeat(D) ? H("agentRows", 17.0, 18.8, "each step names its model and latency") : null}
          {inBeat(D) ? H("paypalRead", 18.8, 20.9, "PayPal read through MCP", colors.accent, "right") : null}
          {inBeat(D) ? H("rootCause", 22.0, 26.8, "root cause, with cited evidence", colors.critical, "inside") : null}
          {inBeat(D) ? H("bannerCard", 27.6, 29.0, "banner · ran on its own", colors.ok, "inside") : null}
          {inBeat(D) ? H("rollbackCard", 29.0, 31.3, "rollback · waits for my approval", colors.warn, "inside") : null}
          {inBeat(E) ? H("approve", 31.5, 32.45, "one click", colors.warn, "right") : null}
          {inBeat(E) ? H("executedCard", 32.7, 34.5, "rollback executed", colors.ok, "inside") : null}
          {fixed && inBeat(FIX) ? H("fixedPrice", 35.0, 36.5, "back to USD, banner gone", colors.ok, "right") : null}
          {fixed && inBeat(FIX) ? H("fixedPayPal", 36.5, 37.9, "PayPal button ready to take payments", colors.ok, "right") : null}
        </div>
      ) : null}

      {/* Beat titles: on screen for each beat's first seconds. */}
      <div style={{ opacity: label(A) }}>
        {inBeat(A) ? <LowerThird title="Chaos panel" sub="judge controls · injected events are labelled" delay={t(A.from) + 4} top={110} left={150} backdrop /> : null}
      </div>
      <div style={{ opacity: label(B) }}>
        {inBeat(B) ? <LowerThird title="Lumen Coffee Co. · PayPal checkout, sandbox" sub="EUR on a USD shop · captures fail" delay={t(B.from) + 4} top={110} left={150} color={colors.critical} backdrop /> : null}
      </div>
      <div style={{ opacity: label(C) }}>
        {inBeat(C) ? <LowerThird title="Incident open" sub="detector · 5-min window vs baseline" delay={t(C.from) + 4} top={110} left={150} color={colors.critical} backdrop /> : null}
      </div>
      <div style={{ opacity: fixed ? label(FIX) : 0 }}>
        {fixed && inBeat(FIX) ? <LowerThird title="Lumen Coffee Co. · after the rollback" sub="the same checkout, seconds later" delay={t(FIX.from) + 4} top={110} left={150} color={colors.ok} backdrop /> : null}
      </div>
      <div style={{ opacity: label(D) }}>
        {inBeat(D) ? <LowerThird title="Incident · the agents at work" sub="every step persisted with its input and output" delay={t(D.from) + 4} top={110} left={150} color={colors.accent} backdrop /> : null}
      </div>

      {/* Beat F: recovery */}
      {inBeat(R) ? (
        <div style={{ position: "absolute", inset: 0, opacity: ease(frame, t(R.from), 10) }}>
          {fixed ? null : <LowerThird title="After the rollback" sub="the Verifier waits for a quiet window" delay={t(F.from)} top={200} />}
          {fixed ? null : <div style={{ position: "absolute", left: chart.x, top: chart.y, width: chart.w, height: chart.h }}>
            <svg width={chart.w} height={chart.h} style={{ overflow: "visible" }}>
              <line x1={0} y1={base} x2={chart.w} y2={base} stroke={colors.line} strokeDasharray="6 8" />
              <text x={0} y={base + 36} fill={colors.textMuted} fontFamily={fonts.mono} fontSize={type.min}>
                baseline · 1 failure / 5 min
              </text>
              <line x1={approveX} y1={20} x2={approveX} y2={base} stroke={colors.ok} strokeDasharray="4 8" opacity={ease(frame, t(F.from + 2.0), 10)} />
              <text x={approveX + 12} y={40} fill={colors.ok} fontFamily={fonts.mono} fontSize={type.min} opacity={ease(frame, t(F.from + 2.0), 10)}>
                rollback approved
              </text>
              <path
                d={chartD}
                fill="none"
                stroke={colors.critical}
                strokeWidth={5}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={chartEvolved.strokeDasharray}
                strokeDashoffset={chartEvolved.strokeDashoffset}
              />
            </svg>
          </div>}
          <div style={{ position: "absolute", left: colX, top: fixed ? 260 : 300 }}>
            <AgentNode x={0} y={0} width={colW} name="Verifier" role="quiet window · metric back at baseline" icon="verify" delay={rt(1.4, 0)} active={frame >= rt(2.4, 0.2)} activeColor={colors.ok} activeDelay={rt(2.4, 0.2)} />
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 150,
                fontFamily: fonts.headline,
                fontWeight: 700,
                fontSize: type.h1Small,
                letterSpacing: "-0.02em",
                color: colors.ok,
                opacity: uiSpring(frame, fps, rt(3.6, 0.4)),
                translate: `0px ${(1 - uiSpring(frame, fps, rt(3.6, 0.4))) * 24}px`,
              }}
            >
              Resolved.
            </div>
            <div style={{ position: "absolute", left: 0, top: 300, display: "flex", flexDirection: "column", gap: 14 }}>
              <Chip text="detected · within seconds" delay={rt(5.2, 2.0)} size={type.label} mono color={colors.ok} />
              <Chip text="root cause · from evidence" delay={rt(5.6, 2.4)} size={type.label} mono color={colors.ok} />
              <Chip text="fix · one human approval" delay={rt(6.0, 2.8)} size={type.label} mono color={colors.ok} />
            </div>
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
