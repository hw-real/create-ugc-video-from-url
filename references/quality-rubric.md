# Quality Rubric

Judge every URL-to-video plan and result against five gates. A gate below 4/5 justifies a targeted retry of only that dimension. This rubric is the scoring logic behind `scripts/score_video_plan.py`.

## The five gates

### G1 — Factual accuracy (claims & evidence)

| Score | Behavior |
|-------|----------|
| 5 | Every claim Verified or clearly Inferred; no Forbidden claims; gaps declared |
| 4 | Minor inferred wording that could read as fact, easily fixable |
| 3 | One unsupported factual claim (price, result, spec) present |
| 2 | Multiple unsupported or invented claims; scarcity/review fabrication |
| 1 | Script actively misleads about product facts or results |

### G2 — Product fidelity (identity preserved)

| Score | Behavior |
|-------|----------|
| 5 | Product geometry, colors, branding, label, variant preserved; reference used |
| 4 | Minor drift unlikely; no extra object invented |
| 3 | Packaging/label likely to drift; generated keyframe without real reference |
| 2 | Branding or variant visibly wrong or invented |
| 1 | Product unrecognizable vs the page |

### G3 — Human & hand continuity

| Score | Behavior |
|-------|----------|
| 5 | One consistent creator; hands/wardrobe/environment stable across shots |
| 4 | Minor risk of hand morphing in fast transitions, acceptable |
| 3 | Outfit or setting changes without a transition reason |
| 2 | Creator identity shifts between shots; hands likely malformed |
| 1 | Multiple persons/characters or severe hand artifacts expected |

### G4 — Narrative clarity

| Score | Behavior |
|-------|----------|
| 5 | One core message; hook in first 1-3s; every shot advances it; clear CTA |
| 4 | Slightly loose structure, message still clear |
| 3 | Two competing messages, or weak hook/CTA |
| 2 | Message muddled; shots don't connect |
| 1 | No coherent storyline |

### G5 — Platform-ready pacing

| Score | Behavior |
|-------|----------|
| 5 | Shot durations total the requested duration; rhythm fits 15s short-form |
| 4 | Minor timing slack, no dead air |
| 3 | Shot durations don't sum to target; dead sections |
| 2 | Severely over/under-duration; long static showcase |
| 1 | Unwatchable pacing for short-form |

## Retry policy

- Retry only the failed gate, with a targeted instruction (e.g. "keep the creator's white tee and same hands", "shorten shot 3", "add a CTA line", "swap the claim to Inferred wording").
- If G2 or G3 fails, prefer regenerating with a real reference image rather than a pure prompt re-roll.
- If only the video motion failed, do not regenerate an adequate supporting image.
- If the user's original brief caused the failure (e.g. impossible length), restate the trade-off and confirm before spending more credits.

## Script integration

`scripts/score_video_plan.py` reads the plan JSON (schema in `script-and-shot-schema.md` §2) and reports per-gate scores plus machine-checkable checks (duration sum, hook presence, CTA presence, prompt URL leaks, shot-list/script mismatch). Fix anything below 4, then re-score before executing.
