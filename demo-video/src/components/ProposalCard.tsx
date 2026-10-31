import React from "react";
import { colors, fonts, radius, Tier, tierColor, type } from "../theme";

export const PROPOSAL_W = 400;
export const PROPOSAL_H = 76;

/**
 * The one proposal shape used everywhere: label + tier dot. Same geometry and
 * colours in S4, S5 and S6 so the object stays recognisable across scenes.
 */
export const ProposalCard: React.FC<{
  label: string;
  tier: Tier;
  style?: React.CSSProperties;
  width?: number;
  tone?: "neutral" | "pass" | "hold" | "refused";
}> = ({ label, tier, style, width = PROPOSAL_W, tone = "neutral" }) => {
  const color = tierColor[tier];
  const border = tone === "neutral" ? colors.line : color;
  return (
    <div
      style={{
        position: "absolute",
        width,
        height: PROPOSAL_H,
        borderRadius: 14,
        background: colors.surfaceRaised,
        border: `1px solid ${border}`,
        boxShadow: tone === "neutral" ? "0 10px 30px rgba(0,0,0,0.35)" : `0 0 0 1px ${color}33, 0 10px 30px rgba(0,0,0,0.35)`,
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "0 22px",
        ...style,
      }}
    >
      <span style={{ width: 12, height: 12, borderRadius: radius.pill, background: color, flexShrink: 0 }} />
      <span
        style={{
          fontFamily: fonts.body,
          fontWeight: 500,
          fontSize: type.labelSmall,
          color: colors.text,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          flex: 1,
        }}
      >
        {label}
      </span>
      <span style={{ fontFamily: fonts.mono, fontSize: type.min, color, flexShrink: 0 }}>{tier}</span>
    </div>
  );
};
