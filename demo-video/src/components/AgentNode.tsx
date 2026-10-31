import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, radius, type } from "../theme";
import { uiSpring } from "../anim";

export type AgentIcon = "triage" | "diagnose" | "remediate" | "verify" | "detector" | "executor" | "shop" | "paypal" | "mcp";

const Icon: React.FC<{ kind: AgentIcon; color: string }> = ({ kind, color }) => {
  const s = { stroke: color, strokeWidth: 2.5, fill: "none", strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (kind) {
    case "triage":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M4 6h16M4 12h10M4 18h6" {...s} />
        </svg>
      );
    case "diagnose":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="6" {...s} />
          <path d="M16 16l4 4" {...s} />
        </svg>
      );
    case "remediate":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M14 4l6 6-9 9H5v-6z" {...s} />
        </svg>
      );
    case "verify":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M4 12l5 5L20 6" {...s} />
        </svg>
      );
    case "detector":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M3 13h4l3-7 4 14 3-7h4" {...s} />
        </svg>
      );
    case "executor":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M13 3L5 14h6l-1 7 8-11h-6z" {...s} />
        </svg>
      );
    case "shop":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M4 9l1-4h14l1 4M4 9v10h16V9M4 9h16M10 19v-5h4v5" {...s} />
        </svg>
      );
    case "paypal":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <rect x="3" y="6" width="18" height="12" rx="2" {...s} />
          <path d="M3 10h18" {...s} />
        </svg>
      );
    case "mcp":
      return (
        <svg width="36" height="36" viewBox="0 0 24 24">
          <path d="M8 6H6a2 2 0 00-2 2v8a2 2 0 002 2h2M16 6h2a2 2 0 012 2v8a2 2 0 01-2 2h-2M9 12h6" {...s} />
        </svg>
      );
  }
};

/**
 * Rounded card with icon, name and a one-line role. `active` adds an accent
 * glow and brightens the icon.
 */
export const AgentNode: React.FC<{
  x: number;
  y: number;
  width?: number;
  name: string;
  role: string;
  icon: AgentIcon;
  active?: boolean;
  activeColor?: string;
  delay?: number;
  activeDelay?: number;
  dashed?: boolean;
}> = ({ x, y, width = 300, name, role, icon, active = false, activeColor = colors.accent, delay = 0, activeDelay = 0, dashed }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = uiSpring(frame, fps, delay);
  const glow = active ? uiSpring(frame, fps, activeDelay) : 0;
  const border = dashed ? `1px dashed ${colors.line}` : `1px solid ${colors.line}`;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        padding: "22px 24px",
        borderRadius: radius.card,
        background: colors.surface,
        border,
        boxShadow: `0 0 0 ${glow * 1.5}px ${activeColor}, 0 0 ${glow * 56}px ${activeColor}55`,
        opacity: enter,
        translate: `0px ${(1 - enter) * 24}px`,
        display: "flex",
        gap: 18,
        alignItems: "center",
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 14,
          display: "grid",
          placeItems: "center",
          background: colors.surfaceRaised,
          border: `1px solid ${colors.line}`,
          flexShrink: 0,
        }}
      >
        <Icon kind={icon} color={interpolate(glow, [0, 1], [0, 1]) > 0.5 ? activeColor : colors.textMuted} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontFamily: fonts.body,
            fontWeight: 500,
            fontSize: type.label,
            color: colors.text,
            letterSpacing: "-0.01em",
            whiteSpace: "nowrap",
          }}
        >
          {name}
        </div>
        <div
          style={{
            fontFamily: fonts.body,
            fontSize: type.min,
            color: colors.textMuted,
            marginTop: 4,
            whiteSpace: "nowrap",
          }}
        >
          {role}
        </div>
      </div>
    </div>
  );
};
