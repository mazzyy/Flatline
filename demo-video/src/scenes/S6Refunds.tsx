import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background } from "../components/Background";
import { BrowserFrame } from "../components/BrowserFrame";
import { Clip } from "../components/Clip";
import { LowerThird } from "../components/LowerThird";
import { PolicyGate } from "../components/PolicyGate";
import { KineticHeadline } from "../components/KineticHeadline";
import { colors, fonts, layout, type } from "../theme";
import { ease } from "../anim";
import { useClips, useT } from "../SceneContext";
import { CLIP_H, CLIP_W } from "./S5Checkout";

const PRODUCTS: { name: string; refunds: number }[] = [
  { name: "House Blend", refunds: 1 },
  { name: "Ethiopia Yirgacheffe", refunds: 5 },
  { name: "Decaf Colombia", refunds: 0 },
  { name: "Coffee Club", refunds: 1 },
];

export const S6Refunds: React.FC = () => {
  const frame = useCurrentFrame();
  const t = useT();
  const clips = useClips();

  const frameC = { x: layout.marginX, y: 120, w: 1000 };
  const colX = 1180;
  const colW = 620;
  const gateAt = t(9.0);
  const dimClip = interpolate(frame, [gateAt, gateAt + 14], [1, 0.22], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const lineAt = t(19.4);
  const dimAll = interpolate(frame, [lineAt - 6, lineAt + 8], [1, 0.12], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const barMax = 5;
  const chart = { x: colX, y: 220, w: colW, h: 380 };
  const barW = 110;
  const gap = (chart.w - PRODUCTS.length * barW) / (PRODUCTS.length - 1);

  return (
    <AbsoluteFill>
      <Background glow="critical" glowStrength={0.14} />
      <div style={{ position: "absolute", inset: 0, opacity: dimAll }}>
        <div style={{ position: "absolute", inset: 0, opacity: dimClip }}>
          <LowerThird title="Refund wave" sub="refunds concentrated on one product" delay={t(0.2)} top={40} color={colors.critical} />
          <BrowserFrame x={frameC.x} y={frameC.y} width={frameC.w} height={44 + (frameC.w * CLIP_H) / CLIP_W} url="localhost:8000/#/incident" delay={t(0.1)} pushInFrames={t(9)}>
            <Clip name="06-refund-wave.mp4" available={Boolean(clips["06-refund-wave.mp4"])} trimBefore={90} />
          </BrowserFrame>

          {/* Refunds by product */}
          <div style={{ position: "absolute", left: chart.x, top: chart.y - 60, fontFamily: fonts.mono, fontSize: type.min, color: colors.textMuted, opacity: ease(frame, t(1.2), 10) }}>
            refunds by product · last 60 min
          </div>
          {PRODUCTS.map((p, i) => {
            const grow = ease(frame, t(1.6) + i * 6, 26);
            const h = (p.refunds / barMax) * (chart.h - 80) * grow;
            const x = chart.x + i * (barW + gap);
            const hot = p.refunds === barMax;
            return (
              <React.Fragment key={p.name}>
                <div
                  style={{
                    position: "absolute",
                    left: x,
                    top: chart.y + chart.h - 60 - h,
                    width: barW,
                    height: Math.max(4, h),
                    borderRadius: 8,
                    background: hot ? colors.critical : colors.surfaceRaised,
                    border: `1px solid ${hot ? colors.critical : colors.line}`,
                    boxShadow: hot ? `0 0 40px ${colors.critical}55` : undefined,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: x - 30,
                    width: barW + 60,
                    top: chart.y + chart.h - 44,
                    textAlign: "center",
                    fontFamily: fonts.body,
                    fontSize: type.min,
                    color: hot ? colors.text : colors.textMuted,
                    fontWeight: hot ? 500 : 400,
                    opacity: grow,
                    lineHeight: 1.2,
                  }}
                >
                  {p.name}
                </div>
                <div
                  style={{
                    position: "absolute",
                    left: x,
                    width: barW,
                    top: chart.y + chart.h - 60 - h - 40,
                    textAlign: "center",
                    fontFamily: fonts.mono,
                    fontSize: type.labelSmall,
                    color: hot ? colors.critical : colors.textMuted,
                    opacity: grow,
                  }}
                >
                  {Math.round(p.refunds * grow)}
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* The refusal */}
        {frame >= gateAt - 10 ? (
          <PolicyGate
            x={1180}
            y={560}
            height={300}
            startX={260}
            endX={1500}
            delay={gateAt}
            laneGap={60}
            proposals={[
              { label: "Pause sales of product", tier: "approval", delay: t(9.8) },
              { label: "Bulk refund", tier: "forbidden", delay: t(13.0) },
            ]}
          />
        ) : null}
      </div>

      {frame >= lineAt ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 1500 }}>
            <KineticHeadline text="The agent asked. The policy said no." size={type.h1} delay={lineAt} align="center" />
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
