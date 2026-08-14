# Asset Decision Rules

Decide between **Path A (reuse page assets)** and **Path B (generate a supporting keyframe)**. Default to Path A. Generation is a tool for fixing gaps, not a default.

## Decision procedure

1. Run `analyze_url_tool` and collect `image_urls`.
2. If the roles/quality of the page images are unclear, inspect them with `analyze_image_content` (free).
3. Apply the checks below.

### Path A — reuse page assets (default)

Use the real product image as the video's `image_urls` reference when at least one page image:

- clearly shows the correct product and packaging
- is large and unobstructed enough to serve as a reference
- supports the planned product interaction or hero shot
- is free of watermark, collage, severe crop, or a misleading variant

A single adequate image is enough. Pass it through `image_urls`; never embed the URL in the prompt text.

### Path B — generate a supporting image (only when required)

Set `image_generation_required = true` ONLY when:

- no usable product image is available from the page, OR
- a stable first frame, creator-product composite, or a missing use scene materially improves fidelity (e.g. the video model needs a person interacting with a product the page only shows as a studio shot), OR
- the video model needs a visual anchor to preserve the exact product or character, OR
- the user explicitly asks for a generated keyframe or creator image.

Prefer Path A when product packaging or label text is likely to drift in generation (brands, nutrition facts, fine print). Real logos/labels reproduce best from a real reference, not from a prompt.

## Keyframe rules (when Path B)

- Preserve the real product's geometry, colors, branding, label, and variant. Use the actual product image as the generation reference via `image_urls`.
- Normally generate exactly one keyframe (`num: 1`). Only generate more when the video needs multiple distinct scenes, each with a different anchor.
- Run `draft_image_prompts` first; forward only its `image_prompts` list.
- The video step must reference the keyframe via `image_urls: ["@ugc_keyframe"]` and declare `depends_on: ["ugc_keyframe"]`.

## Cost / fidelity trade-off

| Situation | Decision | Why |
|-----------|----------|-----|
| Real page image adequate | Path A | Cheaper, exact fidelity |
| Only a studio product shot, but video needs a person using it | Path B (one keyframe) | The video model needs the composite anchor |
| Packaging with fine print / logo | Path A if any usable image; avoid keyframe text drift | Generated label text will likely garble |
| User explicitly wants a generated keyframe | Path B | User intent wins |
| No usable image at all | Path B or ask for a working URL | Never invent the product |

## Post-execution rule

Do not regenerate an adequate supporting image when only the video motion failed — change only the failed dimension (see SKILL.md Phase 8).
