"""Records gameplay footage of a running game window with GStreamer (X11 window capture, H.264 MP4), and optionally
extracts still frames for frame-by-frame review.

Usage:
  python3 capture.py record <window title> <out.mp4> <seconds> [--delay S] [--fps N]
  python3 capture.py frames <in.mp4> <out-dir> <fps>
Capture reads the window's pixels only; it sends no input. Recording costs CPU, so never record during a perf run.
"""
import os
import subprocess
import sys
import time


def find_window(name, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.split(None, 3)[-1].strip() == name:
                return int(line.split()[0], 16)
        time.sleep(1)
    raise SystemExit("game window not found")


def record(name, out, seconds, delay, fps):
    xid = find_window(name, 240)
    time.sleep(delay)
    frames = int(seconds * fps)
    cmd = ["gst-launch-1.0", "-q", "-e", "ximagesrc", f"xid={xid}", "use-damage=false", f"num-buffers={frames}", "!",
           f"video/x-raw,framerate={fps}/1", "!", "videoconvert", "!", "video/x-raw,format=I420", "!",
           "x264enc", "speed-preset=veryfast", "tune=zerolatency", "bitrate=12000", "key-int-max=60", "!",
           "mp4mux", "!", "filesink", f"location={out}"]
    rc = subprocess.run(cmd).returncode
    print(f"recorded {out} ({frames} frames at {fps} fps) rc={rc}")
    return rc


def extract(src, outdir, fps):
    os.makedirs(outdir, exist_ok=True)
    cmd = ["gst-launch-1.0", "-q", "filesrc", f"location={src}", "!", "qtdemux", "!", "decodebin", "!", "videorate", "!",
           f"video/x-raw,framerate={fps}/1", "!", "videoconvert", "!", "pngenc", "!", "multifilesink",
           f"location={os.path.join(outdir, 'f_%04d.png')}"]
    return subprocess.run(cmd).returncode


def main():
    mode = sys.argv[1]
    if mode == "record":
        args = sys.argv[2:]
        delay = float(args[args.index("--delay") + 1]) if "--delay" in args else 0.0
        fps = int(args[args.index("--fps") + 1]) if "--fps" in args else 30
        sys.exit(record(args[0], args[1], float(args[2]), delay, fps))
    elif mode == "frames":
        sys.exit(extract(sys.argv[2], sys.argv[3], int(sys.argv[4])))
    raise SystemExit(__doc__)


main()
