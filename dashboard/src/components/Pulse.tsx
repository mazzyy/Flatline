import { useEffect, useRef } from "react";

const PERIOD = 0.92;
const ALIVE = "#3DDC97";
const FLAT = "#FF4D4D";

/** One heartbeat, phase 0..1: a small P wave, the QRS spike, a T wave. Same curve as the film. */
function beat(p: number): number {
  const g = (x: number, m: number, s: number, a: number) => a * Math.exp(-((x - m) ** 2) / (2 * s * s));
  return g(p, 0.18, 0.035, 0.1) - g(p, 0.3, 0.012, 0.14) + g(p, 0.33, 0.014, 1) - g(p, 0.365, 0.014, 0.26) + g(p, 0.58, 0.06, 0.2);
}

type Change = { at: number; alive: boolean };

/**
 * The revenue monitor from the film, live: a scrolling trace whose right edge is now.
 * Green and beating while the shop takes payments, red and flat while checkout is down.
 */
export default function Pulse({ alive, height = 120, seconds = 7, stroke = 3, head = true }: { alive: boolean; height?: number; seconds?: number; stroke?: number; head?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const changes = useRef<Change[]>([{ at: -1e9, alive }]);

  useEffect(() => {
    const last = changes.current[changes.current.length - 1];
    if (last.alive !== alive) changes.current.push({ at: performance.now() / 1000, alive });
    if (changes.current.length > 12) changes.current.splice(0, changes.current.length - 12);
  }, [alive]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const stateAt = (s: number): Change => {
      let cur = changes.current[0];
      for (const c of changes.current) if (c.at <= s) cur = c;
      return cur;
    };
    const signal = (s: number): number => {
      const cur = stateAt(s);
      if (cur.alive) {
        const origin = cur.at < -1e8 ? 0 : cur.at + 0.05 - 0.33 * PERIOD;
        const ph = (((s - origin) % PERIOD) + PERIOD) % PERIOD;
        return beat(ph / PERIOD);
      }
      // The beat dies over about a second and a half, then the line is flat.
      const since = s - cur.at;
      if (since > 1.6) return 0;
      const ph = ((s % PERIOD) + PERIOD) % PERIOD;
      return Math.max(0, 0.45 - since / 1.6) * beat(ph / PERIOD);
    };

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const now = performance.now() / 1000;
      const mid = h * 0.62;
      const amp = h * 0.54;
      const n = Math.max(60, Math.round(w / 3));
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      let prevX = 0;
      let prevY = mid - signal(now - seconds) * amp;
      for (let i = 1; i <= n; i++) {
        const x = (i / n) * w;
        const s = now - ((w - x) / w) * seconds;
        const y = mid - signal(s) * amp;
        const color = stateAt(s).alive ? ALIVE : FLAT;
        ctx.globalAlpha = Math.min(1, (x / w) * 6); // fades in from the left edge
        ctx.strokeStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = stroke * 3;
        ctx.lineWidth = stroke;
        ctx.beginPath();
        ctx.moveTo(prevX, prevY);
        ctx.lineTo(x, y);
        ctx.stroke();
        prevX = x;
        prevY = y;
      }
      if (head) {
        const color = stateAt(now).alive ? ALIVE : FLAT;
        ctx.globalAlpha = 1;
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = stroke * 5;
        ctx.beginPath();
        ctx.arc(w - stroke * 1.5, prevY, stroke * 1.4, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0;
      if (!still) raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [seconds, stroke, head]);

  return <canvas ref={ref} style={{ width: "100%", height, display: "block" }} aria-hidden="true" />;
}
