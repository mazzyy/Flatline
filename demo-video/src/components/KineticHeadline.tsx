import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, type } from "../theme";
import { STAGGER, uiSpring } from "../anim";

/**
 * Word-by-word reveal: each word slides up 24px inside a mask with opacity.
 */
export const KineticHeadline: React.FC<{
  text: string;
  size?: number;
  delay?: number;
  color?: string;
  font?: "headline" | "body";
  weight?: number;
  align?: "left" | "center";
  maxWidth?: number;
  stagger?: number;
  style?: React.CSSProperties;
}> = ({
  text,
  size = type.h1,
  delay = 0,
  color = colors.text,
  font = "headline",
  weight,
  align = "left",
  maxWidth,
  stagger = STAGGER,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: align === "center" ? "center" : "flex-start",
        columnGap: size * 0.26,
        rowGap: size * 0.1,
        maxWidth,
        fontFamily: font === "headline" ? fonts.headline : fonts.body,
        fontWeight: weight ?? (font === "headline" ? 700 : 400),
        fontSize: size,
        lineHeight: 1.08,
        letterSpacing: font === "headline" ? "-0.02em" : "-0.005em",
        color,
        textAlign: align,
        ...style,
      }}
    >
      {words.map((w, i) => {
        const p = uiSpring(frame, fps, delay + i * stagger);
        return (
          <span key={`${w}-${i}`} style={{ display: "inline-block", overflow: "hidden", paddingBottom: "0.12em", marginBottom: "-0.12em" }}>
            <span
              style={{
                display: "inline-block",
                opacity: p,
                translate: `0px ${(1 - p) * 24}px`,
              }}
            >
              {w}
            </span>
          </span>
        );
      })}
    </div>
  );
};

/** Line reveal for sublines: whole line slides up 24px behind a mask. */
export const LineReveal: React.FC<{
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = uiSpring(frame, fps, delay);
  return (
    <div style={{ overflow: "hidden", paddingBottom: "0.15em", marginBottom: "-0.15em", ...style }}>
      <div style={{ opacity: p, translate: `0px ${(1 - p) * 24}px` }}>{children}</div>
    </div>
  );
};
