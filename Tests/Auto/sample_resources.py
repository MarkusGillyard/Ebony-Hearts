"""Samples GPU memory/utilisation (nvidia-smi) and the game process's resident memory once a second while a packaged
run is active, for the performance and soak reports.

Usage: python3 sample_resources.py <out.csv> [process-name]   (default process: EbonyHearts-Linux-Shipping)
Waits up to 4 minutes for the process, then samples until it exits. The first line records the GPU memory in use
before the game started, so the game's own share can be estimated.
"""
import os
import subprocess
import sys
import time


def gpu():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,clocks.gr,temperature.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip()
    return [v.strip() for v in out.split(",")] if out else ["", "", "", "", ""]


def find_pid(name):
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/comm") as f:
                    if f.read().strip() == name[:15]:
                        return int(pid)
            except OSError:
                pass
    return None


def rss_mb(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        return None
    return None


def main():
    out, name = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "EbonyHearts-Linux-Shipping")
    with open(out, "w") as f:
        f.write("t_s,vram_used_mib,vram_total_mib,gpu_util_pct,gpu_clock_mhz,gpu_temp_c,game_rss_mib\n")
        base = gpu()
        f.write(f"baseline,{base[0]},{base[1]},{base[2]},{base[3]},{base[4]},\n")
        deadline = time.time() + 240
        pid = None
        while pid is None and time.time() < deadline:
            pid = find_pid(name)
            time.sleep(0.5)
        if pid is None:
            raise SystemExit("game process not found")
        t0 = time.time()
        while True:
            rss = rss_mb(pid)
            if rss is None:
                break
            g = gpu()
            f.write(f"{time.time() - t0:.1f},{g[0]},{g[1]},{g[2]},{g[3]},{g[4]},{rss:.1f}\n")
            f.flush()
            time.sleep(1.0)
    print(f"sampled until exit -> {out}")


main()
