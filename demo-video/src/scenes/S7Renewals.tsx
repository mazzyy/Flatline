import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { LowerThird } from "../components/LowerThird";
import { TierBadge } from "../components/TierBadge";
import { CamKey, ClipBeat, StageFrame, WIDE, cameraAt, cameraStyle, onStage } from "../components/Stage";
import { colors, fonts, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";
import { useVideoConfig } from "remotion";

/** Points inside 07-renewals.mp4 (clip pixels), measured on the live recording. */
export const S7_TARGETS = {
  planRead: { x: 520, y: 700 },
  proposals: { x: 600, y: 470 },
};
const CLIP = "07-renewals.mp4";
const CLIP_SECONDS = 12.3;
const T = S7_TARGETS;
const z = (pt: { x: number; y: number }, s: number, at: number): CamKey => ({ at, s, ...onStage(pt) });

// Clip phases: agent timeline 0-5.0 (the PayPal plan read), proposals 5.8-12.3.
const CAM: CamKey[] = [
  WIDE(0),
  WIDE(1.2),
  z(T.planRead, 1.9, 2.4),
  z(T.planRead, 1.9, 4.8),
  WIDE(5.6),
  z(T.proposals, 1.5, 6.6),
  z(T.proposals, 1.5, 11.6),
  WIDE(12.4),
];

export const S7Renewals: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();
  const cam = cameraAt(CAM, frame / t(1));
  const outroAt = t(12.6);
  const dim = interpolate(frame, [outroAt, outroAt + 14], [1, 0.14], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const labelOpacity = Math.max(0, Math.min(1, 1 - (cam.s - 1.05) / 0.3));

  return (
    <AbsoluteFill>
      <Background glow="warn" glowStrength={0.12} />
      <div style={{ position: "absolute", inset: 0, opacity: dim }}>
        <div style={{ position: "absolute", inset: 0, ...cameraStyle(cam) }}>
          <StageFrame url="localhost:8000/#/incident · renewals" delay={0}>
            <ClipBeat name={CLIP} available={Boolean(clips[CLIP])} from={0} clipSeconds={CLIP_SECONDS} />
          </StageFrame>
        </div>
        <div style={{ opacity: labelOpacity }}>
          <LowerThird title="Subscription renewal failures" sub="Coffee Club · 4 failed renewals in 60 min" delay={t(0.2)} top={110} left={150} color={colors.warn} />
        </div>
      </div>

      {frame >= outroAt ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 22 }}>
            <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, opacity: uiSpring(frame, fps, outroAt) }}>proposals</div>
            <div style={{ display: "flex", gap: 24 }}>
              <TierBadge tier="auto" label="Payment reminder" state="executed" delay={outroAt + 4} size={type.label} />
              <TierBadge tier="approval" label="Capture outstanding" state="pending" delay={outroAt + 10} size={type.label} />
            </div>
            <div style={{ width: 1500, marginTop: 30, opacity: ease(frame, t(13.2), 8) }}>
              <KineticHeadline text="The agent does the legwork. I keep the final say on money." size={type.h2} delay={t(13.2)} align="center" />
            </div>
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
