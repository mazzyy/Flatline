import React from "react";
import { Easing, Freeze, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BrowserFrame } from "./BrowserFrame";
import { Clip } from "./Clip";

/** Clips are recorded at this viewport. */
export const CLIP_W = 1600;
export const CLIP_H = 900;

/** One full-width browser frame for the live clips. */
export const STAGE = { x: 110, y: 46, w: 1700 };
export const STAGE_SCALE = STAGE.w / CLIP_W;
export const STAGE_H = 44 + (STAGE.w * CLIP_H) / CLIP_W;

/** Clip pixel → scene pixel, for the full-width stage. */
export const onStage = (pt: { x: number; y: number }) => ({
  x: STAGE.x + pt.x * STAGE_SCALE,
  y: STAGE.y + 44 + pt.y * STAGE_SCALE,
});

/**
 * Plays a clip from `from` (frames, scene-relative) and holds its last frame
 * for as long as the beat lasts.
 */
export const ClipBeat: React.FC<{ name: string; available: boolean; from: number; clipSeconds: number; startAt?: number }> = ({
  name,
  available,
  from,
  clipSeconds,
  startAt = 0, // seconds into the clip to start from
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const trimBefore = Math.round(startAt * fps);
  const last = Math.max(0, Math.floor((clipSeconds - startAt) * fps) - 2);
  if (!available) return <Clip name={name} available={false} />;
  const video = (
    <OffthreadVideo
      src={staticFile(`clips/${name}`)}
      muted
      trimBefore={trimBefore || undefined}
      style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top left" }}
    />
  );
  if (frame < from) return <Freeze frame={0}>{video}</Freeze>; // hold the first frame until it plays
  if (frame - from >= last) return <Freeze frame={last}>{video}</Freeze>;
  return (
    <Sequence from={from} layout="none">
      {video}
    </Sequence>
  );
};

export const StageFrame: React.FC<{ url: string; delay?: number; children: React.ReactNode }> = ({ url, delay = 0, children }) => (
  <BrowserFrame x={STAGE.x} y={STAGE.y} width={STAGE.w} height={STAGE_H} url={url} delay={delay} pushIn={false}>
    {children}
  </BrowserFrame>
);

/** Camera keyframe in scene seconds: zoom `s` centred on scene point (x, y). */
export type CamKey = { at: number; s: number; x: number; y: number };
const camEase = Easing.bezier(0.65, 0, 0.35, 1);

export const cameraAt = (keys: CamKey[], sec: number): { s: number; x: number; y: number } => {
  if (sec <= keys[0].at) return keys[0];
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (sec <= b.at) {
      const e = camEase((sec - a.at) / (b.at - a.at));
      // zoom in log space, straight from one framing to the next
      const logS = Math.log(a.s) + (Math.log(b.s) - Math.log(a.s)) * e;
      return { s: Math.exp(logS), x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e };
    }
  }
  return keys[keys.length - 1];
};

/**
 * Transform for a stage zoomed by the camera; keeps the zoomed point inside the frame.
 * `lift` lets the view sit that many pixels lower than the frame edge allows, which moves
 * the stage up and leaves the bottom of the frame to the captions.
 */
export const cameraStyle = (cam: { s: number; x: number; y: number }, lift = 0): React.CSSProperties => {
  const half = { w: 960 / cam.s, h: 540 / cam.s };
  const x = Math.min(1920 - half.w, Math.max(half.w, cam.x));
  const y = Math.min(1080 - half.h + lift, Math.max(half.h, cam.y));
  return {
    transformOrigin: "0 0",
    transform: `translate(${960 - cam.s * x}px, ${540 - cam.s * y}px) scale(${cam.s})`,
  };
};

/** A wide-view camera key centred on the frame. */
export const WIDE = (at: number): CamKey => ({ at, s: 1, x: 960, y: 540 });

/**
 * The resting view for a clip: the whole page, lifted so the captions below never cover
 * it. Points of interest get a Highlight, not a zoom. Use with cameraStyle(cam, VIEW_LIFT).
 */
export const VIEW_LIFT = 40;
export const VIEW = (at: number): CamKey => ({ at, s: 1, x: 960, y: 540 + VIEW_LIFT });
