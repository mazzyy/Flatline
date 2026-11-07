import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { AgentNode } from "../components/AgentNode";
import { FlowArrow } from "../components/FlowArrow";
import { IncidentCard } from "../components/IncidentCard";
import { PolicyGate } from "../components/PolicyGate";
import { KineticHeadline } from "../components/KineticHeadline";
import { colors, layout, type } from "../theme";
import { uiSpring } from "../anim";
import { useT } from "../SceneContext";

/**
 * The architecture moment. Built left→right, top→bottom as narrated.
 * Row 1: sources → detector → incident. Row 2: four agents. Row 3: MCP (read),
 * policy gate, executor (write).
 */
export const S4Architecture: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = useT();

  // Row 1
  const srcW = 430;
  const shop = { x: layout.marginX, y: 150, w: srcW };
  const paypal = { x: layout.marginX, y: 272, w: srcW };
  const detector = { x: 670, y: 211, w: 390 };
  const incident = { x: 1130, y: 200, w: 480 };
  const rowH = 102;

  // Row 2
  const agentW = 390;
  const agentY = 470;
  const agentsX = [120, 550, 980, 1410];

  // Row 3
  const mcp = { x: agentsX[1] + (agentW - 340) / 2, y: 760, w: 340 };
  const gate = { x: 1440, y: 830 };
  const executor = { x: 1494, y: 779, w: 306 };

  // Timing (seconds in scene)
  const T = {
    shop: t(0.3),
    paypal: t(0.7),
    detector: t(1.2),
    arrows: t(1.7),
    dotsFrom: t(2.2),
    dotsTo: t(8.2),
    detectorPulse: t(4.8),
    incidentArrow: t(5.0),
    incident: t(5.4),
    agents: t(6.2),
    incidentToTriage: t(7.9),
    triage: t(8.6),
    diagnostician: t(11.0),
    mcp: t(11.6),
    mcpArrow: t(12.3),
    remediator: t(16.0),
    gate: t(18.3),
    executor: t(18.3),
    approval: t(19.0),
    auto: t(19.9),
    executorActive: t(21.4),
    verifier: t(21.0),
    dim: t(22.2),
    line: t(22.5),
  };

  const dim = interpolate(frame, [T.dim, T.dim + 14], [1, 0.18], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pulse = frame >= T.detectorPulse && frame < T.incident ? 0.5 + 0.5 * Math.sin((frame - T.detectorPulse) / 3) : 0;

  const center = (c: { x: number; y: number; w: number }) => ({ cx: c.x + c.w / 2, cy: c.y + rowH / 2 });
  const shopC = center(shop);
  const paypalC = center(paypal);
  const detC = center(detector);
  const incC = { cx: incident.x + incident.w / 2, cy: incident.y + 50 };

  return (
    <AbsoluteFill>
      <Background glow="accent" glowStrength={0.16} />
      <div style={{ position: "absolute", inset: 0, opacity: dim }}>
        {/* Row 1 */}
        <AgentNode compact x={shop.x} y={shop.y} width={shop.w} name="Demo shop" role="Lumen Coffee Co. · telemetry" icon="shop" delay={T.shop} />
        <AgentNode compact x={paypal.x} y={paypal.y} width={paypal.w} name="PayPal sandbox" role="webhooks" icon="paypal" delay={T.paypal} />
        <FlowArrow d={`M ${shop.x + shop.w} ${shopC.cy} C ${shop.x + shop.w + 90} ${shopC.cy} ${detector.x - 90} ${detC.cy - 12} ${detector.x - 4} ${detC.cy - 12}`} delay={T.arrows} dots={{ count: 3, period: 40, start: T.dotsFrom, end: T.dotsTo }} />
        <FlowArrow d={`M ${paypal.x + paypal.w} ${paypalC.cy} C ${paypal.x + paypal.w + 90} ${paypalC.cy} ${detector.x - 90} ${detC.cy + 12} ${detector.x - 4} ${detC.cy + 12}`} delay={T.arrows + 6} dots={{ count: 3, period: 46, start: T.dotsFrom + 10, end: T.dotsTo }} />
        <AgentNode compact x={detector.x} y={detector.y} width={detector.w} name="Detector" role="baseline vs. 5-min window" icon="detector" delay={T.detector} active={frame >= T.detectorPulse} activeColor={colors.critical} activeDelay={T.detectorPulse} />
        <div
          style={{
            position: "absolute",
            left: detector.x - 10,
            top: detector.y - 10,
            width: detector.w + 20,
            height: rowH + 20,
            borderRadius: 22,
            border: `2px solid ${colors.critical}`,
            opacity: pulse * 0.6,
            scale: String(1 + pulse * 0.03),
          }}
        />
        <FlowArrow d={`M ${detector.x + detector.w} ${detC.cy} L ${incident.x - 4} ${detC.cy}`} delay={T.incidentArrow} color={colors.critical} />
        <IncidentCard x={incident.x} y={incident.y} width={incident.w} title="Checkout failure spike" sub="incident · 6 vs baseline 1" delay={T.incident} />

        {/* Incident → Triage */}
        <FlowArrow
          d={`M ${incC.cx} ${incident.y + 104} C ${incC.cx} ${incident.y + 230} ${agentsX[0] + agentW / 2} ${agentY - 120} ${agentsX[0] + agentW / 2} ${agentY - 4}`}
          delay={T.incidentToTriage}
          color={colors.critical}
          duration={26}
        />

        {/* Row 2: agents */}
        {[
          { name: "Triage", role: "scope · severity · $ at risk", icon: "triage" as const, at: T.triage },
          { name: "Diagnostician", role: "root cause with evidence", icon: "diagnose" as const, at: T.diagnostician },
          { name: "Remediator", role: "proposes catalog actions", icon: "remediate" as const, at: T.remediator },
          { name: "Verifier", role: "confirms recovery", icon: "verify" as const, at: T.verifier },
        ].map((a, i) => (
          <React.Fragment key={a.name}>
            <AgentNode compact x={agentsX[i]} y={agentY} width={agentW} name={a.name} role={a.role} icon={a.icon} delay={T.agents + i * 5} active={frame >= a.at} activeDelay={a.at} />
            {i < 3 ? (
              <FlowArrow d={`M ${agentsX[i] + agentW} ${agentY + rowH / 2} L ${agentsX[i + 1] - 4} ${agentY + rowH / 2}`} delay={T.agents + 20 + i * 5} duration={14} />
            ) : null}
          </React.Fragment>
        ))}

        {/* Row 3: read scope */}
        <AgentNode compact x={mcp.x} y={mcp.y} width={mcp.w} name="PayPal MCP" role="read scope only" icon="mcp" delay={T.mcp} dashed />
        <FlowArrow d={`M ${mcp.x + mcp.w / 2} ${mcp.y} L ${mcp.x + mcp.w / 2} ${agentY + rowH + 4}`} delay={T.mcpArrow} dashed color={colors.accent} label="read only" labelOffset={{ x: 112, y: 0 }} />

        {/* Row 3: gate + executor */}
        <PolicyGate
          x={gate.x}
          y={gate.y}
          height={200}
          startX={700}
          endX={1500}
          delay={T.gate}
          cardWidth={440}
          absorb
          proposals={[
            { label: "Roll back config", tier: "approval", delay: T.approval },
            { label: "Set shop banner", tier: "auto", delay: T.auto },
          ]}
        />
        <FlowArrow d={`M ${agentsX[2] + agentW / 2} ${agentY + rowH} L ${agentsX[2] + agentW / 2} ${gate.y - 100 - 100}`} delay={T.gate - 10} duration={14} />
        <AgentNode compact x={executor.x} y={executor.y} width={executor.w} name="Executor" role="write scope" icon="executor" delay={T.executor} active={frame >= T.executorActive} activeColor={colors.ok} activeDelay={T.executorActive} />
      </div>

      {/* Final framing line */}
      {frame >= T.line ? (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 1560, opacity: uiSpring(frame, fps, T.line) }}>
            <KineticHeadline text="Agents read. Code decides. Only the executor writes." size={type.h1Small} delay={T.line} align="center" />
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
