import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { BrowserFrame } from "../components/BrowserFrame";
import { Clip } from "../components/Clip";
import { LowerThird } from "../components/LowerThird";
import { TierBadge } from "../components/TierBadge";
import { KineticHeadline } from "../components/KineticHeadline";
import { colors, fonts, layout, type } from "../theme";
import { useClips, useT } from "../SceneContext";
import { CLIP_H, CLIP_W } from "./S5Checkout";
import { uiSpring } from "../anim";
import { useVideoConfig } from "remotion";

export const S7Renewals: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const clips = useClips();
  const frameC = { x: layout.marginX, y: 180, w: 1000 };
  const colX = 1180;

  return (
    <AbsoluteFill>
      <Background glow="warn" glowStrength={0.12} />
      <LowerThird title="Subscription renewal failures" sub="Coffee Club · 4 failed renewals in 60 min" delay={t(0.2)} top={90} color={colors.warn} />
      <BrowserFrame x={frameC.x} y={frameC.y} width={frameC.w} height={44 + (frameC.w * CLIP_H) / CLIP_W} url="localhost:8000/#/incident" delay={t(0.1)}>
        <Clip name="07-renewals.mp4" available={Boolean(clips["07-renewals.mp4"])} trimBefore={90} />
      </BrowserFrame>

      <div style={{ position: "absolute", left: colX, top: 260, display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, opacity: uiSpring(frame, fps, t(1.2)) }}>proposals</div>
        <TierBadge tier="auto" label="Reminder" state="executed" delay={t(1.6)} size={type.label} />
        <TierBadge tier="approval" label="Capture outstanding" state="pending" delay={t(6.8)} size={type.label} />
      </div>

      <div style={{ position: "absolute", left: colX, top: 520, width: 620 }}>
        <KineticHeadline text="Small fixes run on their own." size={type.h2Small} delay={t(8.6)} />
        <KineticHeadline text="Money moves only with a human." size={type.h2Small} delay={t(10.2)} color={colors.warn} style={{ marginTop: 10 }} />
      </div>
    </AbsoluteFill>
  );
};
