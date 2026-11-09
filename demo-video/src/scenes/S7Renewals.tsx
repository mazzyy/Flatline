import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { Chip } from "../components/Chip";
import { LowerThird } from "../components/LowerThird";
import { TierBadge } from "../components/TierBadge";
import { ClipBeat, StageFrame, VIEW, VIEW_LIFT, cameraStyle } from "../components/Stage";
import { Highlight } from "../components/Highlight";
import { colors, fonts, type } from "../theme";
import { ease, uiSpring } from "../anim";
import { useClips, useT } from "../SceneContext";
import { useVideoConfig } from "remotion";

/** Boxes inside 07-renewals.mp4 (clip pixels: left, top, right, bottom), measured on the live recording. */
export const S7_BOXES = {
  planRead: { x0: 255, y0: 668, x1: 925, y1: 720 },
  reminder: { x0: 224, y0: 317, x1: 1376, y1: 509 },
};
const CLIP = "07-renewals.mp4";
const CLIP_SECONDS = 11.64;
/** The page scrolls 40 px down at 5.12 s into the clip. */
const SCROLL = { at: 5.12, dy: 40 };
const B = S7_BOXES;
const CAM = VIEW(0);

export const S7Renewals: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();
  const cam = CAM;
  const outroAt = t(12.6);
  const dim = interpolate(frame, [outroAt, outroAt + 14], [1, 0.14], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // The label belongs to the opening wide shot only.
  const labelOpacity = 1 - ease(frame, t(2.6), 10);

  return (
    <AbsoluteFill>
      <Background glow="warn" glowStrength={0.12} />
      <div style={{ position: "absolute", inset: 0, opacity: dim }}>
        <div style={{ position: "absolute", inset: 0, ...cameraStyle(cam, VIEW_LIFT) }}>
          <StageFrame url="localhost:8000/#/incident · renewals" delay={0}>
            <ClipBeat name={CLIP} available={Boolean(clips[CLIP])} from={0} clipSeconds={CLIP_SECONDS} />
          </StageFrame>
          <Highlight
            box={B.planRead}
            from={t(3.4)}
            to={t(8.1)}
            label="plan read from PayPal through MCP"
            labelSide="right"
            move={{ at: t(SCROLL.at), dur: 5, dy: SCROLL.dy }}
          />
          <Highlight box={B.reminder} from={t(8.4)} to={t(12.3)} label="reminder · sent automatically" color={colors.ok} labelSide="inside" />
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
