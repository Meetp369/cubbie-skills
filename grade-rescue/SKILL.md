---
name: grade-rescue
description: Use whenever a student asks how many marks or what score they need to get a grade (A+, A, B...), whether they can still get an A, where they stand in a class, or "what if I get X". Reads Canvas grades and the Canvas Syllabus tab (via the browser if needed) and always replies with a per-item plan of marks needed, using clearly labeled assumptions when the syllabus is missing instead of asking the student first.
---

# Grade Rescue

The moment: the end of the semester is coming and the student wants to know what they need. Give them a real number in one reply. Do the digging yourself; the student should not have to send screenshots of things Canvas already has.

## Golden rule: always answer with numbers

Never reply with only a question or a request for screenshots. Missing information is normal; fill it with the assumptions below, run the calculator, and give the plan. Then, after the numbers, ask at most one short question that would make it exact. An estimate with clear assumptions is far more useful than no answer.

A labeled estimate is not guessing: the student asked for a target, and the assumptions are stated so they can correct them. Do not rely on numbers or conclusions from earlier in the conversation; re-read Canvas each time and run every step below.

This holds even when the syllabus file can't be opened and Canvas shows only posted grades. Those are the most common cases; handle them with step 3b, not by stopping.

## 0. Check saved rules first

Before reading Canvas, look in Memory and in `$SKILL_DATA_DIR/rules/` for this course's saved grading rules (weights, scale, list of assessments). If found, use them and skip step 3.

## 0b. Best source: fetch straight from Canvas

Cubbie's own Canvas data can miss the Syllabus tab and ungraded assignments. This Skill's script reads them directly with the student's Canvas token. Run it first:

```
python3 scripts/canvas.py --course "<course name the student used>" --out "$SKILL_DATA_DIR/course.json"
```

- It writes the calculator file (weights, every graded and remaining assignment, dropped scores, and the grade scale if Canvas has one) and prints the syllabus grading text.
- If `CUTOFFS` says not set, read the scale from the printed syllabus text and add `"cutoffs"` to the file. If the syllabus lists different weights than Canvas, use the syllabus weights.
- Then go straight to step 4 (run `grade.py`).

If it prints:
- `NO_TOKEN` or `TOKEN_INVALID`: tell the student once, in one line, that they can add a Canvas token for exact answers (Canvas → Account → Settings → New Access Token), then continue with steps 1–3 using Cubbie's own Canvas data.
- `COURSE_NOT_UNIQUE`: ask which course, using the listed names, then run it again with that name.
- `ERROR NETWORK` or another error: continue with steps 1–3.

## 1. Find the course

- Match the course name loosely ("agentic ai" → the Canvas course whose name contains it). If several match or none was named, ask with a short numbered list.
- If Canvas is not connected, ask them to connect it. Only then fall back to asking for a screenshot of their Grades page and the syllabus.

## 2. Collect ALL assignments from Canvas

The Grades view shows only posted marks, so also read the course's Assignments list, Modules and the Canvas calendar for items not graded yet. Read every assignment in the course, not just the current grade:
- graded items: points earned and points possible, by assignment group
- ungraded or not-yet-due items: their points possible, by assignment group. These are the "remaining" work.

Skip excused items. A submitted item graded 0 is a real 0. A past-due item with no grade is ungraded, not 0, unless Canvas marks it missing with a 0.

Never answer with only the overall Canvas percentage; it hides what is still to come.

## 3. Read the syllabus yourself

In Canvas, the syllabus is usually the **Syllabus tab** in the course menu, not a file. Its address is:

```
https://<school-canvas>/courses/<course_id>/assignments/syllabus
```

(for ASU: `https://canvas.asu.edu/courses/<course_id>/assignments/syllabus`; get `<course_id>` from the Canvas course.)

Try in this order until you find the grading section:
1. The course syllabus through Canvas, if your Canvas ability returns it.
2. **Open the Syllabus tab in your browser.** The first time, the student signs in to their school account (they take over the browser for Duo or two-factor); the login is saved for next time. Tell them: "I'll open your Canvas syllabus. Please sign in once in the browser I send; I'll remember it."
3. While in the browser, also open the course's **Grades** page: it shows every assignment, including ungraded ones (shown as "-/100"), and the "Assignments are weighted by group" table with each group's weight.
4. Course pages, Modules, Files (search "syllabus", "grading"), and announcements.

Extract:
- category weights (or note that the course uses total points)
- the letter grade scale, including plus/minus grades if listed (A+, A, A-…). ASU instructors set their own scale, so always use the syllabus scale.
- dropped scores, and any work not yet on Canvas (a final paper or exam that appears in the syllabus but not in Canvas assignments). Add those to the categories with "scores": [].

If Canvas assignment groups have weights, they must match the syllabus; if they differ, trust the syllabus and mention it.

## 3b. When something is missing, assume and keep going

Use these defaults instead of stopping, and list the ones you used in your reply:

- **No letter scale found:** use the common plus/minus scale `{"A+": 97, "A": 93, "A-": 90, "B+": 87, "B": 83, "B-": 80, "C+": 77, "C": 70, "D": 60}`. Say "I assumed A+ = 97%".
- **No future assignments on Canvas yet** (instructors often publish them later):
  - A syllabus category with no grades at all → whole category still to come (`"scores": []`).
  - A category with some grades → use the syllabus schedule to count how many items are left (e.g. "4 reports" and 2 graded → 2 left, each the same points as the graded ones). If the syllabus doesn't say, treat that category as finished and say so.
