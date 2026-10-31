import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, radius, Tier, tierColor, type } from "../theme";
import { uiSpring } from "../anim";

/** Pill: "<label> · <tier>" in the tier colour. Colours never change per tier. */
export const TierBadge: React.FC<{
  tier: Tier;
  label?: string;
  delay?: number;
  size?: number;
  style?: React.CSSProperties;
  state?: "executed" | "pending" | "refused";
}> = ({ tier, label, delay = 0, size = type.labelSmall, style, state }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = uiSpring(frame, fps, delay);
  const color = tierColor[tier];
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        height: size * 1.9,
        padding: `0 ${size * 0.8}px`,
        borderRadius: radius.pill,
        background: `${color}1f`,
        border: `1px solid ${color}`,
        color,
        fontFamily: fonts.body,
        fontWeight: 500,
        fontSize: size,
        whiteSpace: "nowrap",
        opacity: p,
        scale: String(0.92 + p * 0.08),
        ...style,
      }}
    >
      <span style={{ width: size * 0.4, height: size * 0.4, borderRadius: 999, background: color }} />
      {label ? <span style={{ color: colors.text }}>{label}</span> : null}
      {label ? <span style={{ color: colors.textMuted }}>·</span> : null}
      <span>{tier}</span>
      {state ? (
        <>
          <span style={{ color: colors.textMuted }}>·</span>
          <span style={{ color: state === "refused" ? colors.critical : colors.textMuted }}>{state}</span>
        </>
      ) : null}
    </div>
  );
};
