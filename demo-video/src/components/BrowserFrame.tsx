import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, radius, shadow, type } from "../theme";
import { uiSpring } from "../anim";

/**
 * Rounded browser chrome around a screen recording. Gentle push-in over the
 * scene (1.0 → 1.04) when `pushIn` is set. Children are clipped to the viewport.
 */
export const BrowserFrame: React.FC<{
  x: number;
  y: number;
  width: number;
  height: number;
  url?: string;
  delay?: number;
  pushIn?: boolean;
  pushInFrames?: number;
  children?: React.ReactNode;
}> = ({ x, y, width, height, url, delay = 0, pushIn = true, pushInFrames, children }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = uiSpring(frame, fps, delay);
  const span = pushInFrames ?? durationInFrames;
  const scale = pushIn
    ? interpolate(frame, [delay, delay + span], [1, 1.04], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const bar = 44;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height,
        opacity: enter,
        scale: String(interpolate(enter, [0, 1], [0.97, 1]) * scale),
        transformOrigin: "50% 50%",
        borderRadius: radius.frame,
        border: `1px solid ${colors.line}`,
        background: colors.surface,
        boxShadow: shadow.soft,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: bar,
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "0 18px",
          borderBottom: `1px solid ${colors.line}`,
          background: colors.surfaceRaised,
        }}
      >
        {[colors.critical, colors.warn, colors.ok].map((c) => (
          <span key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c, opacity: 0.8 }} />
        ))}
        {url ? (
          <span
            style={{
              marginLeft: 16,
              fontFamily: fonts.mono,
              fontSize: type.min,
              color: colors.textMuted,
              letterSpacing: "-0.01em",
            }}
          >
            {url}
          </span>
        ) : null}
      </div>
      <div style={{ position: "absolute", left: 0, top: bar, right: 0, bottom: 0, overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
};
