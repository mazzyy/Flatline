import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { KineticHeadline, LineReveal } from "../components/KineticHeadline";
import { colors, fonts, layout, type } from "../theme";
import { useT } from "../SceneContext";

const LINE = "checkout.capture → 500";

/** Frame at which line k (0-based) appears: accelerating cascade. */
const lineStart = (k: number, t0: number): number => {
  let f = t0;
  for (let i = 0; i < k; i++) f += Math.max(3, Math.round(22 * Math.pow(0.78, i)));
  return f;
};

export const S1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const t = useT();
  const typingStart = t(0.4);
  const typingFrames = t(1.6);
  const cascadeStart = typingStart + typingFrames + t(0.3);
  const linesOut = t(5.0);
  const headlineAt = t(5.4);
  const sublineAt = t(7.2);
  const lineCount = 14;
  const lineH = 62;

  const typed = Math.floor(interpolate(frame, [typingStart, typingStart + typingFrames], [0, LINE.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const caret = Math.floor(frame / 8) % 2 === 0;
  const linesOpacity = interpolate(frame, [linesOut, linesOut + 10], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const redness = interpolate(frame, [cascadeStart, cascadeStart + 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <Background glow={frame < linesOut ? "critical" : "accent"} glowStrength={frame < linesOut ? 0.12 + redness * 0.18 : 0.22} />
      {/* Cascade of failing captures */}
      <div style={{ position: "absolute", left: layout.marginX, top: layout.marginY + 20, opacity: linesOpacity }}>
        {Array.from({ length: lineCount }).map((_, k) => {
          const start = k === 0 ? typingStart : lineStart(k, cascadeStart);
          if (frame < start) return null;
          const text = k === 0 ? LINE.slice(0, typed) + (typed < LINE.length && caret ? "▍" : "") : LINE;
          const mix = Math.min(1, k / 9) * redness;
          const color = mix > 0.5 ? colors.critical : colors.text;
          const op = interpolate(frame, [start, start + 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div
              key={k}
              style={{
                fontFamily: fonts.mono,
                fontSize: 44,
                lineHeight: `${lineH}px`,
                color,
                opacity: op * (0.5 + 0.5 * (1 - k / lineCount) + (mix > 0.5 ? 0.3 : 0)),
                letterSpacing: "-0.01em",
                whiteSpace: "pre",
              }}
            >
              {text}
              {k > 0 && mix > 0.5 ? <span style={{ color: colors.textMuted, marginLeft: 28, fontSize: type.min }}>+{k * 3} more</span> : null}
            </div>
          );
        })}
      </div>

      {/* Headline */}
      {frame >= headlineAt ? (
        <div style={{ position: "absolute", left: layout.marginX, top: 380, width: layout.width - layout.marginX * 2 }}>
          <KineticHeadline text="Nobody is on call for revenue." size={type.h1Large} delay={headlineAt} />
          <LineReveal delay={sublineAt} style={{ marginTop: 36 }}>
            <div style={{ fontFamily: fonts.body, fontSize: type.h2, color: colors.textMuted, letterSpacing: "-0.01em" }}>
              Shops monitor servers. Not money.
            </div>
          </LineReveal>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
