import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { LineReveal } from "../components/KineticHeadline";
import { colors, fonts, product, type } from "../theme";
import { accentSpring } from "../anim";
import { useT } from "../SceneContext";

export const S10Close: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const p = accentSpring(frame, fps, t(0.2));

  return (
    <AbsoluteFill>
      <Background glow="accent" glowStrength={0.28} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", translate: "0px -20px" }}>
          <div
            style={{
              fontFamily: fonts.headline,
              fontWeight: 700,
              fontSize: 160,
              lineHeight: 1,
              letterSpacing: "-0.03em",
              color: colors.text,
              opacity: Math.min(1, p),
              scale: String(interpolate(p, [0, 1], [0.9, 1])),
            }}
          >
            {product.name}
          </div>
          <LineReveal delay={t(0.9)} style={{ marginTop: 28 }}>
            <div style={{ fontFamily: fonts.body, fontSize: type.h2, color: colors.textMuted, letterSpacing: "-0.01em" }}>{product.closeTagline}</div>
          </LineReveal>
          <LineReveal delay={t(1.6)} style={{ marginTop: 64 }}>
            <div style={{ display: "flex", gap: 56, fontFamily: fonts.mono, fontSize: type.label, color: colors.accent }}>
              <span>{product.repoUrl}</span>
            </div>
          </LineReveal>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
