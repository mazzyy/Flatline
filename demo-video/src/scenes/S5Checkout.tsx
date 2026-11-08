import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath } from "@remotion/paths";
import { Background } from "../components/Background";
import { AgentNode } from "../components/AgentNode";
import { Callout } from "../components/Callout";
import { Chip } from "../components/Chip";
import { LowerThird } from "../components/LowerThird";
import { CamKey, ClipBeat, StageFrame, WIDE, cameraAt, cameraStyle, onStage } from "../components/Stage";
import { colors, fonts, layout, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";

export { CLIP_H, CLIP_W } from "../components/Stage";

/**
 * Points inside the clips (clip pixels, 1600x900), measured on the live recording.
 * Re-measure after re-recording: `node scripts/record-clips.mjs` changes them.
 */
export const S5_TARGETS = {
  chaosInject: { x: 1069, y: 347, w: 96, h: 48 },
  shopBanner: { x: 800, y: 22 },
  shopPay: { x: 560, y: 330 },
  overviewTile: { x: 400, y: 486, w: 390, h: 136 },
  overviewIncident: { x: 800, y: 720 },
  timelineRows: { x: 520, y: 640 },
  paypalRead: { x: 520, y: 700 },
  rootCause: { x: 700, y: 230 },
  proposals: { x: 600, y: 420 },
  approve: { x: 300, y: 603 },
};

/** Clip lengths in seconds (after the recorder trims page loading). */
export const CLIP_SECONDS: Record<string, number> = {
  "01-chaos-bad-currency.mp4": 2.6,
  "02-shop-failing.mp4": 3.4,
  "03-incident-opens.mp4": 4.5,
  "04-incident-detail.mp4": 16.3,
  "05-approve.mp4": 3.5,
};

// Beats in scene seconds (scene starts at 26 s in the film).
const A = { from: 0, to: 5.0 }; // chaos panel
const B = { from: 5.0, to: 11.6 }; // shop checkout with the real PayPal button
const C = { from: 11.6, to: 16.0 }; // overview: incident open
const D = { from: 16.0, to: 31.4 }; // incident: timeline, root cause, proposals
const E = { from: 31.4, to: 33.8 }; // approve
const F = { from: 33.8, to: 45.0 }; // recovery

const z = (pt: { x: number; y: number }, s: number, at: number): CamKey => ({ at, s, ...onStage(pt) });

const T = S5_TARGETS;
const CAM: CamKey[] = [
  WIDE(0),
  WIDE(1.0),
  z(T.chaosInject, 1.6, 2.2),
  z(T.chaosInject, 1.6, 4.0),
  WIDE(4.9),
  WIDE(5.6),
  z(T.shopPay, 1.7, 6.6),
  z(T.shopPay, 1.7, 8.2),
  z(T.shopBanner, 1.9, 9.1),
  z(T.shopBanner, 1.9, 10.8),
  WIDE(11.5),
  WIDE(12.2),
  z(T.overviewTile, 1.8, 13.0),
  z(T.overviewIncident, 1.6, 14.6),
  WIDE(15.9),
  WIDE(16.6),
  z(T.timelineRows, 1.7, 17.6),
  z(T.paypalRead, 1.9, 19.2),
  z(T.paypalRead, 1.9, 20.6),
  WIDE(21.6),
  z(T.rootCause, 1.6, 22.6),
  z(T.rootCause, 1.6, 26.4),
  WIDE(27.2),
  z(T.proposals, 1.45, 28.0),
  z(T.proposals, 1.45, 31.0),
  z(T.approve, 1.9, 31.8),
  z(T.approve, 1.9, 33.3),
  WIDE(33.8),
];

export const S5Checkout: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();

  const sec = frame / t(1);
  const cam = cameraAt(CAM, sec);
  const zoomed = cam.s > 1.05;
  const inBeat = (b: { from: number; to: number }) => frame >= t(b.from) - 8 && frame < t(b.to) + 8;
  const beatFade = (b: { from: number; to: number }) => Math.min(ease(frame, t(b.from) - 4, 8), 1 - ease(frame, t(b.to) - 4, 8));
  const label = (b: { from: number; to: number }) => Math.max(0, Math.min(1, 1 - (cam.s - 1.05) / 0.3)) * beatFade(b);

  const stage = (b: { from: number; to: number }, name: string, url: string) => (
    <div style={{ position: "absolute", inset: 0, opacity: beatFade(b) }}>
      <StageFrame url={url} delay={t(b.from) - 4}>
        <ClipBeat name={name} available={Boolean(clips[name])} from={t(b.from)} clipSeconds={CLIP_SECONDS[name]} />
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
  const colX = 1180;
  const colW = 620;

  return (
    <AbsoluteFill>
      <Background glow={frame < t(F.from) ? "critical" : "ok"} glowStrength={0.12} />

      {frame < t(F.from) + 8 ? (
        <div style={{ position: "absolute", inset: 0, ...cameraStyle(cam) }}>
          {inBeat(A) ? stage(A, "01-chaos-bad-currency.mp4", "localhost:8000/#/chaos") : null}
          {inBeat(B) ? stage(B, "02-shop-failing.mp4", "localhost:3000/checkout · PayPal sandbox") : null}
          {inBeat(C) ? stage(C, "03-incident-opens.mp4", "localhost:8000/#/overview") : null}
          {inBeat(D) ? stage(D, "04-incident-detail.mp4", "localhost:8000/#/incident") : null}
          {inBeat(E) ? stage(E, "05-approve.mp4", "localhost:8000/#/incident") : null}

          {inBeat(A) ? (
            <Callout
              label="Ship bad currency config"
              target={onStage(T.chaosInject)}
              at={{ x: onStage(T.chaosInject).x + 200, y: onStage(T.chaosInject).y - 200 }}
              delay={t(1.2)}
              hideAfter={t(4.6)}
              ring={{ w: T.chaosInject.w + 18, h: T.chaosInject.h + 18 }}
              color={colors.warn}
            />
          ) : null}
        </div>
      ) : null}

      {/* Beat labels sit on top of the stage and fade while the camera is close in. */}
      {inBeat(A) && !zoomed ? <LowerThird title="Chaos panel" sub="judge controls · injected events are labelled" delay={t(A.from) + 4} top={110} left={150} /> : null}
      <div style={{ opacity: label(B) }}>
        {inBeat(B) ? <LowerThird title="Lumen Coffee Co. · real PayPal checkout" sub="EUR on a USD shop · captures fail" delay={t(B.from) + 4} top={110} left={150} color={colors.critical} /> : null}
      </div>
      <div style={{ opacity: label(C) }}>
        {inBeat(C) ? <LowerThird title="Incident open" sub="detector · 5-min window vs baseline" delay={t(C.from) + 4} top={110} left={150} color={colors.critical} /> : null}
      </div>
      {inBeat(D) && frame < t(21.4) ? (
        <div style={{ position: "absolute", left: 150, bottom: 70, display: "flex", gap: 12, opacity: ease(frame, t(17.4), 8) * (1 - ease(frame, t(21.0), 8)) }}>
          <Chip text="live models · named per step" delay={t(17.4)} size={type.min} mono color={colors.accent} />
          <Chip text="PayPal reads · MCP" delay={t(17.8)} size={type.min} mono color={colors.accent} />
        </div>
      ) : null}
      {inBeat(D) && frame >= t(22.2) && frame < t(27.0) ? (
        <div style={{ position: "absolute", left: 150, bottom: 70, display: "flex", gap: 12, opacity: ease(frame, t(22.6), 8) * (1 - ease(frame, t(26.6), 8)) }}>
          <Chip text="root cause · from evidence" delay={t(22.6)} size={type.min} mono color={colors.critical} />
        </div>
      ) : null}

      {/* Beat F: recovery */}
      {inBeat(F) ? (
        <div style={{ position: "absolute", inset: 0, opacity: ease(frame, t(F.from), 10) }}>
          <LowerThird title="Checkout failures · last 15 min" sub="injected incident · PayPal sandbox" delay={t(F.from)} top={200} />
          <div style={{ position: "absolute", left: chart.x, top: chart.y, width: chart.w, height: chart.h }}>
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
          </div>
          <div style={{ position: "absolute", left: colX, top: 300 }}>
            <AgentNode x={0} y={0} width={colW} name="Verifier" role="quiet window · metric back at baseline" icon="verify" delay={t(F.from + 1.4)} active={frame >= t(F.from + 2.4)} activeColor={colors.ok} activeDelay={t(F.from + 2.4)} />
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
                opacity: uiSpring(frame, fps, t(F.from + 3.6)),
                translate: `0px ${(1 - uiSpring(frame, fps, t(F.from + 3.6))) * 24}px`,
              }}
            >
              Resolved.
            </div>
            <div style={{ position: "absolute", left: 0, top: 300, display: "flex", flexDirection: "column", gap: 14 }}>
              <Chip text="detected · within seconds" delay={t(F.from + 5.2)} size={type.label} mono color={colors.ok} />
              <Chip text="root cause · under a minute" delay={t(F.from + 5.6)} size={type.label} mono color={colors.ok} />
              <Chip text="fix · one human approval" delay={t(F.from + 6.0)} size={type.label} mono color={colors.ok} />
            </div>
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
