# create-ugc-video-from-url

Turn one product or landing-page URL into a high-quality, conversion-oriented **UGC video** — with a fact ledger, creative strategy, script, shot list, generation prompt, and (when requested) a generated video.

Designed for the **UGC Maker agent V3** (`ugcmaker_api`), which provides the tools this skill drives:

- `analyze_url_tool` / `analyze_webpage` — URL analysis
- `analyze_image_content` — inspect page images before deciding on generation
- `draft_video_prompt` — script + storyboard + motion-aware generation prompt
- `draft_image_prompts` — keyframe prompts (Path B)
- `run_paid_execution` — one batched, HITL-approved execution of all paid steps

## Install

In UGC Maker agent V3, activate by sending:

```json
{
  "message": "…",
  "skill_url": "https://github.com/hw-real/create-ugc-video-from-url",
  "skill_name": "create-ugc-video-from-url"
}
```

Globally via the skills CLI (for other agents):

```bash
npx skills add hw-real/create-ugc-video-from-url -y
```

## Layout

```
create-ugc-video-from-url/
├── SKILL.md                      # workflow entry point (frontmatter: name, description, metadata)
├── agents/
│   └── openai.yaml               # OpenAI Agents SDK compatible config
├── references/
│   ├── url-analysis-schema.md    # analysis output + Verified/Inferred/Forbidden ledger
│   ├── ugc-style-library.md      # UGC formats and selection rules
│   ├── script-and-shot-schema.md # production plan + shot-list output structure
│   ├── asset-decision-rules.md   # reuse page assets vs generate keyframe
│   ├── video-prompt-guidelines.md# motion-aware, continuity-safe prompt briefs
│   └── quality-rubric.md         # five quality gates and retry policy
└── scripts/
    ├── validate_plan.py          # validate run_paid_execution steps JSON before submit
    └── score_video_plan.py       # score a production plan against the five gates
```

## Workflow

1. **Resolve the brief** — infer safe defaults (15s, 9:16, 1080p, user's language).
2. **Analyze the URL** — `analyze_url_tool`, build a Verified/Inferred/Forbidden fact ledger.
3. **Decide assets** — reuse real page images unless a keyframe genuinely improves fidelity.
4. **Pick a UGC format** — problem-solution, testimonial, unboxing, tutorial, three reasons, lifestyle, money shot, try-on.
5. **Write the visible plan** — creative strategy, script, shot list, generation elements.
6. **Draft the prompt** — one `draft_video_prompt` call with the full script in `script_md`.
7. **Build + validate one execution plan** — `python3 scripts/validate_plan.py plan.json`, then one `run_paid_execution`.
8. **Close the loop** — honest status, targeted regeneration on a failed gate only.

Run `python3 scripts/score_video_plan.py plan.json` for a five-gate quality self-check (factual accuracy, product fidelity, human/hand continuity, narrative clarity, platform-ready pacing).

## License

MIT
