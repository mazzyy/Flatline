import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../theme";

/**
 * Dark base, 1px grid at 6% opacity, and a slow drifting radial accent glow.
 * Pure CSS so it costs nothing to render.
 */
export const Background: React.FC<{ glow?: "accent" | "critical" | "ok" | "warn" | "none"; glowStrength?: number }> = ({
  glow = "accent",
  glowStrength = 0.22,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const glowColor =
    glow === "critical" ? colors.critical : glow === "ok" ? colors.ok : glow === "warn" ? colors.warn : colors.accent;
  // One slow drift across the whole scene; period ~ 40 s so it never repeats on screen.
  const t = frame / (fps * 40);
  const gx = interpolate(Math.sin(t * Math.PI * 2), [-1, 1], [width * 0.3, width * 0.7]);
  const gy = interpolate(Math.cos(t * Math.PI * 2), [-1, 1], [height * 0.25, height * 0.65]);

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${colors.line} 1px, transparent 1px), linear-gradient(90deg, ${colors.line} 1px, transparent 1px)`,
          backgroundSize: "96px 96px",
          backgroundPosition: "-1px -1px",
          // `line` is already dim against `bg`; 0.45 of it reads as ~6% contrast on screen.
          opacity: 0.45,
          maskImage: "radial-gradient(ellipse at center, black 55%, transparent 100%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 55%, transparent 100%)",
        }}
      />
      {glow !== "none" ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(900px 700px at ${gx}px ${gy}px, ${glowColor}, transparent 70%)`,
            opacity: glowStrength,
            filter: "blur(40px)",
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
