#!/usr/bin/env python3
"""score_video_plan.py — score a UGC video production plan against the five
quality gates (see references/quality-rubric.md).

Input plan JSON (schema in references/script-and-shot-schema.md §2):
{
  "brief": {"product_name", "core_benefit", "audience", "pain_point", "format",
            "creator_profile", "tone", "hook", "cta", "duration", "aspect_ratio", "language"},
  "script": "<voiceover text>",
  "shot_list": [{"start", "end", "visual", "camera", "voice", "text"}],
  "generation": {"continuity_anchors": [], "handling", "lighting", "camera",
                 "audio", "negatives": []},
  "asset_decision": {"mode": "reuse|generate", "image_urls": [], "rationale"},
  "video_prompt": "<optional generation prompt>"
}

Gates: G1 factual_accuracy, G2 product_fidelity, G3 human_hand_continuity,
G4 narrative_clarity, G5 platform_ready_pacing. Each 1-5 with rationale.
Machine checks: duration sum, hook, CTA, prompt URL leaks, reference usage.

Usage:
    python3 score_video_plan.py <plan.json>
    python3 score_video_plan.py -                  # stdin
    python3 score_video_plan.py --json '<plan>'

Exit code: 0 always; scores are advisory.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
CTA_WORDS = re.compile(
    r"\b(buy now|shop now|get it|order now|link in bio|try it|grab it|check it out|"
    r"comment|dm me|first link|learn more|visit|点击|购买|下单|橱窗|评论区|主页|去逛逛|冲|安排)\b",
    re.IGNORECASE,
)
ABSOLUTE_CLAIM_WORDS = re.compile(
    r"\b(100%|guarantee[d]?|the best|#1|no\.1|cure|cures|treat[s]? |"
    r"proven to|instantly|effortlessly|lose \d+|\d+% of|safest|perfectly safe|"
    r"永久|绝对|最|第一|治愈|根治|秒杀|百分百|保证)\b",
    re.IGNORECASE,
)
HAND_RISK_WORDS = re.compile(
    r"\b(hand|fingers|hands|手|手指)\b", re.IGNORECASE,
)
FLOAT_TOLERANCE = 0.6


def _load_plan(argv: list[str]) -> dict:
    args = argv[1:]
    if not args:
        print(json.dumps({"error": "no input: pass <plan.json>, '-' for stdin, or --json '<plan>'"}, ensure_ascii=False, indent=2))
        sys.exit(1)
    if args[0] == "--json":
        raw = args[1]
    elif args[0] == "-":
        raw = sys.stdin.read()
    else:
        with open(args[0], "r", encoding="utf-8") as f:
            raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc}"}, ensure_ascii=False, indent=2))
        sys.exit(1)
    if not isinstance(data, dict):
        print(json.dumps({"error": "plan root must be a JSON object"}, ensure_ascii=False, indent=2))
        sys.exit(1)
    return data


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _gather_text(plan: dict) -> str:
    parts = [plan.get("script", ""), plan.get("video_prompt", "")]
    gen = plan.get("generation") or {}
    for k in ("handling", "lighting", "camera", "audio"):
        parts.append(gen.get(k, ""))
    parts.extend(gen.get("negatives", []))
    parts.extend(gen.get("continuity_anchors", []))
    brief = plan.get("brief") or {}
    for k in ("hook", "cta", "core_benefit", "tone", "creator_profile"):
        parts.append(brief.get(k, ""))
    for shot in plan.get("shot_list", []):
        if isinstance(shot, dict):
            for k in ("visual", "camera", "voice", "text"):
                parts.append(shot.get(k, ""))
    return "\n".join(str(p) for p in parts)


def _duration_checks(plan: dict, checks: list[dict], reasons: list[str]) -> float:
    brief = plan.get("brief") or {}
    target = _num(plan.get("duration", brief.get("duration", 0)))
    shots = plan.get("shot_list")
    if not isinstance(shots, list) or not shots:
        checks.append({"check": "shot_list present", "ok": False, "detail": "shot_list empty"})
        reasons.append("shot_list empty — cannot verify pacing")
        return 0.0

    total = 0.0
    prev_end = 0.0
    contiguous = True
    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        start, end = _num(shot.get("start")), _num(shot.get("end"))
        total += max(0.0, end - start)
        if abs(start - prev_end) > FLOAT_TOLERANCE and i > 0:
            contiguous = False
        prev_end = end

    checks.append({"check": "shots contiguous", "ok": contiguous, "detail": f"prev_end={prev_end:.1f}"})
    if target > 0:
        ok = abs(total - target) <= FLOAT_TOLERANCE
        checks.append({
            "check": "duration matches target",
            "ok": ok,
            "detail": f"sum={total:.1f}s target={target:.1f}s",
        })
        if not ok:
            reasons.append(f"shot durations sum to {total:.1f}s but target is {target:.1f}s")
    return total


def _score_plan(plan: dict) -> dict:
    brief = plan.get("brief") or {}
    gen = plan.get("generation") or {}
    asset = plan.get("asset_decision") or {}
    shots = plan.get("shot_list") or []
    script = plan.get("script", "")
    text = _gather_text(plan)

    checks: list[dict] = []
    reasons: dict[str, list[str]] = {f"G{i}": [] for i in range(1, 6)}

    # ── Machine checks ──
    _duration_checks(plan, checks, reasons["G5"])

    hook = brief.get("hook", "")
    checks.append({"check": "hook present", "ok": _is_text(hook), "detail": f"hook={hook!r}"})
    if not _is_text(hook):
        reasons["G4"].append("no explicit hook in brief")

    cta_text = brief.get("cta", "")
    has_cta = _is_text(cta_text) or bool(CTA_WORDS.search(script or ""))
    checks.append({"check": "CTA present", "ok": has_cta, "detail": f"cta={cta_text!r}"})
    if not has_cta:
        reasons["G4"].append("no CTA found in brief or script")

    checks.append({"check": "script non-empty", "ok": _is_text(script), "detail": f"{len(str(script))} chars"})
    if not _is_text(script):
        reasons["G4"].append("script is empty")

    prompt = plan.get("video_prompt", "")
    leaked = URL_RE.findall(str(prompt)) if prompt else []
    checks.append({"check": "no URL leak in prompt", "ok": not leaked, "detail": f"leaked={leaked[:3]}"})
    if leaked:
        reasons["G1"].append("video_prompt contains URLs — must move to image_urls")

    anchors = gen.get("continuity_anchors", [])
    checks.append({"check": "continuity anchors set", "ok": bool(anchors), "detail": f"{len(anchors)} anchors"})
    if not anchors:
        reasons["G3"].append("no continuity anchors (creator, hands, wardrobe, environment)")

    # ── G1 factual accuracy ──
    g1 = 5
    if ABSOLUTE_CLAIM_WORDS.search(text):
        g1 = max(1, g1 - 2)
        reasons["G1"].append("absolute/regulatory wording detected (100%, guaranteed, cure, best…)")
    if not isinstance(script, str) or len(str(script).split()) < 8:
        g1 = max(1, g1 - 1)
        reasons["G1"].append("script too thin to be evidence-grounded")
    if leaked:
        g1 = max(1, g1 - 1)

    # ── G2 product fidelity ──
    g2 = 5
    mode = asset.get("mode", "reuse")
    refs = asset.get("image_urls", [])
    if mode == "generate" and not refs:
        g2 = max(1, g2 - 2)
        reasons["G2"].append("generating without any real reference image risks product drift")
    if mode == "generate":
        reasons["G2"].append(f"generating keyframe (mode={mode}) — ensure real page image used as reference")
    if not refs and mode != "generate":
        reasons["G2"].append("no reference image_urls declared in asset_decision")

    # ── G3 human & hand continuity ──
    g3 = 5
    if not anchors:
        g3 = max(1, g3 - 1)
    if HAND_RISK_WORDS.search(text) and not anchors:
        g3 = max(1, g3 - 1)
        reasons["G3"].append("hands appear but no continuity anchor names them")
    if len({str(s.get("visual", "")).strip() for s in shots if isinstance(s, dict) and str(s.get("visual", "")).strip()}) == 0:
        g3 = max(1, g3 - 1)
        reasons["G3"].append("no shot visuals to judge consistency")

    # ── G4 narrative clarity ──
    g4 = 5
    if not _is_text(hook):
        g4 = max(1, g4 - 1)
    if not has_cta:
        g4 = max(1, g4 - 1)
    if not _is_text(script):
        g4 = max(1, g4 - 2)

    # ── G5 pacing ──
    g5 = 5
    if not isinstance(shots, list) or not shots:
        g5 = 1
    else:
        total = sum(max(0.0, _num(s.get("end")) - _num(s.get("start"))) for s in shots if isinstance(s, dict))
        target = _num(plan.get("duration", brief.get("duration", 0)))
        if target > 0 and abs(total - target) > FLOAT_TOLERANCE:
            g5 = max(1, g5 - 2)
        elif target == 0:
            g5 = max(1, g5 - 1)

    scores = {
        "G1_factual_accuracy": {"score": g1, "max": 5, "rationale": reasons["G1"] or ["claims appear grounded; keep Verified/Inferred discipline"]},
        "G2_product_fidelity": {"score": g2, "max": 5, "rationale": reasons["G2"] or ["real reference in use; product identity anchored"]},
        "G3_human_hand_continuity": {"score": g3, "max": 5, "rationale": reasons["G3"] or ["continuity anchors cover creator/hands/wardrobe/environment"]},
        "G4_narrative_clarity": {"score": g4, "max": 5, "rationale": reasons["G4"] or ["single message with hook and CTA"]},
        "G5_platform_ready_pacing": {"score": g5, "max": 5, "rationale": reasons["G5"] or ["shot durations match target; rhythm fits short-form"]},
    }

    below = [k for k, v in scores.items() if v["score"] < 4]
    summary = {
        "overall": "retry_failed_gates" if below else "good_to_execute",
        "gates_below_4": below,
    }

    return {
        "summary": summary,
        "scores": scores,
        "checks": checks,
        "suggestions": [
            f"retry gate: {gate} — {scores[gate]['rationale']}" for gate in below
        ],
    }


def main() -> int:
    plan = _load_plan(sys.argv)
    report = _score_plan(plan)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
