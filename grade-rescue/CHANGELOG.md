# Grade Rescue hardening changes

- Added strict JSON/input validation and clear errors for malformed or mathematically underdetermined course models.
- Added `EXACT` vs `PROVISIONAL` status based on verified cutoffs, verified grading rules, and complete full-term inventory.
- Added `inventory_complete`, `cutoffs_verified`, `rules_verified`, and `allow_extra_credit` contract fields.
- Removed silent target substitution for unknown grades such as `A++`.
- Added fallback plus/minus scale only as an explicitly warned provisional assumption.
- Clarified that per-item outputs are an equal-percentage plan, not independent minimum scores.
- Added safeguards for unknown remaining point totals. Partial weighted categories with unknown future points now fail rather than inventing a denominator.
- Added extra-credit validation and what-if range validation.
- Updated skill instructions to cross-check the whole term and official syllabus/policy before claiming exactness.
- Corrected README manifest documentation.
- Added 9 unit/CLI tests and retained compatibility with all four original examples.
