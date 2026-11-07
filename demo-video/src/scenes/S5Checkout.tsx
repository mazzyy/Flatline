import React from "react";
import { AbsoluteFill, Easing, useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath } from "@remotion/paths";
import { Background } from "../components/Background";
import { BrowserFrame } from "../components/BrowserFrame";
import { Clip } from "../components/Clip";
import { Callout } from "../components/Callout";
import { LowerThird } from "../components/LowerThird";
import { IncidentCard } from "../components/IncidentCard";
import { TierBadge } from "../components/TierBadge";
import { AgentNode } from "../components/AgentNode";
import { Chip } from "../components/Chip";
import { colors, fonts, layout, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";

/** Clips are recorded at this viewport; callout targets below are in clip pixels. */
export const CLIP_W = 1600;
export const CLIP_H = 900;

/** Target points inside each clip (clip pixel space). Adjust per recording. */
export const S5_TARGETS = {
  chaosButton: { x: 1180, y: 360, w: 140, h: 52 },
  overviewTile: { x: 280, y: 500, w: 440, h: 160 },
  /** Centre and size of the checkout-failure tile itself (ring while zoomed). */
  overviewTileBox: { x: 400, y: 486, w: 390, h: 136 },
  banner: { x: 800, y: 28, w: 900, h: 40 },
  approve: { x: 160, y: 490 },
  triageRow: { x: 220, y: 730 },
  diagRow: { x: 220, y: 780 },
};

const toScene = (frame: { x: number; y: number; w: number }, pt: { x: number; y: number }) => {
  const s = frame.w / CLIP_W;
  return { x: frame.x + pt.x * s, y: frame.y + 44 + pt.y * s };
};

/**
 * Beat B camera: push in on the overview's checkout-failure tile while the
 * narration says the incident is open, glide to the shop's warning banner for
 * "And look!", then pull back out before beat C. Keyframes in scene seconds.
 */
type CamKey = { at: number; s: number; x: number; y: number };
const CAM_B: CamKey[] = [
  { at: 8.4, s: 1, x: 960, y: 540 },
  { at: 9.25, s: 2.3, x: 1300, y: 580 }, // checkout failure tile + incident row
  { at: 10.7, s: 2.3, x: 1300, y: 580 },
  { at: 11.6, s: 2.8, x: 520, y: 330 }, // shop warning banner
  { at: 13.0, s: 2.8, x: 520, y: 330 },
  { at: 13.8, s: 1, x: 960, y: 540 },
];
const camEase = Easing.bezier(0.65, 0, 0.35, 1);

const cameraAt = (sec: number): { s: number; x: number; y: number } => {
  if (sec <= CAM_B[0].at) return CAM_B[0];
  for (let i = 0; i < CAM_B.length - 1; i++) {
    const a = CAM_B[i];
    const b = CAM_B[i + 1];
    if (sec <= b.at) {
      const e = camEase((sec - a.at) / (b.at - a.at));
      // zoom in log space; dip out a little when travelling between two close-ups
      const travelling = a.s > 1.01 && b.s > 1.01 && (a.x !== b.x || a.y !== b.y);
      const logS = Math.log(a.s) + (Math.log(b.s) - Math.log(a.s)) * e - (travelling ? 0.45 * Math.sin(Math.PI * e) : 0);
      return { s: Math.exp(logS), x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e };
    }
  }
  return CAM_B[CAM_B.length - 1];
};

export const S5Checkout: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();

  // Beats (seconds)
  const A = { from: 0, to: 7 };
  const B = { from: 7, to: 14 };
  const C = { from: 14, to: 24 };
  const D = { from: 24, to: 29 };
  const E = { from: 29, to: 35 };
  const inBeat = (b: { from: number; to: number }) => frame >= t(b.from) && frame < t(b.to) + 8;
  const beatFade = (b: { from: number; to: number }) =>
    Math.min(ease(frame, t(b.from), 10), 1 - ease(frame, t(b.to) - 6, 8));

  const frameA = { x: 280, y: 100, w: 1360 };
  const frameL = { x: layout.marginX, y: 250, w: 800 };
  const frameR = { x: 1000, y: 250, w: 800 };
  const frameC = { x: layout.marginX, y: 120, w: 1000 };
  const colX = 1180;
  const colW = 620;

  const chaosT = toScene(frameA, S5_TARGETS.chaosButton);
  const tileT = toScene(frameR, S5_TARGETS.overviewTile);
  const triageT = toScene(frameC, S5_TARGETS.triageRow);
  const diagT = toScene(frameC, S5_TARGETS.diagRow);

  // Recovery chart (beat E), in local SVG coordinates
  const chart = { x: layout.marginX, y: 300, w: 1000, h: 300 };
  const base = chart.h - 50;
  const chartD = `M 0 ${base} L 240 ${base - 4} L 330 40 L 520 48 L 640 56 L 760 ${base - 6} L ${chart.w} ${base - 2}`;
  const chartP = ease(frame, t(29.4), t(2.6));
  const chartEvolved = evolvePath(chartP, chartD);
  const approveX = 760; // where the rollback was approved

  const cam = cameraAt(frame / t(1));
  const camStyle: React.CSSProperties = {
    transformOrigin: "0 0",
    transform: `translate(${960 - cam.s * cam.x}px, ${540 - cam.s * cam.y}px) scale(${cam.s})`,
  };
  // Callout pills sit below the frames; hide them while the camera is close in.
  const camLabel = Math.max(0, Math.min(1, 1 - (cam.s - 1.05) / 0.35));

  return (
    <AbsoluteFill>
      <Background glow={frame < t(E.from) ? "critical" : "ok"} glowStrength={0.14} />

      {/* Beat A: chaos panel */}
      {inBeat(A) ? (
        <div style={{ position: "absolute", inset: 0, opacity: beatFade(A) }}>
          <LowerThird title="Chaos panel" sub="judge controls · synthetic events are labelled" delay={t(0.2)} top={30} />
          <BrowserFrame x={frameA.x} y={frameA.y} width={frameA.w} height={44 + (frameA.w * CLIP_H) / CLIP_W} url="localhost:8000/#/chaos" delay={t(0.1)} pushInFrames={t(7)}>
            <Clip name="01-chaos-bad-currency.mp4" available={Boolean(clips["01-chaos-bad-currency.mp4"])} />
          </BrowserFrame>
          <Callout label="Ship bad currency config" target={chaosT} at={{ x: chaosT.x + 240, y: chaosT.y - 160 }} delay={t(1.6)} ring={{ w: S5_TARGETS.chaosButton.w * (frameA.w / CLIP_W) + 16, h: S5_TARGETS.chaosButton.h * (frameA.w / CLIP_W) + 16 }} color={colors.warn} />
        </div>
      ) : null}

      {/* Beat B: split shop / overview */}
      {inBeat(B) ? (
        <div style={{ position: "absolute", inset: 0, opacity: beatFade(B), ...camStyle }}>
          <LowerThird title="Lumen Coffee Co." sub="checkout fails · CURRENCY_MISMATCH" delay={t(B.from) + 4} top={150} color={colors.critical} />
          <LowerThird title="Overview" sub="incident opens within seconds" delay={t(B.from) + 10} top={150} left={frameR.x} />
          <BrowserFrame x={frameL.x} y={frameL.y} width={frameL.w} height={44 + (frameL.w * CLIP_H) / CLIP_W} url="localhost:3000" delay={t(B.from)} pushInFrames={t(7)}>
            <Clip name="02-shop-failing.mp4" available={Boolean(clips["02-shop-failing.mp4"])} />
          </BrowserFrame>
          <BrowserFrame x={frameR.x} y={frameR.y} width={frameR.w} height={44 + (frameR.w * CLIP_H) / CLIP_W} url="localhost:8000/#/overview" delay={t(B.from) + 6} pushInFrames={t(7)}>
            <Clip name="03-incident-opens.mp4" available={Boolean(clips["03-incident-opens.mp4"])} />
          </BrowserFrame>
          <Callout label="Banner is already up" target={toScene(frameL, S5_TARGETS.banner)} at={{ x: frameL.x + 40, y: frameL.y + 44 + (frameL.w * CLIP_H) / CLIP_W + 50 }} delay={t(10.9)} color={colors.warn} labelOpacity={camLabel} />
          <Callout label="Checkout tile · breach" target={tileT} at={{ x: frameR.x + 40, y: frameR.y + 44 + (frameR.w * CLIP_H) / CLIP_W + 50 }} delay={t(9.0)} color={colors.critical} labelOpacity={camLabel} ringAt={toScene(frameR, S5_TARGETS.overviewTileBox)} ring={{ w: S5_TARGETS.overviewTileBox.w * (frameR.w / CLIP_W) + 16, h: S5_TARGETS.overviewTileBox.h * (frameR.w / CLIP_W) + 16 }} />
        </div>
      ) : null}

      {/* Beat C + D: incident detail, root cause, proposals, approve */}
      {inBeat(C) || inBeat(D) ? (
        <div style={{ position: "absolute", inset: 0, opacity: Math.min(ease(frame, t(C.from), 10), 1 - ease(frame, t(D.to) - 6, 8)) }}>
          <BrowserFrame x={frameC.x} y={frameC.y} width={frameC.w} height={44 + (frameC.w * CLIP_H) / CLIP_W} url="localhost:8000/#/incident" delay={t(C.from)} pushInFrames={t(15)}>
            <div style={{ position: "absolute", inset: 0, opacity: 1 - ease(frame, t(D.from), 8) }}>
              <Clip name="04-incident-detail.mp4" available={Boolean(clips["04-incident-detail.mp4"])} />
            </div>
            {frame >= t(D.from) - 8 ? (
              <div style={{ position: "absolute", inset: 0, opacity: ease(frame, t(D.from), 8) }}>
                <Clip name="05-approve.mp4" available={Boolean(clips["05-approve.mp4"])} />
              </div>
            ) : null}
          </BrowserFrame>

          {/* Agent timeline callouts */}
          <Callout label="Triage · scope and severity" target={triageT} at={{ x: colX, y: 760 }} delay={t(14.8)} hideAfter={t(17.6)} />
          <Callout label="Diagnostician · root cause" target={diagT} at={{ x: colX, y: 840 }} delay={t(16.0)} hideAfter={t(17.6)} />

          {/* Root cause pull-out */}
          {frame >= t(17.4) ? (
            <IncidentCard x={colX} y={frameC.y} width={colW} sub="root cause · from evidence" title="Config version 2 introduced the wrong currency." delay={t(17.4)} big>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 20 }}>
                {["config v2 · EUR on a USD shop", "6 failed captures", "CURRENCY_MISMATCH"].map((c, i) => (
                  <Chip key={c} text={c} delay={t(18.2) + i * 5} size={type.min} mono color={colors.critical} />
                ))}
              </div>
            </IncidentCard>
          ) : null}

          {/* Proposals */}
          {frame >= t(20.4) ? (
            <div style={{ position: "absolute", left: colX, top: 610, display: "flex", flexDirection: "column", gap: 18 }}>
              <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, opacity: uiSpring(frame, fps, t(20.4)) }}>proposals</div>
              <TierBadge tier="auto" label="Set banner" state="executed" delay={t(20.6)} size={type.label} />
              <TierBadge tier="approval" label="Roll back config" state={frame >= t(27.2) ? "executed" : "pending"} delay={t(23.6)} size={type.label} />
            </div>
          ) : null}
          {frame >= t(26.0) ? <Callout label="Approve" target={toScene(frameC, S5_TARGETS.approve)} at={{ x: colX, y: 870 }} delay={t(26.0)} color={colors.ok} /> : null}
        </div>
      ) : null}

      {/* Beat E: recovery */}
      {inBeat(E) ? (
        <div style={{ position: "absolute", inset: 0, opacity: ease(frame, t(E.from), 10) }}>
          <LowerThird title="Checkout failures · last 15 min" sub="synthetic incident · MOCK" delay={t(E.from)} top={200} />
          <div style={{ position: "absolute", left: chart.x, top: chart.y, width: chart.w, height: chart.h }}>
            <svg width={chart.w} height={chart.h} style={{ overflow: "visible" }}>
              <line x1={0} y1={base} x2={chart.w} y2={base} stroke={colors.line} strokeDasharray="6 8" />
              <text x={0} y={base + 36} fill={colors.textMuted} fontFamily={fonts.mono} fontSize={type.min}>
                baseline · 1 failure / 5 min
              </text>
              <line x1={approveX} y1={20} x2={approveX} y2={base} stroke={colors.ok} strokeDasharray="4 8" opacity={ease(frame, t(31.0), 10)} />
              <text x={approveX + 12} y={40} fill={colors.ok} fontFamily={fonts.mono} fontSize={type.min} opacity={ease(frame, t(31.0), 10)}>
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
          <div style={{ position: "absolute", left: colX, top: 380 }}>
            <AgentNode x={0} y={0} width={colW} name="Verifier" role="quiet window · metric back at baseline" icon="verify" delay={t(31.6)} active={frame >= t(32.4)} activeColor={colors.ok} activeDelay={t(32.4)} />
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
                opacity: uiSpring(frame, fps, t(32.8)),
                translate: `0px ${(1 - uiSpring(frame, fps, t(32.8))) * 24}px`,
              }}
            >
              Resolved.
            </div>
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
