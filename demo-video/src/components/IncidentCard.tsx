import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, type } from "../theme";
import { uiSpring } from "../anim";

/**
 * The incident object: critical left bar, title, optional subtitle. Same shape
 * in S4 (emitted by the detector) and S5 (root-cause pull-out).
 */
export const IncidentCard: React.FC<{
  x: number;
  y: number;
  width?: number;
  title: string;
  sub?: string;
  delay?: number;
  color?: string;
  big?: boolean;
  children?: React.ReactNode;
}> = ({ x, y, width = 420, title, sub, delay = 0, color = colors.critical, big = false, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = uiSpring(frame, fps, delay);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        borderRadius: 16,
        background: colors.surfaceRaised,
        border: `1px solid ${colors.line}`,
        borderLeft: `6px solid ${color}`,
        boxShadow: `0 16px 40px rgba(0,0,0,0.4), 0 0 48px ${color}22`,
        padding: big ? "28px 32px" : "18px 22px",
        opacity: p,
        translate: `0px ${(1 - p) * 24}px`,
      }}
    >
      <div
        style={{
          fontFamily: fonts.mono,
          fontSize: type.min,
          color,
          letterSpacing: "0.02em",
          textTransform: "uppercase",
        }}
      >
        {sub ?? "incident"}
      </div>
      <div
        style={{
          marginTop: 8,
          fontFamily: big ? fonts.headline : fonts.body,
          fontWeight: big ? 700 : 500,
          fontSize: big ? type.h2 : type.label,
          lineHeight: 1.15,
          letterSpacing: big ? "-0.02em" : "-0.01em",
          color: colors.text,
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
};
