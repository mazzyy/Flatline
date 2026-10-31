/**
 * Scene order and target lengths (seconds). The composition is exactly the sum
 * of these; transitions overlap into the *extra* frames added to each sequence,
 * so each scene is visible for its target length.
 */
export const SCENES = [
  { id: "s1", name: "Hook", seconds: 12 },
  { id: "s2", name: "The problem", seconds: 16 },
  { id: "s3", name: "Introducing", seconds: 12 },
  { id: "s4", name: "How it works", seconds: 25 },
  { id: "s5", name: "Demo 1 · checkout spike", seconds: 35 },
  { id: "s6", name: "Demo 2 · refund wave", seconds: 25 },
  { id: "s7", name: "Demo 3 · renewals", seconds: 15 },
  { id: "s8", name: "Trust and audit", seconds: 15 },
  { id: "s9", name: "Built with", seconds: 10 },
  { id: "s10", name: "Close", seconds: 5 },
] as const;

export type SceneIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;

export const TRANSITION_FRAMES = 12;
export const BASE_SECONDS = SCENES.reduce((a, s) => a + s.seconds, 0); // 170

export type Timeline = {
  /** Frames each TransitionSeries.Sequence gets (includes transition overlap). */
  sequenceFrames: number[];
  /** Absolute frame where each scene becomes the incoming scene. */
  sceneStart: number[];
  /** Visible frames per scene (target × scale). */
  sceneVisible: number[];
  total: number;
  scale: number;
};

export const getTimeline = (fps: number, scale = 1): Timeline => {
  const visible = SCENES.map((s) => Math.round(s.seconds * scale * fps));
  const sequenceFrames = visible.map((v, i) => (i < SCENES.length - 1 ? v + TRANSITION_FRAMES : v));
  const sceneStart: number[] = [];
  let acc = 0;
  for (const v of visible) {
    sceneStart.push(acc);
    acc += v;
  }
  return { sequenceFrames, sceneStart, sceneVisible: visible, total: acc, scale };
};

/** Seconds-in-scene → frame-in-sequence, honouring the voiceover scale. */
export const sec = (seconds: number, fps: number, scale: number): number => Math.round(seconds * scale * fps);
