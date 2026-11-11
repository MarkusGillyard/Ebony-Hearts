"""Verify a complete run_battery_1108.sh battery from its log and evidence.

Usage: python3 Tests/Auto/verify_battery.py --log battery.log --evidence battery/
This checks completion and evidence integrity, not gameplay quality or performance targets.
"""

import argparse
import json
import math
import re
from pathlib import Path


SCENARIOS = (
    "perf-cold", "smoke", "controls-selftest", "controls-remap",
    "controls-persist", "controls-ui", "settings-video-audio", "journey",
    "lesson", "xinput", "vpad-layout-xbox", "vpad-layout-ds4",
    "vpad-menu-and-fight", "vpad-disconnect", "vpad-remap", "matrix",
    "review-match", "review-reactions", "review-flow", "review-playtest",
    "signature", "review-combat", "review-jump", "art",
    "perf-1080-vsync", "perf-1080-novsync", "perf-aura", "perf-default",
)
PAD = {
    "vpad-layout-xbox": ("layout", "xbox"),
    "vpad-layout-ds4": ("layout", "ds4"),
    "vpad-menu-and-fight": ("menu-and-fight", "xbox"),
    "vpad-disconnect": ("disconnect", "xbox"),
    "vpad-remap": ("remap", "xbox"),
}
PERF = {
    "perf-cold": ("perf_cold_first_match_25s",),
    "smoke": ("perf_smoke",),
    "perf-1080-vsync": ("perf_fight_60s", "perf_menu_20s"),
    "perf-1080-novsync": ("perf_fight_60s", "perf_menu_20s"),
    "perf-aura": (
        "perf_training_no_aura_10s", "perf_training_aura_7s",
        "perf_training_aura2_7s",
    ),
    "perf-default": ("perf_fight_60s", "perf_menu_20s"),
}
RUN_LINE = re.compile(r"^\d\d:\d\d:\d\d ([a-z][\w-]*) rc=(\d+)(?:\s|$)", re.M)
BAD_LINE = re.compile(r"\b(?:FAIL|WARN|STUCK)\b")
QUIT = re.compile(r"\bquit after \d+ matches")
MATCH_END = re.compile(r"\bmatch_end\b")


def read(path, errors):
    try:
        data = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"missing or unreadable {path}: {exc}")
        return ""
    if not data.strip():
        errors.append(f"empty {path}")
    return data


def verify(log_path, evidence):
    errors = []
    log = read(log_path, errors)
    starts = re.findall(r"^\d\d:\d\d:\d\d battery start .+$", log, re.M)
    ends = re.findall(r"^\d\d:\d\d:\d\d battery done\s*$", log, re.M)
    if len(starts) != 1 or len(ends) != 1:
        errors.append(f"battery start/done markers: {len(starts)}/{len(ends)} (need 1/1)")
    if BAD_LINE.search(log):
        errors.append("battery log contains FAIL/WARN/STUCK")
    runs = RUN_LINE.findall(log)
    if tuple(name for name, _ in runs) != SCENARIOS:
        errors.append("scenario names/order/count differ from complete 1108 battery")
        errors.append("observed: " + ", ".join(name for name, _ in runs))
    for name, rc in runs:
        if rc != "0":
            errors.append(f"{name}: package rc={rc}")
    if not evidence.is_dir():
        errors.append(f"missing evidence directory: {evidence}")
        return errors

    for name in SCENARIOS:
        directory = evidence / name
        if not directory.is_dir():
            errors.append(f"{name}: missing evidence directory")
            continue
        if name == "xinput":
            driver = read(directory / "driver.out", errors)
            if "sent quit" not in driver or "window " not in driver:
                errors.append("xinput: driver did not record window and sent quit")
            for shot in ("x01_title", "x02_main", "x03_fight", "x04_after_inputs", "x05_pause", "x06_quit_confirm"):
                path = directory / f"{shot}.png"
                if not path.is_file() or path.stat().st_size == 0:
                    errors.append(f"xinput: missing or empty {path.name}")
            if BAD_LINE.search(driver) or "Traceback" in driver:
                errors.append("xinput: driver contains FAIL/WARN/STUCK/Traceback")
            continue

        auto = read(directory / "auto_log.txt", errors)
        if BAD_LINE.search(auto):
            errors.append(f"{name}: auto log contains FAIL/WARN/STUCK")
        if name in ("journey", "vpad-menu-and-fight", "vpad-disconnect"):
            if "quit requested" not in auto:
                errors.append(f"{name}: missing quit requested completion")
        elif not QUIT.search(auto):
            errors.append(f"{name}: missing quit after completion")

        if name in PAD:
            scenario, kind = PAD[name]
            pad = read(directory / "pad.out", errors)
            if f"virtual pad scenario done: {scenario} ({kind})" not in pad:
                errors.append(f"{name}: virtual pad driver did not complete")
            if BAD_LINE.search(pad) or "Traceback" in pad:
                errors.append(f"{name}: pad driver contains FAIL/WARN/STUCK/Traceback")
        if name == "matrix":
            matches = len(MATCH_END.findall(auto))
            if matches != 12 or "quit after 12 matches" not in auto or "mem matrix_end" not in auto:
                errors.append(f"matrix: incomplete 12-match run ({matches} match_end markers)")
        if name == "lesson":
            if not re.search(r'ok lesson_status step=1/14 "Movement"', auto):
                errors.append("lesson: missing step 1 status")
            for step in range(2, 15):
                if not re.search(rf"\bok wait_lesson {step}\b", auto):
                    errors.append(f"lesson: missing successful wait for step {step}")
            if not re.search(r'ok lesson_status step=14/14 "Lesson complete"', auto):
                errors.append("lesson: missing step 14 completion status")
        for perf_name in PERF.get(name, ()):
            if not re.search(rf"\bperf_end {re.escape(perf_name)}\b", auto):
                errors.append(f"{name}: missing perf_end {perf_name}")
            path = directory / f"{perf_name}.json"
            try:
                metrics = json.loads(path.read_text(encoding="utf-8"))
                frames = metrics.get("frames")
                seconds = metrics.get("seconds")
                if (metrics.get("name") != perf_name or
                        isinstance(frames, bool) or
                        not isinstance(frames, (int, float)) or
                        not math.isfinite(frames) or frames <= 0 or
                        isinstance(seconds, bool) or
                        not isinstance(seconds, (int, float)) or
                        not math.isfinite(seconds) or seconds <= 0):
                    errors.append(f"{name}: invalid perf metrics in {path.name}")
            except (OSError, UnicodeError, ValueError, AttributeError) as exc:
                errors.append(f"{name}: missing or invalid {path.name}: {exc}")
        if name in ("review-combat", "review-jump"):
            capture = read(directory / "capture.out", errors)
            movie = directory / f"{name}.mp4"
            if "recorded " not in capture or "rc=0" not in capture:
                errors.append(f"{name}: capture did not report success")
            if not movie.is_file() or movie.stat().st_size == 0:
                errors.append(f"{name}: missing or empty capture video")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    errors = verify(args.log, args.evidence)
    for error in errors:
        print("FAIL:", error)
    if errors:
        raise SystemExit(1)
    print(f"PASS: {len(SCENARIOS)} scenario exits, completion markers, and evidence files")


if __name__ == "__main__":
    main()
