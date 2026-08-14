# Script & Shot Schema

The production plan is the contract the user approves before any paid generation. Output it as clean Markdown (never raw JSON envelopes). This document defines its exact structure.

## 1. Output structure (user-visible)

### Creative strategy

```markdown
### Creative strategy

- **Product & verified benefit**: <product name> — <one page-supported benefit>
- **Audience & pain point**: <who> — <problem>
- **Platform / duration / aspect ratio / language**: <e.g. TikTok · 15s · 9:16 · English>
- **Format & creator profile**: <format from ugc-style-library> · <creator persona>
- **Tone**: <one line, e.g. warm, direct, phone-shot>
- **Hook**: <first 1-3s line or visual>
- **CTA**: <proportionate call-to-action>
- **Asset decision**: <reuse page assets OR generate keyframe> — <one-sentence rationale>
```

### Video script

- Complete natural-language voiceover/dialogue, timed to the duration.
- First 1-3 seconds must be useful (hook), not filler.
- Spoken lines natural; demonstrate rather than assert.
- End with a proportionate CTA.

### Shot list

| Time | Visual / action | Camera | Voice / audio | On-screen text |
|------|-----------------|--------|---------------|----------------|
| 0-2s | ... | ... | ... | ... |
| 2-6s | ... | ... | ... | ... |

Constraints:

- Shot durations are contiguous and total the requested duration (e.g. 15s → 0-2, 2-6, 6-11, 11-15).
- Every shot advances the single core message; drop shots that don't.
- Each row is filmable by a video model from one prompt: one action, one location (or an explicit transition), consistent subject.

### Generation elements

State model-facing constraints separately from user-facing claims:

- **Continuity anchors**: creator identity, hands, wardrobe, product packaging, environment, lighting that must stay consistent.
- **Product-handling constraints**: how the product is held, rotated, interacted with.
- **Lighting**: key/soft light, natural window light, etc.
- **Camera language**: handheld phone-style, slow push-in, cuts vs single take.
- **Native audio direction**: dialogue, room tone, music, SFX — only when useful.
- **Negative constraints**: no morphing packaging, drifting labels, malformed hands, fake UI, random cuts, unsupported before/after, watermark.

## 2. Internal planning JSON (model-facing, never output raw)

When building the video prompt brief or running the plan scripts, represent the plan as:

```json
{
  "brief": {
    "product_name": "",
    "core_benefit": "",
    "audience": "",
    "pain_point": "",
    "format": "",
    "creator_profile": "",
    "tone": "",
    "hook": "",
    "cta": "",
    "duration": 15,
    "aspect_ratio": "9:16",
    "language": "en"
  },
  "script": "<full voiceover/dialogue text>",
  "shot_list": [
    {"start": 0, "end": 2, "visual": "", "camera": "", "voice": "", "text": ""}
  ],
  "generation": {
    "continuity_anchors": [],
    "handling": "",
    "lighting": "",
    "camera": "",
    "audio": "",
    "negatives": []
  },
  "asset_decision": {"mode": "reuse|generate", "image_urls": [], "rationale": ""}
}
```

This JSON is what `scripts/score_video_plan.py` consumes for the quality self-check.

## 3. Plan quality gates

- Durations total exactly the requested duration.
- Exactly one primary message; each shot maps to it.
- Every claim in the script is Verified or marked Inferred.
- The shot list, script, and prompt agree on product/wardrobe/environment continuity.
- The plan stops before paid generation if the user asked only for a plan/script.
