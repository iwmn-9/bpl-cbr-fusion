# Brief: final micro-fixes after re-review

For the implementing AI session (dsh, DeepSeek V4.1 Flash, reasoning MAX).
AGENTS.md wins on any conflict. Work only in this directory. Do not edit
BRIEF-*.md or docs/. Two items remain from the re-reviews; both are
small. `python3 demo.py` output must stay exactly as it is now.

## Item A — citation comment wording (semantic re-review)

In library.py, replace the anti-unification citation comment so it
reads, in substance and close to verbatim:

"Anti-unification / least general generalization, restricted to
structurally identical skeletons (Plotkin 1970); the promotion loop is
the same family of move as DreamCoder's library learning (Ellis et al.
2021), minus the neural parts and minus its MDL acceptance test."

Keep it a short comment at the same place. Nothing else about the
comment block changes.

## Item B — template IDs must be monotonic (code re-review)

`_next_template_id` currently derives the next ID from the maximum
suffix among live templates, so a dissolved template's ID gets reused
(a log can show "dissolved T2" followed by an unrelated "promoted
T2"). Make IDs monotonic for the lifetime of a library:

- Library carries a persistent counter for the next template number,
  saved and loaded with the rest of library.json.
- Allocation takes the counter value and increments it; dissolved IDs
  are never reused.
- A library.json without the counter (older files) initializes it to
  one past the maximum existing suffix.

## Acceptance

- `python3 demo.py` output identical to the current run (paths,
  promotion events, T1/T2 with support 4/3, references 7/7, net size
  delta +152 B). Note: in a fresh demo the counter starts at 1, so the
  demo still names them T1 and T2.
- A dissolution scenario check: dissolve a template, then promote a
  new one; the new ID must not reuse the dissolved ID.
- Existing save/load round-trips still work, including a library.json
  written without the counter field.
