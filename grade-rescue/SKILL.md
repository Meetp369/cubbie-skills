---
name: grade-rescue
description: Tells a student exactly what they need on their remaining work (final exam, projects, reports, papers) to get each letter grade, using their real Canvas grades and the syllabus rules. Use when the student asks what marks or score they need, whether they can still get an A, where they stand in a class, or "what if I get X".
---

# Grade Rescue

The moment: the end of the semester is coming and the student wants to know what they need. Give them a real number in one reply. Do the digging yourself; the student should not have to send screenshots of things Canvas already has.

## Golden rule: always answer with numbers

Never reply with only a question or a request for screenshots. Missing information is normal; fill it with the assumptions below, run the calculator, and give the plan. Then, after the numbers, ask at most one short question that would make it exact. An estimate with clear assumptions is far more useful than no answer.

This holds even when the syllabus file can't be opened and Canvas shows only posted grades. Those are the most common cases; handle them with step 3b, not by stopping.

## 0. Check saved rules first

Before reading Canvas, look in Memory and in `$SKILL_DATA_DIR/rules/` for this course's saved grading rules (weights, scale, list of assessments). If found, use them and skip step 3.

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
- **No weights found:** use the Canvas assignment group weights; if there are none, use `"scheme": "points"`.

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
