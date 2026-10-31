import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, radius, type } from "../theme";
import { accentSpring, uiSpring } from "../anim";

/** Small text chip. `playful` uses the accent spring. */
export const Chip: React.FC<{
  text: string;
  delay?: number;
  color?: string;
  playful?: boolean;
  size?: number;
  mono?: boolean;
}> = ({ text, delay = 0, color = colors.accent, playful = false, size = type.label, mono = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = playful ? accentSpring(frame, fps, delay) : uiSpring(frame, fps, delay);
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        height: size * 2,
        padding: `0 ${size}px`,
        borderRadius: radius.pill,
        border: `1px solid ${color}66`,
        background: `${color}14`,
        color: colors.text,
        fontFamily: mono ? fonts.mono : fonts.body,
        fontWeight: 500,
        fontSize: size,
        whiteSpace: "nowrap",
        opacity: Math.min(1, p),
        scale: String(0.8 + 0.2 * p),
      }}
    >
      {text}
    </div>
  );
};
