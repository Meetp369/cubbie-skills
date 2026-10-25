---
name: grade-rescue
description: Use when a student asks what score they need for a target grade, whether a grade is still reachable, where they stand, or a grade what-if. Read the full Canvas course and official grading policy, build a complete course model, run the deterministic calculator, and clearly distinguish exact results from provisional estimates.
---

# Grade Rescue

Give students a useful numerical answer without pretending incomplete gradebook data is exact. Canvas's displayed current grade is usually based only on graded work; never treat it as percentage points already earned toward the final course grade.

## Non-negotiable accuracy rules

1. Re-read the current Canvas course data for every calculation. Do not reuse old grade numbers from chat or memory.
2. Inventory the **whole term**, including unpublished/future work visible in Assignments, Modules, Calendar, syllabus, announcements, and exam/project schedules.
3. Use the official syllabus/course policy for category weights, drop rules, extra credit, and letter cutoffs. Canvas assignment-group weights are a fallback/cross-check, not proof of the letter scale.
4. Never silently assume that A = 93% (or any other cutoff) and call the result exact.
5. Never call an equal-percentage plan a set of independent minimums. Scores trade off according to final-grade impact.
6. Never do grade arithmetic yourself. Build JSON and run `scripts/grade.py`.
7. If an input is unresolved, return a **PROVISIONAL** scenario and name the largest uncertainty. Exact-looking numbers must not hide missing data.

## 1. Select the course

Match the student's course loosely. If none or several match, ask one short course-selection question. If Canvas is disconnected, ask them to connect it; only then fall back to screenshots/manual data.

## 2. Build a full-term assignment inventory

Collect every graded and remaining assessment. For each item capture:
- exact Canvas name
- assignment group/category
- earned points if graded
- points possible
- due date/status when available

Cross-check Grades against Assignments, Modules, Calendar, syllabus and announcements. Do not use only the Grades page because unpublished/future work may be absent.

Set `inventory_complete: true` **only** when you have checked the whole-term sources and can account for all graded and remaining assessments described by official course material. Otherwise set it false.

For a future item whose existence is known but points are unknown, put `"possible": null`. Do not invent its point value.

## 3. Verify grading rules

Read the Canvas Syllabus tab and syllabus files; also check official course pages/announcements when needed. Extract:
- weighted categories, or confirmation that the course is total-points based
- letter-grade cutoffs including plus/minus grades
- drop-lowest/drop-highest or replacement rules
- extra-credit treatment
- assessments mentioned in policy/schedule but missing from Canvas assignments

Set:
- `cutoffs_verified: true` only when the requested letter cutoff came from official course policy or the instructor/student explicitly supplied it.
- `rules_verified: true` only when weights/point scheme and relevant drop/replacement rules were verified against official course policy.

If Canvas and syllabus conflict, use the official published course policy and mention the discrepancy.

### Missing policy

Do not stop just because one policy detail is unavailable. Build the best provisional model and let the calculator label it. If no cutoffs are available, omit `cutoffs`; the calculator uses its fallback scale and marks the result provisional. After the numbers, ask at most one question about the uncertainty that could change the answer most.

Do **not** save assumed rules as verified rules.

## 4. Build calculator JSON

Weighted example:

```json
{
  "course": "CSE 512",
  "scheme": "weighted",
  "cutoffs": {"A": 90, "B": 80},
  "cutoffs_verified": true,
  "rules_verified": true,
  "inventory_complete": true,
  "categories": [
    {"name": "Assignments", "weight": 30, "scores": [[100, 100]],
     "remaining": [{"name": "Assignment 02", "possible": 100}]},
    {"name": "Group Project", "weight": 25, "scores": [[20, 20]],
     "remaining": [{"name": "Phase 02", "possible": 30}, {"name": "Phase 03", "possible": 50}]},
    {"name": "Final Exam", "weight": 10, "scores": [],
     "remaining": [{"name": "Final Exam", "possible": null}]}
  ]
}
```

For total-points courses use `"scheme": "points"` and omit weights. A points-based course cannot produce a reliable course-total calculation while a known remaining item's points are unknown; the calculator will error instead of guessing.

For weighted categories, if a future item's points are unknown, use null. The calculator will mark the category unresolved/provisional rather than fabricating a denominator.

`drop_lowest` may be added to a category. Set `allow_extra_credit: true` only when scores above points possible are intentional under course policy.

## 5. Run the calculator

Write the model to `$SKILL_DATA_DIR/course.json` and run:

```bash
python3 scripts/grade.py "$SKILL_DATA_DIR/course.json" --target A
```

Use the exact grade requested. For a what-if:

```bash
python3 scripts/grade.py "$SKILL_DATA_DIR/course.json" --what-if 85
```

If the calculator prints `ERROR`, do not bypass it with mental math. Explain the missing/invalid input and, if possible, collect the missing course data.

## 6. Interpret output faithfully

### EXACT

You may say "you need" when the calculator says `Status: EXACT`.

Include:
- current Canvas-style grade on graded work
- verified target cutoff
- remaining modeled final-grade weight
- required average across remaining work
- equal-percentage target per remaining item
- a sentence that these item targets are **not independent minimums** and can trade off

### PROVISIONAL

Use words such as "estimate", "under this model", or "provisional". Never present provisional item scores as guaranteed requirements. Include the calculator warning that matters most and ask at most one question that would make the result materially more accurate.

If the final exam or another item's points are unknown, a percentage target for that item is acceptable; do not invent raw marks.

If the requested grade is unreachable, report the best possible result under the model and the highest reachable grade. If useful, rerun for that reachable grade.

## 7. Response style

Be concise and student-friendly, but preserve the accuracy labels. A good response is:

> You're at 99.41% on graded work. This result is **provisional** because the final's point total and the syllabus A cutoff are not verified.
>
> Under the current model, an A at 93% would require an 85.63% average across the remaining modeled work.
> • Assignment 02: about 86/100
> • Phase 02: about 26/30
> • Phase 03: about 43/50
> • Final: about 86%
>
> Those are an equal-percentage plan, not separate minimums—doing better on a higher-impact item can offset another score.
>
> The biggest uncertainty is the official A cutoff/final structure. If I can verify that grading section, I can make this exact.

Do not say that the student's displayed Canvas grade is their final-course contribution.

## 8. Remember verified rules only

When the student supplies an official syllabus/policy or explicit instructor cutoff, save verified course rules to `$SKILL_DATA_DIR/rules/<course>.json` for reuse. Preserve provenance (for example `source: "syllabus"`) when possible. Never promote fallback assumptions to verified status.

## 9. Optional follow-up

After answering, you may offer a what-if scenario or a recalculation when new grades post. Schedule reminders/check-ins only with student consent. Never do graded work for the student; offer study planning or explanations instead.

Grades are private. The instructor's gradebook and published course policy are authoritative.
