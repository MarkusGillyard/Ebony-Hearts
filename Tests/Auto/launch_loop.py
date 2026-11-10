"""Start-and-quit loop for a packaged build: one launch at a time, each attempt recorded and classified.

Usage:
  python3 launch_loop.py --launcher <EbonyHearts.sh> --runs N --out <dir> [--script <auto script>]
                         [--timeout S] [--gap S] [--fresh-profile] [--stop-on-fail] [--label TEXT] -- [game args...]

Every attempt gets its own folder (attempt-0001, ...) with the game's stdout/stderr and its automation log, and one
JSON line in attempts.jsonl: start time, arguments, PID, exit status or signal, duration, the audio sink and monitors
in use, and an outcome:

  clean       exit 0, the script reached "quit", no FAIL/WARN line, platform_check ok when the script runs it
  crash       killed by a signal (the launcher reports 128+N) or the engine's crash handler ran
  timeout     still running after --timeout seconds; the process group was killed
  silent      exit 0 but the game never wrote its automation log (it did not get to the game)
  audio_fail  platform_check reported the game's audio output inactive
  fail        exit 0 with FAIL/WARN lines or without the quit marker
  nonzero     any other exit status

Before each launch the loop waits for any earlier game process to leave and aborts if one remains; after
each exit it checks only its own process group for leftover game processes (orphans). --fresh-profile renames the game's saved profile aside
before every attempt (nothing is deleted), so each launch is a first run. summary.json holds the counts.
"""
import argparse
import datetime
import json
import os
import signal
import subprocess
import sys
import time

GAME_PROCESS_NAMES = ("EbonyHearts-Lin", "EbonyHearts")  # /proc/<pid>/comm is cut to 15 characters
CRASH_MARKERS = ("Signal 11 caught", "CommonUnixCrashHandler", "Unhandled Exception: SIG")


def game_pids():
    pids = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/comm") as f:
                if f.read().strip() in GAME_PROCESS_NAMES:
                    pids.append(int(entry))
        except OSError:
            pass
    return pids


def game_pids_in_group(pgid):
    result = []
    for pid in game_pids():
        try:
            if os.getpgid(pid) == pgid:
                result.append(pid)
        except OSError:
            pass
    return result


def wait_no_game(seconds, pgid=None):
    remaining = game_pids if pgid is None else lambda: game_pids_in_group(pgid)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not remaining():
            return []
        time.sleep(0.2)
    return remaining()


def quiet(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def device_state():
    monitors = quiet(["xrandr", "--listactivemonitors"]).splitlines()[1:]
    return {"sink": quiet(["pactl", "get-default-sink"]), "monitors": [m.strip() for m in monitors]}


def move_profile_aside(tag):
    profile = os.path.join(os.path.expanduser("~"), ".config", "Epic", "EbonyHearts")
    if not os.path.isdir(profile) or os.path.islink(profile):
        return None
    target = f"{profile}.pre-{tag}"
    n = 0
    while os.path.exists(target):
        n += 1
        target = f"{profile}.pre-{tag}-{n}"
    os.rename(profile, target)
    return target


def classify(rc, timed_out, stdout_text, auto_text, wants_platform_check):
    if timed_out:
        return "timeout"
    if rc < 0 or rc > 128 or any(m in stdout_text for m in CRASH_MARKERS):
        return "crash"
    if rc != 0:
        return "nonzero"
    if not auto_text:
        return "silent"
    lines = auto_text.splitlines()
    if wants_platform_check:
        check = [l for l in lines if " platform_check " in l]
        if check and " audio_output=0" in check[-1]:
            return "audio_fail"
        if not check:
            return "fail"
    if any(" FAIL " in l or " WARN " in l or "] FAIL" in l or "] WARN" in l for l in lines):
        return "fail"
    if not any("quit after" in l for l in lines):
        return "fail"
    return "clean"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--launcher", required=True)
    ap.add_argument("--runs", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--script", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_quit.txt"))
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--gap", type=float, default=2.0)
    ap.add_argument("--fresh-profile", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("game_args", nargs="*")
    a = ap.parse_args()

    launcher = os.path.abspath(a.launcher)
    script = os.path.abspath(a.script)
    with open(script) as f:
        wants_platform_check = any(l.strip() == "platform_check" for l in f)
    os.makedirs(a.out, exist_ok=True)
    if os.listdir(a.out):
        sys.exit(f"output folder is not empty: {a.out}")
    jsonl = None
    counts = {}
    started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    for i in range(1, a.runs + 1):
        aid = f"attempt-{i:04d}"
        ev = os.path.join(a.out, aid)
        overlap = wait_no_game(15.0)
        if overlap:
            if jsonl is not None:
                jsonl.close()
            sys.exit(f"another game process is still running; refusing to launch or clean it up: {overlap}")
        os.makedirs(ev)
        if jsonl is None:
            jsonl = open(os.path.join(a.out, "attempts.jsonl"), "a")
        profile_moved = move_profile_aside(f"{os.path.basename(os.path.normpath(a.out))}-{aid}") if a.fresh_profile else None
        args = [launcher, f"-EHAuto={script}", f"-EHEvidence={ev}", *a.game_args]
        rec = {"id": aid, "label": a.label, "start": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
               "args": args[1:], "device": device_state(), "overlap_pids": overlap, "profile_moved_to": profile_moved}
        t0 = time.monotonic()
        with open(os.path.join(ev, "stdout.log"), "w") as out:
            proc = subprocess.Popen(args, stdout=out, stderr=subprocess.STDOUT, cwd=os.path.dirname(launcher), start_new_session=True)
            rec["pid"] = proc.pid
            timed_out = False
            try:
                rc = proc.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(proc.pid, sig)
                    except ProcessLookupError:
                        break
                    try:
                        proc.wait(timeout=10)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                rc = proc.returncode if proc.returncode is not None else -9
        rec["duration_s"] = round(time.monotonic() - t0, 3)
        rec["exit"] = rc
        rec["signal"] = -rc if rc < 0 else (rc - 128 if rc > 128 else 0)
        rec["timed_out"] = timed_out
        orphans = wait_no_game(10.0, pgid=proc.pid)
        rec["orphan_pids"] = orphans
        for pid in orphans:
            try:
                if os.getpgid(pid) == proc.pid:
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        with open(os.path.join(ev, "stdout.log"), errors="replace") as f:
            stdout_text = f.read()
        auto_path = os.path.join(ev, "auto_log.txt")
        auto_text = open(auto_path, errors="replace").read() if os.path.exists(auto_path) else ""
        outcome = classify(rc, timed_out, stdout_text, auto_text, wants_platform_check)
        if orphans and outcome == "clean":
            outcome = "fail"
        rec["outcome"] = outcome
        check = [l for l in auto_text.splitlines() if " platform_check " in l]
        rec["platform_check"] = check[-1].split("] ", 1)[-1] if check else None
        jsonl.write(json.dumps(rec) + "\n")
        jsonl.flush()
        counts[outcome] = counts.get(outcome, 0) + 1
        print(f"{aid} {outcome} exit={rc} {rec['duration_s']}s", flush=True)
        if outcome != "clean" and a.stop_on_fail:
            break
        time.sleep(a.gap)
    if jsonl is not None:
        jsonl.close()
    summary = {"label": a.label, "launcher": launcher, "script": script, "game_args": a.game_args, "runs": sum(counts.values()),
               "counts": counts, "started": started, "finished": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary))
    return 0 if counts.get("clean", 0) == summary["runs"] else 1


if __name__ == "__main__":
    sys.exit(main())
