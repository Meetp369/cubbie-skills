#!/usr/bin/env python3
"""Deterministic Grade Rescue calculator (standard library only).

The calculator never invents course policy. Exact results require verified cutoffs
and a complete inventory of graded + remaining work. Provisional inputs still
produce useful scenarios, but are prominently labeled.
"""
import argparse
import json
import math
import sys

DEFAULT_CUTOFFS = {"A+": 97, "A": 93, "A-": 90, "B+": 87, "B": 83, "B-": 80, "C+": 77, "C": 70, "D": 60}
EPS = 1e-9


def fmt(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _number(value, label, allow_zero=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number.")
    value = float(value)
    if value < 0 or (not allow_zero and value <= 0):
        raise ValueError(f"{label} must be {'non-negative' if allow_zero else 'positive'}.")
    return value


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")
    scheme = data.get("scheme")
    if scheme not in ("weighted", "points"):
        raise ValueError("scheme must be 'weighted' or 'points'.")
    cats = data.get("categories")
    if not isinstance(cats, list) or not cats:
        raise ValueError("categories must be a non-empty list.")
    names = set()
    for i, cat in enumerate(cats, 1):
        if not isinstance(cat, dict):
            raise ValueError(f"Category {i} must be an object.")
        name = str(cat.get("name", "")).strip()
        if not name:
            raise ValueError(f"Category {i} is missing a name.")
        if name.casefold() in names:
            raise ValueError(f"Duplicate category name: {name}.")
        names.add(name.casefold())
        if scheme == "weighted":
            _number(cat.get("weight"), f"{name} weight")
        drop = cat.get("drop_lowest", 0) or 0
        if isinstance(drop, bool) or not isinstance(drop, int) or drop < 0:
            raise ValueError(f"{name} drop_lowest must be a non-negative integer.")
        for j, s in enumerate(cat.get("scores", []), 1):
            if isinstance(s, dict):
                earned, possible = s.get("earned"), s.get("possible")
            elif isinstance(s, (list, tuple)) and len(s) >= 2:
                earned, possible = s[0], s[1]
            else:
                raise ValueError(f"{name} score {j} must contain earned and possible points.")
            if earned is None:
                continue
            e = _number(earned, f"{name} score {j} earned")
            p = _number(possible, f"{name} score {j} possible", allow_zero=False)
            if e > p and not data.get("allow_extra_credit", False):
                raise ValueError(f"{name} score {j} is {fmt(e)}/{fmt(p)}. Set allow_extra_credit=true if this is intentional.")
        read_remaining(cat)  # validates shape and points
    cutoffs = data.get("cutoffs")
    if cutoffs is not None:
        if not isinstance(cutoffs, dict) or not cutoffs:
            raise ValueError("cutoffs must be a non-empty object when provided.")
        for grade, cutoff in cutoffs.items():
            c = _number(cutoff, f"cutoff {grade}")
            if c > 100:
                raise ValueError(f"cutoff {grade} cannot exceed 100%.")


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
    """Return remaining items as (name, points_possible). None means unknown points."""
    rem = cat.get("remaining", 0)
    if rem is None:
        return [(f"{cat['name']} (remaining work)", None)]
    if isinstance(rem, bool):
        raise ValueError(f"{cat['name']} remaining must be points or a list.")
    if isinstance(rem, (int, float)):
        value = _number(rem, f"{cat['name']} remaining")
        return [(f"{cat['name']} (rest)", value)] if value else []
    if not isinstance(rem, list):
        raise ValueError(f"{cat['name']} remaining must be points, null, or a list.")
    items = []
    for i, r in enumerate(rem, 1):
        if isinstance(r, dict):
            name = str(r.get("name") or f"{cat['name']} {i}")
            possible = r.get("possible")
        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            name, possible = str(r[0]), r[1]
        else:
            raise ValueError(f"{cat['name']} remaining item {i} is invalid.")
        if possible is None:
            items.append((name, None))
        else:
            p = _number(possible, f"{name} possible", allow_zero=False)
            items.append((name, p))
    return items


def analyze(data, notes, warnings):
    """Return current, earned contribution A, remaining contribution B, total W, items."""
    points = data["scheme"] == "points"
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
        known_rem = [(n, p) for n, p in rem if p is not None]
        unknown_rem = [(n, p) for n, p in rem if p is None]
        R = sum(p for _, p in known_rem)

        if points:
            if unknown_rem:
                raise ValueError(f"{name} has remaining work with unknown points; a points-based course cannot be calculated exactly until those points are known.")
            if P == 0 and R == 0:
                notes.append(f"{name}: no points known, so it was left out.")
                continue
            A += E; B += R; W += P + R
            cur_num += E; cur_den += P
            items += [(n, p, p) for n, p in known_rem]
            continue

        w = float(cat["weight"])
        W += w
        if unknown_rem:
            if P or R:
                raise ValueError(
                    f"{name} has both completed work and remaining work with unknown points. "
                    "Its final category percentage cannot be determined without the missing point total (or an explicit policy-based assumption)."
                )
            B += w
            for n, _ in unknown_rem:
                items.append((n, None, w / len(unknown_rem)))
            continue

        if P == 0 and R == 0:
            # Explicitly empty category: category is assumed entirely future only when inventory says so.
            if cat.get("status") == "future" or cat.get("all_remaining", False):
                B += w
                items.append((name, None, w))
            else:
                warnings.append(f"{name}: no graded or remaining items were supplied; category status is unknown.")
                B += w
                items.append((f"{name} (unresolved category)", None, w))
            continue

        T = P + R
        A += w * E / T
        B += w * R / T
        if P:
            cur_num += w * E / P; cur_den += w
        items += [(n, p, w * p / T) for n, p in known_rem]

    if W <= EPS:
        raise ValueError("No categories or points found, so there is nothing to calculate from.")
    if cur_den <= EPS:
        notes.append("Nothing is graded yet, so every item counts toward the goal.")
    if not points and abs(W - 100) > 0.01:
        warnings.append(f"Category weights add to {fmt(W)}%, not 100%; results are normalized across the supplied categories.")
    current = 100 * cur_num / cur_den if cur_den else None
    return current, A, B, W, items


def main():
    ap = argparse.ArgumentParser(description="Marks needed on each remaining item.")
    ap.add_argument("input")
    ap.add_argument("--target", help="letter grade to plan for, e.g. A or B+")
    ap.add_argument("--what-if", type=float, help="final grade if the student averages this %% on remaining work")
    args = ap.parse_args()
    if args.target and args.what_if is not None:
        print("ERROR: use either --target or --what-if, not both.")
        sys.exit(2)
    if args.what_if is not None and not 0 <= args.what_if <= 100:
        print("ERROR: --what-if must be between 0 and 100.")
        sys.exit(2)

    notes, warnings = [], []
    try:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
        validate(data)
        current, A, B, W, items = analyze(data, notes, warnings)
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError, IndexError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    cutoffs = data.get("cutoffs")
    cutoff_verified = bool(data.get("cutoffs_verified", cutoffs is not None))
    if not cutoffs:
        cutoffs = DEFAULT_CUTOFFS
        cutoff_verified = False
        warnings.append("Letter cutoffs were not verified; using the fallback plus/minus scale (A+=97, A=93, A-=90, ...).")

    inventory_complete = bool(data.get("inventory_complete", False))
    if not inventory_complete:
        warnings.append("The full-term assignment inventory was not marked complete; future/unpublished work may change the result.")
    rules_verified = bool(data.get("rules_verified", False))
    if data["scheme"] == "weighted" and not rules_verified:
        warnings.append("Weight/drop rules were not marked verified against the syllabus or official course policy.")

    exact = cutoff_verified and inventory_complete and (rules_verified or data["scheme"] == "points") and not warnings
    order = sorted(cutoffs.items(), key=lambda kv: -kv[1])

    def letter(g):
        return next((k for k, v in order if g + EPS >= v), f"below {order[-1][0]}")

    def need(cut):
        if B <= EPS:
            return math.inf
        return 100 * (cut / 100 * W - A) / B

    print(data.get("course", "Course"))
    print(f"Status: {'EXACT' if exact else 'PROVISIONAL'}")
    if current is None:
        print("Current grade: nothing graded yet")
    else:
        print(f"Current grade (graded work only): {fmt(current)}%")

    if B <= EPS:
        final = 100 * A / W
        print(f"Nothing left to grade. Final grade: {fmt(final)}% ({letter(final)})")
    else:
        best = 100 * (A + B) / W
        print(f"Remaining modeled weight: {fmt(100 * B / W)}% of the final grade")
        print(f"Best possible under this model: {fmt(best)}% ({letter(best)})")

        if args.what_if is not None:
            g = 100 * (A + args.what_if / 100 * B) / W
            print(f"If you average {fmt(args.what_if)}% on the modeled remaining work: {fmt(g)}% ({letter(g)})")
        else:
            if args.target:
                match = {k.upper(): k for k in cutoffs}
                key = match.get(args.target.strip().upper())
                if key is None:
                    print(f"ERROR: target '{args.target}' is not on the course grade scale ({', '.join(cutoffs)}).")
                    sys.exit(2)
            else:
                key = next((k for k, v in order if need(v) <= 100 + EPS), order[-1][0])
            cut = cutoffs[key]
            x = need(cut)
            print()
            if x <= EPS:
                print(f"Goal {key} ({fmt(cut)}%+): already secured under this model even with 0 on modeled remaining work.")
            elif x > 100 + EPS:
                print(f"Goal {key} ({fmt(cut)}%+): not reachable under this model (would need {fmt(x)}% average on remaining work).")
                reach = next((k for k, v in order if need(v) <= 100 + EPS), None)
                if reach:
                    print(f"Highest grade still reachable under this model: {reach}.")
            else:
                print(f"Goal {key} ({fmt(cut)}%+): required average across modeled remaining work: {fmt(x)}%")
                print("Equal-percentage target plan (these are NOT separate minimums):")
                for name, possible, share in sorted(items, key=lambda it: -it[2]):
                    weight = fmt(100 * share / W)
                    if possible:
                        marks = math.ceil((x / 100 * possible - EPS) * 2) / 2
                        marks = min(marks, possible)
                        print(f"  - {name}: {fmt(marks)}/{fmt(possible)}  (modeled final-grade share {weight}%)")
                    else:
                        print(f"  - {name}: about {fmt(x)}%  (modeled final-grade share {weight}%)")
                print("Tradeoff: scoring above target on one item can offset scoring below target on another, in proportion to their final-grade impact.")

            print()
            print("Average needed on modeled remaining work, by grade:")
            for k, c in order:
                n = need(c)
                msg = "not reachable" if n > 100 + EPS else ("secured" if n <= EPS else f"{fmt(n)}%")
                print(f"  {k}: {msg}")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"- {w}")
    if notes:
        print("Notes:")
        for n in notes:
            print(f"- {n}")


if __name__ == "__main__":
    main()
