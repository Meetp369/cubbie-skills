# Grade Rescue 🎓

A Cubbie Skill that calculates what a student needs on remaining coursework for a target grade using Canvas data plus official course grading rules.

**Install:** send this folder's GitHub link to Cubbie and approve installation.

**Try it:** `How many marks do I need in CSE 512 to get an A?`

## Files

- `SKILL.md` — Cubbie workflow and accuracy requirements
- `scripts/grade.py` — deterministic calculator (Python standard library only)
- `tests/test_grade.py` — unit/CLI tests
- `examples/` — sample course models
- `cubbie.yaml` — skill runtime/network/secret manifest

## Accuracy contract

The calculator reports `EXACT` only when the course inventory and grading rules are marked verified/complete. Otherwise it reports `PROVISIONAL` and prints warnings. Unknown remaining point totals are never silently invented.

Important input flags:

- `inventory_complete`: whole-term assessment inventory has been checked
- `cutoffs_verified`: letter cutoffs came from official policy or explicit instructor/student information
- `rules_verified`: weighting/point scheme and relevant drop/replacement rules were verified
- `allow_extra_credit`: permit earned points above points possible when course policy intentionally allows it

## Local tests

```bash
python3 -m unittest discover -s tests -v
```

Run an example:

```bash
python3 scripts/grade.py examples/agentic-ai.json --target A
```
