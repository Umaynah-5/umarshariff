# The Three Kinds of Checks Inside an Eval

## 1. Code-based assertions

For things with a right answer: valid JSON? Contains the required disclaimer?

Deterministic, cheap — run these first.

## 2. LLM-as-judge

For subjective things (tone, "did it answer the question"): a second AI grades the output against your criteria, after you've confirmed it agrees with your own grading.

## 3. Human review

You read the raw traces. This never fully goes away.

---

You don't guess what "good" means. You find it by reacting to real outputs.
