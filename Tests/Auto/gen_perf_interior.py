"""Generates Tests/Auto/fp_perf_interior.txt (python3 Tests/Auto/gen_perf_interior.py Tests/Auto/fp_perf_interior.txt): one route through the interior's rooms, played twice (warm-up, capture)."""
import sys
def turn(n, d):  # n steps of 10 degrees (125 counts at 0.08 deg/count); d = +1 left... sign as the yaw changes
    return ["loop %d" % n, "look %d 0" % (125 * d), "wait 0.05", "endloop"]
def walk(key, s):
    return ["hold kbA %s" % key, "wait %.2f" % s, "release kbA %s" % key]
def spin():
    return turn(36, 1)
R = []
R += ["log route: the Threshold Hall, up the stair to the loft and out onto the balcony", "fp_reset", "wait 0.5"]
R += turn(18, 1) + walk("FPForward", 2.40) + ["fp_state hall"] + spin()
R += turn(9, 1) + walk("FPForward", 1.05) + turn(9, 1) + walk("FPForward", 2.8) + ["fp_state loft"] + spin()
R += turn(9, 1) + walk("FPForward", 1.0) + turn(9, -1) + walk("FPForward", 1.0) + ["fp_state balcony"]
R += turn(18, 1) + turn(36, -1) + turn(18, 1)
R += ["log route: the forge", "fp_reset", "wait 0.5"]
R += turn(9, -1) + walk("FPForward", 2.33) + turn(9, 1) + walk("FPForward", 2.25) + turn(9, -1) + walk("FPForward", 2.6) + ["fp_state forge"] + spin()
R += turn(18, 1) + walk("FPForward", 1.2)
R += ["log route: the Hall of the Six", "fp_reset", "wait 0.5"]
R += turn(9, 1) + walk("FPForward", 2.33) + turn(9, -1) + walk("FPForward", 2.25) + turn(9, 1) + walk("FPForward", 2.6) + ["fp_state hall_of_six"] + spin()
R += ["log route: the way down into the undercroft", "fp_reset", "wait 0.5"]
R += turn(9, -1) + walk("FPForward", 2.33) + turn(9, 1) + walk("FPForward", 5.5) + ["fp_state way_down"] + turn(9, -1) + walk("FPForward", 0.25) + turn(9, 1) + walk("FPForward", 4.2) + ["fp_state crypt"] + spin()
R += walk("FPForward", 1.5) + turn(9, 1) + walk("FPForward", 1.0) + spin()
L = ["# Warm frame-time capture through the Chapel interior's rooms (all builds: device inputs only, so it runs in",
     "# Shipping): the Threshold Hall, the stair, the loft and its balcony, both transepts, the way down and the crypt.",
     "# The route is played once to warm caches, then captured. fp_state lines record where each stop ended.",
     "wait 6", "log warm-up pass"] + R + ["log captured pass", "perf_begin"] + R + ["perf_end fp_interior", "fp_state end", "mem end", "quit"]
open(sys.argv[1], "w").write("\n".join(L) + "\n")
print(len(L))
