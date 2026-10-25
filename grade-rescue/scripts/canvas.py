#!/usr/bin/env python3
"""Fetch one course straight from the Canvas API with the student's own token.

Gets what Cubbie's Canvas sync misses: the Syllabus tab, every assignment
(including ungraded ones), group weights, dropped scores and, when the
instructor set one up, the letter grade scale.

Usage:
    python3 scripts/canvas.py --course "Agentic AI" --out "$SKILL_DATA_DIR/course.json"

Env:
    CANVAS_API_TOKEN   the student's Canvas access token (from cubbie.yaml secrets)
    CANVAS_BASE_URL    optional, default https://canvas.asu.edu

Prints a short summary plus the syllabus grading text. Standard library only.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("CANVAS_BASE_URL", "https://canvas.asu.edu").rstrip("/")
TOKEN = os.environ.get("CANVAS_API_TOKEN", "").strip()


class CanvasError(Exception):
    pass


def get(path, params=None):
    """GET a Canvas API path, following pagination. Returns parsed JSON."""
    url = f"{BASE}/api/v1{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    out = None
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
                link = r.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise CanvasError("TOKEN_INVALID: the Canvas token is wrong or expired.")
            if e.code == 403:
                raise CanvasError(f"FORBIDDEN: {path}")
            if e.code == 404:
                raise CanvasError(f"NOT_FOUND: {path}")
            raise CanvasError(f"HTTP {e.code} on {path}")
        except urllib.error.URLError as e:
            raise CanvasError(f"NETWORK: {e.reason}")
        if isinstance(data, list):
            out = (out or []) + data
        else:
            return data
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    return out or []


def text_from_html(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", "\t", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def grading_part(text, limit=3500):
    """Return the part of the syllabus about grading, or the start if none found."""
    m = re.search(r"(?i)(grading|grade scale|grade distribution|evaluation|assessment|A\+)", text)
    start = max(0, m.start() - 200) if m else 0
    return text[start:start + limit]


def find_course(name):
    courses = get("/courses", {"enrollment_state": "active", "per_page": 100})
    q = name.lower().strip()
    hits = [c for c in courses if q in (c.get("name", "") + " " + c.get("course_code", "")).lower()]
    if not hits:
        words = q.split()
        hits = [c for c in courses if all(w in (c.get("name", "") + " " + c.get("course_code", "")).lower() for w in words)]
    return hits, courses


def cutoffs_for(course_id, standard_id):
    if not standard_id:
        return None
    for path in (f"/courses/{course_id}/grading_standards", f"/courses/{course_id}/grading_standards/{standard_id}"):
        try:
            data = get(path)
        except CanvasError:
            continue
        items = data if isinstance(data, list) else [data]
        for g in items:
            if g.get("id") == standard_id and g.get("grading_scheme"):
                return {row["name"]: round(float(row["value"]) * 100, 2) for row in g["grading_scheme"]}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True, help="part of the course name or code")
    ap.add_argument("--out", required=True, help="where to write the calculator JSON")
    args = ap.parse_args()

    if not TOKEN:
        print("NO_TOKEN: CANVAS_API_TOKEN is not set. Use Cubbie's own Canvas data instead.")
        sys.exit(2)

    try:
        hits, courses = find_course(args.course)
        if len(hits) != 1:
            names = [c.get("name") for c in (hits or courses)]
            print("COURSE_NOT_UNIQUE: " + ("several match" if hits else "no match") + ". Courses:")
            for n in names:
                print(f"- {n}")
            sys.exit(3)
        c = hits[0]
        cid = c["id"]
        course = get(f"/courses/{cid}", {"include[]": ["syllabus_body"]})
        groups = get(f"/courses/{cid}/assignment_groups",
                     {"include[]": ["assignments", "submission"], "per_page": 100})
    except CanvasError as e:
        print(f"ERROR {e}")
        sys.exit(1)

    weighted = bool(course.get("apply_assignment_group_weights"))
    categories = []
    for g in sorted(groups, key=lambda g: g.get("position", 0)):
        cat = {"name": g.get("name", "Group"), "scores": [], "remaining": []}
        if weighted:
            cat["weight"] = float(g.get("group_weight") or 0)
        drop = (g.get("rules") or {}).get("drop_lowest")
        if drop:
            cat["drop_lowest"] = int(drop)
        for a in g.get("assignments", []):
            pts = a.get("points_possible") or 0
            if not pts or a.get("omit_from_final_grade") or a.get("published") is False:
                continue
            sub = a.get("submission") or {}
            if sub.get("excused"):
                continue
            score = sub.get("score")
            if score is not None and sub.get("workflow_state") == "graded":
                cat["scores"].append([float(score), float(pts)])
            else:
                cat["remaining"].append({"name": a.get("name", "Assignment"), "possible": float(pts)})
        if weighted and cat["weight"] == 0:
            continue
        if not weighted and not cat["scores"] and not cat["remaining"]:
            continue
        categories.append(cat)

    cutoffs = cutoffs_for(cid, course.get("grading_standard_id"))
    data = {"course": course.get("name", args.course), "scheme": "weighted" if weighted else "points",
            "categories": categories}
    if cutoffs:
        data["cutoffs"] = cutoffs

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(data, f, indent=2)

    print(f"COURSE: {data['course']} (id {cid})")
    print(f"SCHEME: {data['scheme']}" + (" (Canvas group weights)" if weighted else " (Canvas has no group weights)"))
    for cat in categories:
        w = f" {cat['weight']:g}%" if weighted else ""
        print(f"- {cat['name']}{w}: {len(cat['scores'])} graded, {len(cat['remaining'])} still to come")
    print(f"CUTOFFS: {json.dumps(cutoffs) if cutoffs else 'not set in Canvas; look in the syllabus text below'}")
    print(f"WROTE: {args.out}")
    syl = text_from_html(course.get("syllabus_body") or "")
    print("SYLLABUS (grading part):")
    print(grading_part(syl) if syl else "(the Syllabus tab is empty)")


if __name__ == "__main__":
    main()
