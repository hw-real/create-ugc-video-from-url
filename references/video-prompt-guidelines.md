# Video Prompt Guidelines

The generation prompt is the single most important input to the video model. It is produced by `draft_video_prompt` — use only its returned `video_prompt`. This document defines what the `brief` must contain so the draft comes out right, and what the final prompt must satisfy.

## 1. What the brief must require (passed to `draft_video_prompt`)

Include ALL of these in the brief:

- **Authentic UGC camera behavior** — phone-shot, handheld, natural imperfect framing; not polished corporate-ad staging.
- **Explicit subject action & product interaction** — what the creator does (pick up, open, apply, use, hold up to camera), not a static showcase.
- **Framing, lighting, and transitions** — camera movement per shot (push-in, pan, cut, single-take), lighting direction and quality, how scenes transition.
- **Exact continuity** — creator identity, hands, wardrobe, product packaging, environment must stay identical across the video. Name the anchors explicitly.
- **Text policy** — readable text (brand names, prices, labels) added in post; do not rely on generated in-scene text, which garbles.
- **Native audio** — dialogue, room tone, music, or sound effects only when useful; the brief states what the viewer should hear.
- **Negative constraints** — no malformed hands, duplicate objects, morphing packaging, drifting labels, fake UI, random cuts, or unsupported before/after claims.

## 2. What the final prompt must satisfy

- Uses the product's real appearance: correct geometry, colors, branding, label, variant (anchored by the reference image in `image_urls`).
- One coherent action sequence per shot; each transition is intentional.
- No media URLs inside the prompt text. URLs travel only in `image_urls` / `video_urls`.
- No placeholder URLs like `https://example.com/...` anywhere.
- Positive prompt and negative constraints are not contradictory (e.g. do not say "handheld" while also forbidding camera movement).
- Duration-consistent: the prompt describes a sequence that fits the requested duration (the execution layer splits >15s automatically; describe the full logical sequence regardless).

## 3. Prompt anti-patterns

| Anti-pattern | Fix |
|--------------|-----|
| "a high-quality 4k commercial ad" | Re-specify authentic UGC camera behavior |
| Static product showcase | Add explicit creator action and interaction |
| "the logo should be perfect" | State text is added in post; keep prompt focused on motion |
| Prompt says "no text" but scene needs a label | Move the label to on-screen text overlay |
| Same person changes outfit between shots | Enforce wardrobe continuity in the brief |
| URL pasted into the prompt | Move to `image_urls` |
| Ambiguous subject (no product named) | Anchor with the real product and reference image |

## 4. Self-check before execution

If the returned `video_prompt` is empty, one sentence, or generic, retry `draft_video_prompt` once with a shorter but complete brief. Do not proceed with it.

When you run `scripts/validate_plan.py`, it independently checks the plan's prompts for URL leaks, length, and dependency issues — fix anything it flags before calling `run_paid_execution`.
