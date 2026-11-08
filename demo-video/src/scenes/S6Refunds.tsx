import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { LowerThird } from "../components/LowerThird";
import { PolicyGate } from "../components/PolicyGate";
import { CamKey, ClipBeat, StageFrame, WIDE, cameraAt, cameraStyle, onStage } from "../components/Stage";
import { colors, type } from "../theme";
import { ease } from "../anim";
import { useClips, useT } from "../SceneContext";

/** Points inside 06-refund-wave.mp4 (clip pixels), measured on the live recording. */
export const S6_TARGETS = {
  rootCause: { x: 800, y: 330 },
  productLine: { x: 700, y: 195 },
  pauseSales: { x: 800, y: 585 },
  probe: { x: 800, y: 750 },
};
const CLIP = "06-refund-wave.mp4";
const CLIP_SECONDS = 12.64;
const T = S6_TARGETS;
const z = (pt: { x: number; y: number }, s: number, at: number): CamKey => ({ at, s, ...onStage(pt) });

// Clip phases (the clip starts at scene 0.3): root cause 0-2.5, then the proposals view
// (the notify card names the product, then pause_sales, then the refused probe).
const CAM: CamKey[] = [
  WIDE(0),
  WIDE(0.6),
  z(T.rootCause, 1.45, 1.3),
  z(T.rootCause, 1.45, 2.6),
  WIDE(3.2),
  z(T.productLine, 1.6, 3.9),
  z(T.productLine, 1.6, 4.9),
  z(T.pauseSales, 1.6, 5.7),
  z(T.pauseSales, 1.6, 8.0),
  z(T.probe, 1.7, 8.8),
  z(T.probe, 1.7, 11.4),
  WIDE(12.1),
];

export const S6Refunds: React.FC = () => {
  const frame = useCurrentFrame();
  const t = useT();
  const clips = useClips();
  const cam = cameraAt(CAM, frame / t(1));

  const gateAt = t(11.8);
  const dimClip = interpolate(frame, [gateAt, gateAt + 14], [1, 0.16], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const lineAt = t(17.5);
  const dimAll = interpolate(frame, [lineAt - 6, lineAt + 8], [1, 0.12], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // The label belongs to the opening wide shot only.
  const labelOpacity = frame < t(3.0) ? Math.max(0, Math.min(1, 1 - (cam.s - 1.05) / 0.3)) : 0;

  return (
    <AbsoluteFill>
      <Background glow="critical" glowStrength={0.12} />
      <div style={{ position: "absolute", inset: 0, opacity: dimAll }}>
        <div style={{ position: "absolute", inset: 0, opacity: dimClip }}>
          <div style={{ position: "absolute", inset: 0, ...cameraStyle(cam) }}>
            <StageFrame url="localhost:8000/#/incident · refund wave" delay={0}>
              <ClipBeat name={CLIP} available={Boolean(clips[CLIP])} from={t(0.3)} clipSeconds={CLIP_SECONDS} />
            </StageFrame>
          </div>
          <div style={{ opacity: labelOpacity }}>
            <LowerThird title="Refund wave" sub="5 refunds on one product in an hour" delay={t(0.2)} top={110} left={150} color={colors.critical} backdrop />
          </div>
        </div>

        {/* The red-team probe meets the policy proxy */}
        {frame >= gateAt - 10 ? (
          <PolicyGate
            x={1100}
            y={500}
            height={300}
            startX={240}
            endX={1620}
            delay={gateAt}
            laneGap={60}
            proposals={[
              { label: "Pause sales of the product", tier: "approval", delay: t(12.0) },
              { label: "Bulk refund · red-team probe", tier: "forbidden", delay: t(12.8) },
            ]}
          />
        ) : null}
        {frame >= gateAt ? (
          <div style={{ opacity: ease(frame, gateAt + 6, 10) }}>
            <LowerThird title="Policy proxy" sub="plain code · the catalog decides, not the model" delay={gateAt + 6} top={110} left={150} />
          </div>
        ) : null}
      </div>

      {frame >= lineAt ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 1500 }}>
            <KineticHeadline text="Whoever asks, the code decides." size={type.h1} delay={lineAt} align="center" />
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
