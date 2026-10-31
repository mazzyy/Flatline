import React from "react";
import { useCurrentFrame } from "remotion";
import { colors, fonts, type } from "../theme";
import { ease } from "../anim";

/** Animated number in JetBrains Mono with a label underneath. */
export const StatCounter: React.FC<{
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  delay?: number;
  duration?: number;
  size?: number;
  color?: string;
  note?: string;
  align?: "left" | "center" | "right";
  decimals?: number;
}> = ({ value, label, prefix = "", suffix = "", delay = 0, duration = 60, size = 112, color = colors.text, note, align = "left", decimals = 0 }) => {
  const frame = useCurrentFrame();
  const p = ease(frame, delay, duration);
  const current = value * p;
  const text = `${prefix}${current.toLocaleString("en-US", { maximumFractionDigits: decimals, minimumFractionDigits: decimals })}${suffix}`;
  return (
    <div style={{ textAlign: align, opacity: ease(frame, delay, 10) }}>
      <div
        style={{
          fontFamily: fonts.mono,
          fontWeight: 500,
          fontSize: size,
          lineHeight: 1,
          letterSpacing: "-0.03em",
          color,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {text}
      </div>
      <div style={{ marginTop: 14, fontFamily: fonts.body, fontSize: type.label, color: colors.textMuted }}>
        {label}
        {note ? <span style={{ marginLeft: 14, fontSize: type.min, color: colors.textMuted, opacity: 0.8 }}>({note})</span> : null}
      </div>
    </div>
  );
};
