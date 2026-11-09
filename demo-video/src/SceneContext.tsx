import React, { createContext, useCallback, useContext } from "react";
import { useVideoConfig } from "remotion";

export type ClipAvailability = Record<string, boolean>;

export type SceneContextValue = {
  scale: number;
  clips: ClipAvailability;
};

export const SceneContext = createContext<SceneContextValue>({ scale: 1, clips: {} });

/** Per-scene playback speed of the scene's own animation (see timeline.ts). */
export const SceneSpeedContext = createContext(1);

/** `t(seconds)` → frames within the current scene, honouring the voiceover scale and scene speed. */
export const useT = () => {
  const { fps } = useVideoConfig();
  const { scale } = useContext(SceneContext);
  const speed = useContext(SceneSpeedContext);
  return useCallback((seconds: number) => Math.round((seconds * scale * fps) / speed), [fps, scale, speed]);
};

export const useClips = () => useContext(SceneContext).clips;

export const CLIP_FILES = [
  "01-chaos-bad-currency.mp4",
  "02-shop-failing.mp4",
  "03-incident-opens.mp4",
  "04-incident-detail.mp4",
  "05-approve.mp4",
  "06-refund-wave.mp4",
  "07-renewals.mp4",
  "08-audit-log.mp4",
  "09-transactions.mp4",
] as const;

export type ClipName = (typeof CLIP_FILES)[number];

export const SceneProvider: React.FC<{ value: SceneContextValue; children: React.ReactNode }> = ({ value, children }) => (
  <SceneContext.Provider value={value}>{children}</SceneContext.Provider>
);
