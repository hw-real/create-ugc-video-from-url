#!/usr/bin/env python3
"""validate_plan.py — validate a UGC video execution plan (steps_json) before
calling run_paid_execution.

Checks, against the ugcmaker agent V3 contract:
  - step shape (id/tool/name/args/depends_on), unique ids
  - tool must be a known paid tool
  - per-tool args: enums, required fields, numeric ranges
  - dependency graph: referenced ids exist, no cycles
  - @step_id placeholders must be backed by a depends_on edge
  - prompt rules: non-empty, no media URLs inside prompt text, no placeholder URLs
  - media URL caps: i2v image_urls <= 8, v2v video_urls <= 3, merge 2-8

Usage:
    python3 validate_plan.py <plan.json>        # read from file
    python3 validate_plan.py -                   # read from stdin
    python3 validate_plan.py --json '[...]'      # inline JSON

Exit code: 0 if valid (warnings ok), 1 if errors.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

EXIT_OK = 0
EXIT_ERR = 1

PAID_TOOLS = {
    "generate_image_tool",
    "generate_video_tool",
    "merge_videos_tool",
    "edit_image_tool",
}

IMAGE_RESOLUTIONS = {"1k", "2k", "4k"}
IMAGE_QUALITIES = {"low", "medium", "high"}
VIDEO_RESOLUTIONS = {"480p", "720p", "1080p", "4k"}
ASPECT_RATIOS = {"1:1", "9:16", "16:9", "3:4", "4:3"}
IMAGE_SCENE_TYPES = {None, 2, 6, 11, 13, 4, 5}
VIDEO_SCENE_TYPES = {None, 1, 2, 3, 5}
EDIT_SCENE_TYPES = {1, 3, 7, 8, 9, 10}

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(
    r"(https?://(example\.com|your-|placeholder\.|<.*>)|[A-Za-z0-9._-]+\.com/your)", re.IGNORECASE
)
STEP_REF_RE = re.compile(r"^@([A-Za-z0-9_-]+)$")
MIN_VIDEO_DURATION = 3
MAX_VIDEO_DURATION = 60


def load_plan(argv: list[str]) -> list[dict]:
    """Load and parse the steps array from file, stdin, or --json."""
    args = argv[1:]
    if not args:
        print(json.dumps({
            "valid": False,
            "errors": ["no input: pass <plan.json>, '-' for stdin, or --json '<steps>'"],
            "warnings": [],
        }, ensure_ascii=False, indent=2))
        sys.exit(EXIT_ERR)

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
        print(json.dumps({
            "valid": False,
            "errors": [f"invalid JSON: {exc}"],
            "warnings": [],
        }, ensure_ascii=False, indent=2))
        sys.exit(EXIT_ERR)

    if isinstance(data, dict) and "steps" in data:
        data = data["steps"]
    if not isinstance(data, list):
        return fail("plan root must be a JSON array of steps (or {\"steps\": [...]})")
    return data


def fail(msg: str) -> None:
    print(json.dumps({"valid": False, "errors": [msg], "warnings": []},
                     ensure_ascii=False, indent=2))
    sys.exit(EXIT_ERR)


def is_valid_url(value: Any, *, allow_step_ref: bool = True) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    value = value.strip()
    if allow_step_ref and STEP_REF_RE.match(value):
        return True
    if not value.startswith(("http://", "https://")):
        return False
    if PLACEHOLDER_RE.search(value):
        return False
    return True


def check_media_list(
    value: Any,
    *,
    field: str,
    max_items: int | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"args.{field} must be a list, got {type(value).__name__}")
        return
    if max_items is not None and len(value) > max_items:
        errors.append(f"args.{field} exceeds max {max_items} items ({len(value)} given)")
    for i, item in enumerate(value):
        if not is_valid_url(item):
            errors.append(f"args.{field}[{i}] is not a valid URL or @step_id reference: {item!r}")


def check_prompt(value: Any, *, field: str, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"args.{field} must be a non-empty string")
        return
    urls = URL_RE.findall(value)
    if urls:
        errors.append(
            f"args.{field} contains media URLs inside the prompt text: {urls[:3]} — "
            "move URLs to args.image_urls/video_urls"
        )
    if PLACEHOLDER_RE.search(value):
        errors.append(f"args.{field} contains a placeholder URL (example.com / your-...)")


def check_dependencies(steps: list[dict], errors: list[str], warnings: list[str]) -> None:
    ids = [s.get("id") for s in steps]
    seen: set[str] = set()
    for step in steps:
        sid = step.get("id")
        if not isinstance(sid, str) or not sid:
            errors.append(f"step missing string 'id': {step.get('name', '?')!r}")
            continue
        if sid in seen:
            errors.append(f"duplicate step id: {sid!r}")
        seen.add(sid)

    ids_set = {s.get("id") for s in steps}
    for step in steps:
        sid = step.get("id")
        deps = step.get("depends_on", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            errors.append(f"step {sid!r}: depends_on must be a list")
            continue
        for dep in deps:
            if dep not in ids_set:
                errors.append(f"step {sid!r}: depends_on references unknown step {dep!r}")

        # @step_id placeholders in args must be covered by depends_on
        args = step.get("args") or {}
        for key, value in args.items():
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, str):
                    m = STEP_REF_RE.match(item.strip())
                    if m and m.group(1) not in deps:
                        errors.append(
                            f"step {sid!r}: args.{key} references @{m.group(1)} but "
                            f"depends_on does not include {m.group(1)!r}"
                        )

    # cycle detection (DFS on dependency edges)
    graph = {s.get("id"): s.get("depends_on") or [] for s in steps if s.get("id")}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {k: WHITE for k in graph}

    def visit(node: str) -> bool:
        color[node] = GRAY
        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            if color[dep] == GRAY:
                return True  # cycle
            if color[dep] == WHITE and visit(dep):
                return True
        color[node] = BLACK
        return False

    for node in graph:
        if color[node] == WHITE and visit(node):
            errors.append(f"dependency cycle detected involving step {node!r}")
            break


def validate_step(step: dict, errors: list[str], warnings: list[str]) -> None:
    sid = step.get("id", "?")
    tool = step.get("tool")
    if tool not in PAID_TOOLS:
        errors.append(
            f"step {sid!r}: unknown tool {tool!r} (allowed: {sorted(PAID_TOOLS)})"
        )
        return
    if not isinstance(step.get("name"), str) or not step["name"].strip():
        errors.append(f"step {sid!r}: missing human-readable 'name'")
    args = step.get("args")
    if not isinstance(args, dict):
        errors.append(f"step {sid!r}: args must be an object")
        return

    if tool == "generate_image_tool":
        prompts = args.get("prompts")
        if not isinstance(prompts, list) or not prompts:
            errors.append(f"step {sid!r}: args.prompts must be a non-empty list")
        else:
            for i, p in enumerate(prompts):
                check_prompt(p, field=f"prompts[{i}]", errors=errors, warnings=warnings)
        if "resolution" in args and args["resolution"] not in IMAGE_RESOLUTIONS:
            errors.append(f"step {sid!r}: resolution {args['resolution']!r} not in {sorted(IMAGE_RESOLUTIONS)}")
        if "quality" in args and args["quality"] not in IMAGE_QUALITIES:
            errors.append(f"step {sid!r}: quality {args['quality']!r} not in {sorted(IMAGE_QUALITIES)}")
        if "aspect_ratio" in args and args["aspect_ratio"] not in ASPECT_RATIOS:
            errors.append(f"step {sid!r}: aspect_ratio {args['aspect_ratio']!r} not in {sorted(ASPECT_RATIOS)}")
        if "scene_type" in args and args["scene_type"] not in IMAGE_SCENE_TYPES:
            errors.append(f"step {sid!r}: image scene_type {args['scene_type']!r} unsupported")
        check_media_list(args.get("image_urls"), field="image_urls", max_items=None,
                         errors=errors, warnings=warnings)
        num = args.get("num")
        if num is not None and (not isinstance(num, int) or num < 1):
            errors.append(f"step {sid!r}: args.num must be a positive int")

    elif tool == "generate_video_tool":
        check_prompt(args.get("prompt"), field="prompt", errors=errors, warnings=warnings)
        dur = args.get("duration")
        if dur is not None:
            if not isinstance(dur, (int, float)) or isinstance(dur, bool):
                errors.append(f"step {sid!r}: duration must be a number, got {dur!r}")
            elif not (MIN_VIDEO_DURATION <= dur <= MAX_VIDEO_DURATION):
                errors.append(
                    f"step {sid!r}: duration {dur} out of range "
                    f"[{MIN_VIDEO_DURATION}, {MAX_VIDEO_DURATION}]"
                )
        if "resolution" in args and args["resolution"] not in VIDEO_RESOLUTIONS:
            errors.append(f"step {sid!r}: resolution {args['resolution']!r} not in {sorted(VIDEO_RESOLUTIONS)}")
        if "aspect_ratio" in args and args["aspect_ratio"] not in ASPECT_RATIOS:
            errors.append(f"step {sid!r}: aspect_ratio {args['aspect_ratio']!r} not in {sorted(ASPECT_RATIOS)}")
        if "scene_type" in args and args["scene_type"] not in VIDEO_SCENE_TYPES:
            errors.append(f"step {sid!r}: video scene_type {args['scene_type']!r} unsupported")
        check_media_list(args.get("image_urls"), field="image_urls", max_items=8,
                         errors=errors, warnings=warnings)
        check_media_list(args.get("video_urls"), field="video_urls", max_items=3,
                         errors=errors, warnings=warnings)
        if args.get("prompt") and isinstance(args.get("prompt"), str) and len(args["prompt"].strip()) < 20:
            warnings.append(f"step {sid!r}: prompt looks generic/too short — re-draft via draft_video_prompt")

    elif tool == "merge_videos_tool":
        urls = args.get("video_urls")
        if not isinstance(urls, list) or not (2 <= len(urls) <= 8):
            errors.append(f"step {sid!r}: merge_videos_tool requires video_urls with 2-8 items")
        check_media_list(urls, field="video_urls", max_items=8, errors=errors, warnings=warnings)

    elif tool == "edit_image_tool":
        st = args.get("scene_type")
        if st not in EDIT_SCENE_TYPES:
            errors.append(f"step {sid!r}: edit_image_tool scene_type {st!r} not in {sorted(EDIT_SCENE_TYPES)}")
        check_media_list(args.get("image_urls"), field="image_urls", max_items=None,
                         errors=errors, warnings=warnings)
        if "image_url" in args and not is_valid_url(args["image_url"]):
            errors.append(f"step {sid!r}: args.image_url is not a valid URL")


def main() -> int:
    steps = load_plan(sys.argv)
    if steps is None:
        return EXIT_ERR

    errors: list[str] = []
    warnings: list[str] = []

    for step in steps:
        if not isinstance(step, dict):
            errors.append(f"step is not an object: {step!r}")
            continue
        validate_step(step, errors, warnings)

    check_dependencies([s for s in steps if isinstance(s, dict)], errors, warnings)

    tools_used: dict[str, int] = {}
    for s in steps:
        if isinstance(s, dict):
            tools_used[s.get("tool", "?")] = tools_used.get(s.get("tool", "?"), 0) + 1

    report = {
        "valid": not errors,
        "steps": len(steps),
        "tools": tools_used,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return EXIT_OK if not errors else EXIT_ERR


if __name__ == "__main__":
    sys.exit(main())
