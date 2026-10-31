import { Easing, interpolate, spring } from "remotion";

/** UI entrance: no bounce. */
export const uiSpring = (frame: number, fps: number, delay = 0): number =>
  spring({ frame: frame - delay, fps, config: { damping: 200 } });

/** Accent entrance: a little life. */
export const accentSpring = (frame: number, fps: number, delay = 0): number =>
  spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.8 } });

/** 0→1 over `duration` frames starting at `delay`, with a premium ease-out. */
export const ease = (frame: number, delay: number, duration: number): number =>
  interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

/** Linear 0→1 clamp. */
export const lin = (frame: number, delay: number, duration: number): number =>
  interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Slide-up + fade reveal from a progress value. */
export const reveal = (p: number, distance = 24): React.CSSProperties => ({
  opacity: p,
  translate: `0px ${(1 - p) * distance}px`,
});

/** Fade-out near the end of a sequence. */
export const fadeOut = (frame: number, durationInFrames: number, frames = 10): number =>
  interpolate(frame, [durationInFrames - frames, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

export const STAGGER = 5;
