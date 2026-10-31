import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline } from "../components/KineticHeadline";
import { Chip } from "../components/Chip";
import { colors, fonts, product } from "../theme";
import { accentSpring } from "../anim";
import { useT } from "../SceneContext";

export const S3Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const nameAt = t(0.4);
  const tagAt = t(1.6);
  const chipsAt = t(4.2);
  const p = accentSpring(frame, fps, nameAt);

  return (
    <AbsoluteFill>
      <Background glow="accent" glowStrength={0.3} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", translate: "0px -40px" }}>
          <div
            style={{
              position: "absolute",
              width: 900,
              height: 360,
              top: -90,
              borderRadius: 999,
              background: `radial-gradient(closest-side, ${colors.accent}55, transparent)`,
              filter: "blur(30px)",
              opacity: Math.min(1, p),
            }}
          />
          <div
            style={{
              fontFamily: fonts.headline,
              fontWeight: 700,
              fontSize: 176,
              lineHeight: 1,
              letterSpacing: "-0.03em",
              color: colors.text,
              opacity: Math.min(1, p),
              scale: String(interpolate(p, [0, 1], [0.86, 1])),
              position: "relative",
            }}
          >
            {product.name}
          </div>
          <div style={{ marginTop: 36, position: "relative" }}>
            <KineticHeadline text={product.tagline} font="body" weight={400} size={48} delay={tagAt} color={colors.textMuted} align="center" maxWidth={1300} />
          </div>
          <div style={{ marginTop: 56, display: "flex", gap: 20, position: "relative" }}>
            {["Detect", "Diagnose", "Fix safely"].map((c, i) => (
              <Chip key={c} text={c} delay={chipsAt + i * 6} playful />
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
