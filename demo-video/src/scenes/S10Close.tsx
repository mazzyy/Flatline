import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { LineReveal } from "../components/KineticHeadline";
import { colors, fonts, product, type } from "../theme";
import { accentSpring, uiSpring } from "../anim";
import { useT } from "../SceneContext";

export const S10Close: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();
  const p = accentSpring(frame, fps, t(0.2));
  const builder = uiSpring(frame, fps, t(1.5));

  return (
    <AbsoluteFill>
      <Background glow="accent" glowStrength={0.28} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", translate: "0px -40px" }}>
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
          {/* The builder: photo, name, links */}
          <div
            style={{
              marginTop: 64,
              display: "flex",
              alignItems: "center",
              gap: 30,
              padding: "22px 40px 22px 22px",
              borderRadius: 999,
              background: `${colors.surface}cc`,
              border: `1px solid ${colors.line}`,
              opacity: builder,
              translate: `0px ${(1 - builder) * 18}px`,
            }}
          >
            <Img
              src={staticFile("brand/builder.jpg")}
              style={{ width: 132, height: 132, borderRadius: "50%", objectFit: "cover", border: `3px solid ${colors.accent}`, flexShrink: 0 }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted }}>built by</div>
              <div style={{ fontFamily: fonts.headline, fontWeight: 700, fontSize: 44, color: colors.text, letterSpacing: "-0.01em" }}>Abdul Musawar Soomro</div>
              <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.accent }}>
                {product.repoUrl} · musawar.tech
              </div>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
