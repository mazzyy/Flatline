import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, Tier, tierColor, type } from "../theme";
import { accentSpring, ease, uiSpring } from "../anim";
import { PROPOSAL_H, PROPOSAL_W, ProposalCard } from "./ProposalCard";

export type GateProposal = {
  label: string;
  tier: Tier;
  delay: number;
  lane?: number; // vertical offset from gate centre
};

const TRAVEL = 40;

/**
 * A gate that proposal cards travel into from the left.
 * auto → passes through to the right. approval → held at the gate, warn pulse.
 * forbidden → hits the gate, one shake, red REFUSED stamp.
 */
export const PolicyGate: React.FC<{
  x: number;
  y: number;
  height?: number;
  startX: number;
  endX: number;
  proposals: GateProposal[];
  delay?: number;
  title?: string;
  subtitle?: string;
  showPassLabel?: boolean;
  /** Fade auto cards out after they pass (absorbed by the executor). */
  absorb?: boolean;
  cardWidth?: number;
  laneGap?: number;
}> = ({
  x,
  y,
  height = 320,
  startX,
  endX,
  proposals,
  delay = 0,
  title = "Policy proxy",
  subtitle = "plain code · no LLM",
  showPassLabel = false,
  absorb = false,
  cardWidth = PROPOSAL_W,
  laneGap = 22,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = uiSpring(frame, fps, delay);
  const gateW = 28;

  return (
    <>
      {/* Gate posts */}
      <div
        style={{
          position: "absolute",
          left: x - gateW / 2,
          top: y - height / 2,
          width: gateW,
          height: height * enter,
          borderRadius: 10,
          background: `linear-gradient(180deg, ${colors.accent}, ${colors.accent}66)`,
          boxShadow: `0 0 40px ${colors.accent}55`,
          transformOrigin: "top",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: x - 170,
          top: y - height / 2 - 92,
          width: 340,
          textAlign: "center",
          opacity: enter,
        }}
      >
        <div style={{ fontFamily: fonts.body, fontWeight: 500, fontSize: type.label, color: colors.text }}>{title}</div>
        <div style={{ fontFamily: fonts.mono, fontSize: type.min, color: colors.accent, marginTop: 4 }}>{subtitle}</div>
      </div>

      {proposals.map((pr, i) => {
        const lane = pr.lane ?? (i - (proposals.length - 1) / 2) * (PROPOSAL_H + laneGap);
        const top = y + lane - PROPOSAL_H / 2;
        const arriveX = x - gateW / 2 - cardWidth - 18; // left edge when touching the gate
        const t = ease(frame, pr.delay, TRAVEL);
        const appear = uiSpring(frame, fps, pr.delay);
        const arrived = frame >= pr.delay + TRAVEL;
        let left: number;
        let tone: "neutral" | "pass" | "hold" | "refused" = "neutral";
        let extra: React.ReactNode = null;
        let shake = 0;
        let opacity = appear;

        if (pr.tier === "auto") {
          // Through the gate and onwards.
          const t2 = ease(frame, pr.delay + TRAVEL - 6, TRAVEL);
          left = interpolate(t, [0, 1], [startX, arriveX]) + interpolate(t2, [0, 1], [0, endX - arriveX]);
          const nearGate = Math.abs(left + cardWidth / 2 - x) < cardWidth / 2;
          tone = t2 > 0.05 ? "pass" : "neutral";
          if (nearGate) tone = "pass";
          if (absorb) opacity = Math.min(appear, 1 - interpolate(t2, [0.55, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
        } else if (pr.tier === "approval") {
          left = interpolate(t, [0, 1], [startX, arriveX]);
          tone = arrived ? "hold" : "neutral";
          if (arrived) {
            const pulse = 0.5 + 0.5 * Math.sin((frame - pr.delay - TRAVEL) / 6);
            extra = (
              <div
                style={{
                  position: "absolute",
                  left: arriveX,
                  top: top - 34,
                  width: cardWidth,
                  textAlign: "right",
                  fontFamily: fonts.mono,
                  fontSize: type.min,
                  color: tierColor.approval,
                  opacity: 0.6 + 0.4 * pulse,
                }}
              >
                held · waiting for a human
              </div>
            );
          }
        } else {
          left = interpolate(t, [0, 1], [startX, arriveX]);
          if (arrived) {
            const dt = frame - (pr.delay + TRAVEL);
            // One decaying shake.
            shake = dt < 14 ? Math.sin(dt * 1.1) * 12 * Math.exp(-dt / 5) : 0;
            tone = "refused";
            const sp = accentSpring(frame, fps, pr.delay + TRAVEL + 2);
            extra = (
              <div
                style={{
                  position: "absolute",
                  left: arriveX + cardWidth - 230,
                  top: top - 24,
                  padding: "8px 18px",
                  border: `4px solid ${colors.critical}`,
                  borderRadius: 10,
                  color: colors.critical,
                  fontFamily: fonts.headline,
                  fontWeight: 700,
                  fontSize: type.h2Small,
                  letterSpacing: "0.04em",
                  opacity: sp,
                  rotate: "-10deg",
                  scale: String(interpolate(sp, [0, 1], [1.8, 1])),
                  transformOrigin: "center",
                  background: `${colors.bg}cc`,
                }}
              >
                REFUSED
              </div>
            );
          }
        }

        return (
          <React.Fragment key={`${pr.label}-${i}`}>
            <ProposalCard
              label={pr.label}
              tier={pr.tier}
              tone={tone}
              width={cardWidth}
              style={{ left: left + shake, top, opacity }}
            />
            {extra}
          </React.Fragment>
        );
      })}

      {showPassLabel ? (
        <div
          style={{
            position: "absolute",
            left: x + 40,
            top: y + height / 2 + 12,
            fontFamily: fonts.mono,
            fontSize: type.min,
            color: colors.ok,
            opacity: enter,
          }}
        >
          only passed proposals reach the executor →
        </div>
      ) : null}
    </>
  );
};