- **Weights:** if you found category weights anywhere (syllabus, a course page, an announcement, or the Canvas weights table), use `"scheme": "weighted"` with those weights, and map each assignment to its category by name. If published weights and the Canvas setup differ, use the published weights. Use `"scheme": "points"` only when no weights exist anywhere.

Ask the student for nothing up front. After giving the numbers, ask one question about the biggest assumption.

If you couldn't read the syllabus (for example, the student didn't sign in in the browser), end like this:
> This is an estimate: I assumed A+ = 97% and that the paper is still to come.
> To make it exact, sign in once so I can read your Canvas Syllabus tab, or paste its grading section here. I'll remember it for next time.

## 3c. Save the rules

When the student sends a syllabus (file or photo) or tells you a cutoff, read it, then save the course's rules so you never ask again:
- remember them in Memory (e.g. "Agentic AI grading: Project 50, Reports 30, Paper 10, Participation 10; A+ 97")
- write them to `$SKILL_DATA_DIR/rules/<course>.json` in the calculator format, with `scores` empty

Then immediately recalculate and send the exact plan.

## 4. Run the calculator

Write the data to `$SKILL_DATA_DIR/course.json` and run:

```
python3 scripts/grade.py "$SKILL_DATA_DIR/course.json" --target A
```

Use `--target` with the grade the student asked for. Leave it out if they didn't name one; the script then plans for the best grade still reachable.

Format (weighted course):

```json
{
  "course": "Agentic AI",
  "scheme": "weighted",
  "cutoffs": {"A+": 97, "A": 93, "A-": 90, "B+": 87, "B": 83},
  "categories": [
    {"name": "Project", "weight": 50, "scores": [[45, 50]],
     "remaining": [{"name": "Project milestone 2", "possible": 50}, {"name": "Final project demo", "possible": 100}]},
    {"name": "Reports", "weight": 30, "scores": [[26, 30], [27, 30]],
     "remaining": [{"name": "Report 3", "possible": 30}]},
    {"name": "Paper", "weight": 10, "scores": []},
    {"name": "Quizzes", "weight": 10, "drop_lowest": 1, "scores": [[6, 10], [9, 10]],
     "remaining": [{"name": "Quiz 5", "possible": 10}]}
  ]
}
```

- `scores`: graded items as [earned, possible]
- `remaining`: each ungraded item by its Canvas name with its points possible, so the student sees a per-item plan
- A category with `"scores": []` and no `remaining` is treated as entirely still to come (e.g. a paper or final exam not yet on Canvas).
- Points courses: `"scheme": "points"`, no weights, same `scores` and `remaining`.
- "What if I score 85 on the rest?" → `--what-if 85` instead of `--target`.

If the script prints `ERROR`, tell the student what is missing in plain words.

Never do the math yourself; always use the script's numbers.

## 5. Reply

Always include the per-item list. If the goal is not reachable, run the script again with `--target` set to the highest reachable grade and give that list. A reply without a per-item list is incomplete.

Write like a friend texting, not a report. Don't mention schemes, totals, sync times or how you calculated. Keep assumptions to one short line.

Short texts, one idea each:
1. Where they stand now and how much of the grade is still to come.
2. The goal and the percentage to aim for, then each remaining item with the marks needed, biggest item first, exactly as the script lists them.
3. One line that a higher score on a big item gives room on smaller ones.
4. If the goal is not reachable, say so kindly, give the best possible grade and the plan for the highest reachable grade (run the script again with that `--target`).
5. One useful note (a dropped score, or the scale you assumed).

If they ask for a grade that doesn't exist (e.g. "A++"), say in a few words that the highest is A+ and plan for it.

Example:
> You're at 89.4% in Agentic AI. 61.5% of your grade is still to come.
>
> For an A (93%), aim for 95.4% on everything left:
> • Final project demo: 95.5/100
> • Project milestone 2: 48/50
> • Report 3: 29/30
> • Paper: 95%+
> • Quiz 5 and 6: 10/10 each
>
> Do better on the project and you get a little room on the quizzes.
> A+ isn't reachable anymore; your best possible is 95.8%.

Example when the goal is out of reach:
> A+ isn't possible anymore 😕 Even full marks on everything left gets you 94.2%.
>
> But an A (93%) is! Aim for 97% on what's left:
> • Final project: 97/100
> • Report 3: 29.5/30
> • Paper: 97%+
>
> (I assumed A+ = 97% and A = 93%. If your syllabus says different, paste the grading section and I'll redo it.)

Then offer: "Want to see what happens if you score 90% on everything?" and use `--what-if`.

## 6. Offer a plan (ask first)

Find the next big due dates in Canvas, then offer:
- a check-in before each remaining deadline (student picks the time; suggest 9 pm the night before)
- a wake-up call on exam morning, if there is an exam
- a study guide PDF from the course materials, citing them

Schedule only what the student says yes to. Remember the course and target grade, and when new grades post, offer to recalculate.

## Rules

- Help the student learn; never do graded work for them.
- Grades are private; never share or send them anywhere.
- This is an estimate; the instructor's gradebook is the final word.
