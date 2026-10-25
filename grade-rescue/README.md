# Grade Rescue 🎓

A Cubbie Skill that tells you exactly what you need on your final to get an A, B or C, using your real Canvas grades and your syllabus rules (weights, dropped scores, cutoffs).

**Install:** text this folder's GitHub link to Cubbie and reply "yes".

**Try it:** "how many marks do I need in Agentic AI to get an A?"

Files:
- `SKILL.md`: instructions for Cubbie
- `scripts/grade.py`: the calculator
- `scripts/canvas.py`: reads the Syllabus tab, all assignments and weights straight from Canvas with the student's token
- `cubbie.yaml`: declares canvas.asu.edu and the Canvas token (standard library only, no packages)
- `examples/`: sample inputs for testing: `python3 scripts/grade.py examples/agentic-ai.json`
