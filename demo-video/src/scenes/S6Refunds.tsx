import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { LowerThird } from "../components/LowerThird";
import { PolicyGate } from "../components/PolicyGate";
import { ClipBeat, StageFrame, VIEW, VIEW_LIFT, cameraStyle } from "../components/Stage";
import { Highlight } from "../components/Highlight";
import { colors, type } from "../theme";
import { ease } from "../anim";
import { useClips, useT } from "../SceneContext";

/** Boxes inside 06-refund-wave.mp4 (clip pixels: left, top, right, bottom), measured on the live recording. */
export const S6_BOXES = {
  rootCause: { x0: 224, y0: 240, x1: 1376, y1: 410 },
  productLine: { x0: 236, y0: 165, x1: 1376, y1: 222 },
  pauseSales: { x0: 224, y0: 496, x1: 1376, y1: 677 },
  probe: { x0: 224, y0: 695, x1: 1376, y1: 807 },
};
const CLIP = "06-refund-wave.mp4";
const CLIP_SECONDS = 12.64;
const B = S6_BOXES;
// The clip starts at scene 0.3 on the root cause and scrolls to the proposals at scene 2.9-3.3.
// The camera rests; highlights follow the narration.
const CAM = VIEW(0);

export const S6Refunds: React.FC = () => {
  const frame = useCurrentFrame();
  const t = useT();
  const clips = useClips();
  const cam = CAM;

  const gateAt = t(11.8);
  const dimClip = interpolate(frame, [gateAt, gateAt + 14], [1, 0.16], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const lineAt = t(17.5);
  const dimAll = interpolate(frame, [lineAt - 6, lineAt + 8], [1, 0.12], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // The label belongs to the opening wide shot only.
  const labelOpacity = 1 - ease(frame, t(2.3), 10);

  return (
    <AbsoluteFill>
      <Background glow="critical" glowStrength={0.12} />
      <div style={{ position: "absolute", inset: 0, opacity: dimAll }}>
        <div style={{ position: "absolute", inset: 0, opacity: dimClip }}>
          <div style={{ position: "absolute", inset: 0, ...cameraStyle(cam, VIEW_LIFT) }}>
            <StageFrame url="localhost:8000/#/incident · refund wave" delay={0}>
              <ClipBeat name={CLIP} available={Boolean(clips[CLIP])} from={t(0.3)} clipSeconds={CLIP_SECONDS} />
            </StageFrame>
            <Highlight box={B.rootCause} from={t(0.9)} to={t(2.7)} label="one product, no common buyer" color={colors.critical} />
            <Highlight box={B.productLine} from={t(3.6)} to={t(5.3)} label="the product the refunds share" labelSide="below" />
            <Highlight box={B.pauseSales} from={t(5.4)} to={t(9.0)} label="pause sales · needs my approval" color={colors.warn} labelSide="inside" />
            <Highlight box={B.probe} from={t(9.2)} to={t(11.7)} label="red-team probe · refused" color={colors.critical} labelSide="inside" />
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
