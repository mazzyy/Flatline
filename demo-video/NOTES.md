# Flatline demo video: notes

## Outputs

| File | What |
|---|---|
| `out/flatline-demo.mp4` | Submission cut. 1920×1080, 155 s, 30 fps, H.264. Narration, music and SFX, captions matched to the voice |
| `public/audio/soundtrack-v5.m4a` | Final mix (voice + music + SFX). Rendered under the picture when `hasSoundtrack` is on (the default) |
| `scripts/audio-v2/` | `build-voiceover-v2.py` → `compose-music-sfx.py` → `mix-soundtrack.py`, then `make-captions.py`; `narration.json` holds the line timings |
| `out/poster.png` | YouTube thumbnail (S3 introducing frame, no captions) |

## Scenes

Order and lengths live in `src/timeline.ts`. The demo starts at 0:26.

| # | Name | Seconds | Starts at |
|---|---|---|---|
| S1 | Hook | 8 | 0:00 |
| S2 | The problem (Recurly estimate, sourced on screen) | 10 | 0:08 |
| S3 | Introducing | 8 | 0:18 |
| S5 | Demo 1 · checkout spike (chaos panel, shop, overview, incident, approve, recovery) | 45 | 0:26 |
| S4 | How it works | 14 | 1:11 |
| S6 | Demo 2 · refund wave and the red-team probe | 22 | 1:25 |
| S7 | Demo 3 · renewals | 18 | 1:47 |
| S8 | Trust and audit | 15 | 2:05 |
| S9 | Built with | 10 | 2:20 |
| S10 | Close | 5 | 2:30 |

The clips play full width on a stage (`components/Stage.tsx`) and a camera zooms to points measured on the recording (`S5_TARGETS`, `S6_TARGETS`, `S7_TARGETS`, in clip pixels). Re-measure them after re-recording.

## Clips

All eight clips are recorded against the Docker stack (`localhost:8000` and `:3000`) on the PayPal sandbox with live models (`LLM_MODE=live`), by Playwright at 1600×900. The script waits off camera while the agents work and trims page loading. Every root cause, proposal and rationale on screen was written by the model named in its agent step; the red-team bulk refund is added by the refund playbook and labelled as such.

| File | What |
|---|---|
| `01-chaos-bad-currency.mp4` | Chaos panel, click **Ship bad currency config** |
| `02-shop-failing.mp4` | Checkout page after the agents ran: their banner, EUR on a USD shop (the PayPal button renders once the shop loads the sandbox SDK; rebuild with `make up` before recording) |
| `03-incident-opens.mp4` | Overview: checkout tile in breach, the incident with money at risk per hour |
| `04-incident-detail.mp4` | Agent timeline (models, PayPal reads through MCP), root cause, proposals |
| `05-approve.mp4` | Approve on the config rollback, held until it shows as executed |
| `06-refund-wave.mp4` | Root cause names the product; pause sales pending; red-team bulk refund refused |
| `07-renewals.mp4` | Plan read from PayPal through MCP; payment reminder sent on its own |
| `08-audit-log.mp4` | Audit log with detector, agent, policy and executor rows |

Record (with the stack up):

```
cd demo-video && node scripts/record-clips.mjs            # all clips
node scripts/record-clips.mjs --resume                   # only the missing ones
```

A new incident within 30 minutes of one for the same playbook is merged into it, so wait that long before re-taking a scenario.

## Re-render

```
npx remotion render DemoVideo out/flatline-demo.mp4 --codec=h264 --crf=18
npx remotion still DemoVideo out/poster.png --frame=600
```

To change the narration: edit `LINES` in `scripts/audio-v2/build-voiceover-v2.py`, run the three audio scripts in order, run `make-captions.py` on the new `narration.json`, then re-render.

## Decisions

- One transition family: a 12-frame fade. Policy colours never change: auto = ok, approval = warn, forbidden = critical.
- Captions are burned in from `src/captions.ts`, so the video works muted.
- Music and SFX are synthesized in code (nothing licensed); the voice is Kokoro `am_fenrir`.
- The closing card shows only the repo URL; any hosted demo link lives in the README and the Devpost text.
