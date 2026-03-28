---
name: No lambda assignments
description: User prefers def over assigning lambda expressions to variables
type: feedback
---

Do not assign a `lambda` expression to a variable — use a `def` instead.

**Why:** Style preference / linting rule (E731). Lambda assignments obscure the function name in tracebacks and are less readable.

**How to apply:** Whenever you'd write `FOO = lambda: ...`, write `def FOO(): ...` instead.
