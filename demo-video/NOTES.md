# Flatline demo video — notes

## Outputs

| File | What |
|---|---|
| `out/demo-video.mp4` | Master, 1920×1080, 170.0 s, 42 MB, H.264 CRF 18 |
| `out/demo-video-720.mp4` | Preview, 1280×720, 13 MB (ffmpeg scale of the master) |
| `out/poster.png` | YouTube thumbnail, S3 introducing frame |
| `out/stills/` | Review stills per scene |

## Final duration

170 s (5100 frames) at 1920×1080, 30 fps. No voiceover on disk, so scenes are not stretched.

## Placeholders

`{{PROJECT_NAME}}` → **Flatline**  
`{{REPO_URL}}` → `github.com/mazzyy/Flatline`  
`{{DEMO_URL}}` → `flatline-api.onrender.com` (not yet live; swap the string in `src/theme.ts` `product.demoUrl` when Render is up)

## Scenes

| # | Name | Seconds | Frames |
|---|---|---|---|
| S1 | Hook | 12 | 0–360 |
| S2 | The problem | 16 | 360–840 |
| S3 | Introducing | 12 | 840–1200 |
| S4 | How it works | 25 | 1200–1950 |
| S5 | Demo 1 · checkout spike | 35 | 1950–3000 |
| S6 | Demo 2 · refund wave | 25 | 3000–3750 |
| S7 | Demo 3 · renewals | 15 | 3750–4200 |
| S8 | Trust and audit | 15 | 4200–4650 |
| S9 | Built with | 10 | 4650–4950 |
| S10 | Close | 5 | 4950–5100 |

12-frame fades overlap the extra frames on each sequence, so each scene is visible for its target length. Total stays 170 s.

## Assets

All eight clips were recorded against the live Docker stack (`localhost:8000` + `:3000`) with Playwright at 1600×900, then transcoded to H.264.

| File | Notes |
|---|---|
| `01-chaos-bad-currency.mp4` | Chaos panel, click **Ship bad currency config** |
| `02-shop-failing.mp4` | Lumen Coffee shop with the auto banner (“Checkout is being repaired”) — the banner is the visible failure, not a live 500 page |
| `03-incident-opens.mp4` | Overview: checkout tile in Breach, incident awaiting approval, $108/h |
| `04-incident-detail.mp4` | Root cause + proposals + agent timeline |
| `05-approve.mp4` | Approve click on config rollback |
| `06-refund-wave.mp4` | First ~3 s is the Chaos click; composition trims those (`trimBefore={90}`) to land on the incident (`refund.bulk` refused) |
| `07-renewals.mp4` | Same trim; reminder auto + capture outstanding pending |
| `08-audit-log.mp4` | Audit table with policy / executor / agent rows |
| `audio/voiceover.mp3` | **Missing.** Record from `public/audio/SCRIPT.txt` and drop it here |
| `audio/music.mp3` | **Missing on purpose.** No royalty-free track was bundled |

Re-record clips: with the stack up (`make up`),

```
cd demo-video && node scripts/record-clips.mjs
```

`--resume` skips files that already exist.

## Decisions

- Dark Linear/Vercel palette from the brief. Brand accent `#4C8DFF`. Policy colours never change: auto = ok, approval = warn, forbidden = critical.
- One transition family: 12-frame fade (`@remotion/transitions`).
- Captions are burned in from `src/captions.ts` so the video works without a voiceover.
- Remotion’s bundled Chrome crashed (`Target closed`) on this Mac. Renders use system Chrome via `Config.setBrowserExecutable`.
- `OffthreadVideo` is not looped (Remotion requires a finite `durationInFrames` on the wrapping Sequence). Short clips hold / end; overlays carry the beat.
- Shop clip shows the honest-banner state rather than a raw capture 500 — that is what the live shop looks like after the auto action.
- `DemoVideoVertical` (1080×1920) was not built. The submission asset is the 16:9 file.
- Illustrative revenue-lost number in S2 is `$12,480`, labelled “illustrative”.

## Re-render

From `demo-video/`:

```
# stills
npx remotion still DemoVideo out/stills/s3-mid.png --frame=1020

# master
npx remotion render DemoVideo out/demo-video.mp4 --codec=h264 --crf=18

# 720p preview
npx remotion render DemoVideo out/demo-video-720.mp4 --codec=h264 --crf=20 --scale=0.6666667

# poster (S3 introducing)
npx remotion still DemoVideo out/poster.png --frame=1020
```

After adding `public/audio/voiceover.mp3`, restore `calculateMetadata` in `src/Root.tsx` (see git history / the first version) so a voiceover longer than 170 s stretches every scene. Then re-render.
