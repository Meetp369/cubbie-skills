#!/usr/bin/env python3
"""Grade Rescue calculator.

Lists every remaining item (exam, project, report, paper...) and the marks the
student needs on each one to reach their target grade.

Usage:
    python3 scripts/grade.py course.json                # plan for the best reachable grade
    python3 scripts/grade.py course.json --target A     # plan for a specific grade
    python3 scripts/grade.py course.json --what-if 85   # grade if you average 85% on what's left

Standard library only.
"""
import argparse
import json
import math
import sys

DEFAULT_CUTOFFS = {"A": 90, "B": 80, "C": 70, "D": 60}


def fmt(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def read_scores(cat):
    scores = []
    for s in cat.get("scores", []):
        if isinstance(s, dict):
            earned, possible = s.get("earned"), s.get("possible")
        else:
            earned, possible = s[0], s[1]
        if earned is None or possible in (None, 0):
            continue
        scores.append((float(earned), float(possible)))
    drop = int(cat.get("drop_lowest", 0) or 0)
    dropped = []
    if drop > 0 and len(scores) > drop:
        ordered = sorted(scores, key=lambda x: x[0] / x[1])
        dropped, scores = ordered[:drop], ordered[drop:]
    return scores, dropped


def read_remaining(cat):
    """Remaining items as a list of (name, points_possible)."""
    rem = cat.get("remaining", 0) or 0
    if isinstance(rem, (int, float)):
        return [(f"{cat['name']} (rest)", float(rem))] if rem else []
    items = []
    for i, r in enumerate(rem, 1):
        if isinstance(r, dict):
            items.append((r.get("name") or f"{cat['name']} {i}", float(r["possible"])))
        else:
            items.append((r[0], float(r[1])))
    return [it for it in items if it[1] > 0]


def analyze(data, notes):
    """Final grade with an average of x (0..1) on remaining work = (A + x*B) / W * 100.

    Returns current, A, B, W and the remaining items as
    (name, points_possible or None, share of the final grade in %-points before scaling).
    """
    points = data.get("scheme") == "points"
    A = B = W = 0.0
    cur_num = cur_den = 0.0
    items = []

    for cat in data["categories"]:
        name = cat["name"]
        scores, dropped = read_scores(cat)
        if dropped:
            notes.append(f"Dropped lowest {name} score ({', '.join(f'{fmt(e)}/{fmt(p)}' for e, p in dropped)}).")
        E = sum(e for e, _ in scores)
        P = sum(p for _, p in scores)
        rem = read_remaining(cat)
        R = sum(p for _, p in rem)

        if points:
            if P == 0 and R == 0:
                notes.append(f"{name}: no points known yet, so it was left out.")
                continue
            A += E
            B += R
            W += P + R
            cur_num += E
            cur_den += P
            items += [(n, p, p) for n, p in rem]
            continue

        w = float(cat["weight"])
        W += w
        if P == 0 and R == 0:
            B += w
            items.append((name, None, w))
        else:
            T = P + R
            A += w * E / T
            B += w * R / T
            if P:
                cur_num += w * E / P
                cur_den += w
            items += [(n, p, w * p / T) for n, p in rem]

    if cur_den == 0:
        raise ValueError("No graded work yet, so there is nothing to calculate from.")
    if not points and abs(W - 100) > 0.01:
        notes.append(f"Weights add up to {fmt(W)}%, not 100%; scaled to 100%.")
    return 100 * cur_num / cur_den, A, B, W, items


def main():
    ap = argparse.ArgumentParser(description="Marks needed on each remaining item.")
    ap.add_argument("input")
    ap.add_argument("--target", help="letter grade to plan for, e.g. A or B+")
    ap.add_argument("--what-if", type=float, help="final grade if the student averages this %% on remaining work")
    args = ap.parse_args()

    notes = []
    try:
        with open(args.input) as f:
            data = json.load(f)
        current, A, B, W, items = analyze(data, notes)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    cutoffs = data.get("cutoffs")
    if not cutoffs:
        cutoffs = DEFAULT_CUTOFFS
        notes.append("Letter cutoffs not given; used 90/80/70/60. Check the syllabus.")
    order = sorted(cutoffs.items(), key=lambda kv: -kv[1])

    def letter(g):
        return next((k for k, v in order if g >= v), f"below {order[-1][0]}")

    def need(cut):
        return 100 * (cut / 100 * W - A) / B

    print(data.get("course", "Course"))
    print(f"Current grade (graded work only): {fmt(current)}%")

    if B == 0:
        final = 100 * A / W
        print(f"Nothing left to grade. Final grade: {fmt(final)}% ({letter(final)})")
        return

    best = 100 * (A + B) / W
    print(f"Still to come: {fmt(100 * B / W)}% of your grade")
    print(f"Best possible (full marks on everything left): {fmt(best)}% ({letter(best)})")

    if args.what_if is not None:
        g = 100 * (A + args.what_if / 100 * B) / W
        print(f"If you score {fmt(args.what_if)}% on everything left: {fmt(g)}% ({letter(g)})")
    else:
        # pick the target: the one asked for, or the best reachable grade
        if args.target:
            match = {k.upper(): k for k in cutoffs}
            key = match.get(args.target.strip().upper())
            if key is None:
                key = order[0][0]
                notes.append(f"'{args.target}' is not on the grade scale; planned for {key}, the highest grade.")
        else:
            key = next((k for k, v in order if need(v) <= 100), order[-1][0])
        cut = cutoffs[key]
        x = need(cut)

        print()
        if x <= 0:
            print(f"Goal {key} ({fmt(cut)}%+): already locked in ✅ even with 0 on what's left.")
        elif x > 100:
            print(f"Goal {key} ({fmt(cut)}%+): not reachable (would need {fmt(x)}% on everything left).")
            reach = next((k for k, v in order if need(v) <= 100), None)
            if reach:
                print(f"Highest grade still reachable: {reach}.")
        else:
            print(f"Goal {key} ({fmt(cut)}%+): score at least {fmt(x)}% on each remaining item:")
            for name, possible, share in sorted(items, key=lambda it: -it[2]):
                weight = fmt(100 * share / W)
                if possible:
                    marks = math.ceil(x / 100 * possible * 2) / 2  # round up to the nearest half mark
                    print(f"  - {name}: {fmt(marks)}/{fmt(possible)}  (worth {weight}% of your grade)")
                else:
                    print(f"  - {name}: {fmt(x)}%  (worth {weight}% of your grade)")
            print("Doing better on a bigger item lets you score lower on a smaller one.")

        print()
        print("Average needed on everything left, by grade:")
        for k, c in order:
            n = need(c)
            msg = "not reachable" if n > 100 else ("locked in ✅" if n <= 0 else f"{fmt(n)}%")
            print(f"  {k}: {msg}")

    if notes:
        print("Notes:")
        for n in notes:
            print(f"- {n}")


if __name__ == "__main__":
    main()
