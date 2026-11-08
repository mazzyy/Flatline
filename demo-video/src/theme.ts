import { loadFont as loadInterTight } from "@remotion/google-fonts/InterTight";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadJetBrains } from "@remotion/google-fonts/JetBrainsMono";

/** Single source of truth for colours. Use nowhere else as literals. */
export const colors = {
  bg: "#0B0D12",
  surface: "#141821",
  surfaceRaised: "#1C2230",
  line: "#2A3242",
  text: "#F2F4F8",
  textMuted: "#8A93A6",
  accent: "#4C8DFF",
  ok: "#3DD68C",
  warn: "#F5B83D",
  critical: "#FF5C5C",
} as const;

export type Tier = "auto" | "approval" | "forbidden";

export const tierColor: Record<Tier, string> = {
  auto: colors.ok,
  approval: colors.warn,
  forbidden: colors.critical,
};

const headline = loadInterTight("normal", { weights: ["700"], subsets: ["latin"] });
const body = loadInter("normal", { weights: ["400", "500"], subsets: ["latin"] });
const mono = loadJetBrains("normal", { weights: ["500"], subsets: ["latin"] });

export const fonts = {
  headline: headline.fontFamily,
  body: body.fontFamily,
  mono: mono.fontFamily,
} as const;

export const type = {
  h1: 96,
  h1Large: 112,
  h1Small: 88,
  h2: 48,
  h2Small: 44,
  label: 30,
  labelSmall: 28,
  caption: 34,
  min: 24,
} as const;

export const layout = {
  width: 1920,
  height: 1080,
  marginX: 120,
  marginY: 96,
  columns: 12,
  gutter: 24,
} as const;

export const contentWidth = layout.width - layout.marginX * 2;
export const columnWidth =
  (contentWidth - layout.gutter * (layout.columns - 1)) / layout.columns;

/** Left edge of a 1-based column. */
export const colX = (col: number): number =>
  layout.marginX + (col - 1) * (columnWidth + layout.gutter);

/** Width spanning n columns. */
export const colW = (n: number): number => n * columnWidth + (n - 1) * layout.gutter;

export const radius = {
  card: 16,
  frame: 20,
  pill: 999,
} as const;

export const shadow = {
  soft: "0 24px 64px rgba(0, 0, 0, 0.45)",
  glow: (color: string) => `0 0 0 1px ${color}55, 0 0 48px ${color}44`,
} as const;

export const product = {
  name: "Flatline",
  tagline: "An on-call SRE agent for your PayPal revenue.",
  closeTagline: "On call for your revenue.",
  repoUrl: "github.com/mazzyy/Flatline",
} as const;
