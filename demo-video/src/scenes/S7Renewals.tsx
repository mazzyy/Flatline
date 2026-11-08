import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { Chip } from "../components/Chip";
import { LowerThird } from "../components/LowerThird";
import { TierBadge } from "../components/TierBadge";
import { CamKey, ClipBeat, StageFrame, WIDE, cameraAt, cameraStyle, onStage } from "../components/Stage";
import { colors, fonts, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";
import { useVideoConfig } from "remotion";

/** Points inside 07-renewals.mp4 (clip pixels), measured on the live recording. */
export const S7_TARGETS = {
  planRead: { x: 600, y: 700 },
  reminder: { x: 760, y: 420 },
};
const CLIP = "07-renewals.mp4";
const CLIP_SECONDS = 11.64;
const T = S7_TARGETS;
const z = (pt: { x: number; y: number }, s: number, at: number): CamKey => ({ at, s, ...onStage(pt) });

// Clip phases: agent timeline with the PayPal plan read 0-5, then the proposals view
// (the page scrolls only ~40 px, so the plan read stays in frame), reminder card.
const CAM: CamKey[] = [
  WIDE(0),
  WIDE(1.8),
  z(T.planRead, 1.9, 3.2),
  z(T.planRead, 1.9, 7.9),
  z(T.reminder, 1.6, 8.8),
  z(T.reminder, 1.6, 12.0),
  WIDE(12.6),
];

export const S7Renewals: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();
  const cam = cameraAt(CAM, frame / t(1));
  const outroAt = t(12.6);
  const dim = interpolate(frame, [outroAt, outroAt + 14], [1, 0.14], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // The label belongs to the opening wide shot only.
  const labelOpacity = frame < t(6.0) ? Math.max(0, Math.min(1, 1 - (cam.s - 1.05) / 0.3)) : 0;

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
          <LowerThird title="Subscription renewal failures" sub="Coffee Club · 4 failed renewals in 60 min" delay={t(0.2)} top={110} left={150} color={colors.warn} backdrop />
        </div>
      </div>

      {frame >= outroAt ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 22 }}>
            <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, opacity: uiSpring(frame, fps, outroAt) }}>outcome</div>
            <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
              <Chip text="plan healthy · read from PayPal" delay={outroAt + 4} size={type.label} mono color={colors.accent} />
              <TierBadge tier="auto" label="Payment reminders" state="executed" delay={outroAt + 10} size={type.label} />
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
