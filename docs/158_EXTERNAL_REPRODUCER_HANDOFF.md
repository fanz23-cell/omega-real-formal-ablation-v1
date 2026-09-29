# 158. External Reproducer Handoff

*Written for a reader who has no context on this project's prior conversations, chat history,
or internal docs — a professor, an internal engineer new to this codebase, or a
SingularityNET/Omega researcher evaluating this result independently.*

## System context (what you need to know before anything else)

This project runs a service robot cognition stack: an LLM-driven "Omega" agent that reasons
over recorded evidence using a bounded, deterministic formal-logic module (NAL/PLN, executed
by a MeTTa interpreter called PeTTa, itself implemented in SWI-Prolog). Production has one
specific, narrow, already-deployed capability: when two recorded observations directly
contradict each other (e.g. "the door is locked" and "the door is not locked," both about the
exact same thing, from evidence of comparable weight), the system can invoke a `revision`
operation that computes a combined truth value (a frequency/confidence pair) and returns it
as an advisory — never as an automatic action, always flagged `authority=NONE`, meaning a
human or a separate authoritative check must still decide what to actually do.

## The research question

Does that real numeric computation itself add decision value, or does simply telling the
model in plain language "these two things conflict, be careful" already capture all the
benefit?

## Why this question needed a NEW study

An earlier round of this benchmark answered a related question ("does a
structured-memory-plus-formal-advisory system beat a weak, unstructured baseline?") and found
a large, clean effect. But that earlier study's "formal advisory" arm was, on inspection, a
hand-written Python function that mimicked the shape of the real math — it never called the
actual MeTTa interpreter. That is scientifically insufficient to answer THIS question: it
cannot distinguish "the real math helps" from "a python approximation of it that happens to
look similar helps." This round rebuilds the experiment to call the real, unmodified
production code end-to-end (proven via `docs/149_real_metta_end_to_end_witness.md` — two
real software bugs were found and fixed just getting the real invocation working at all,
documented there in full), and adds a THIRD arm the earlier study didn't have.

## The three arms

- **B0**: sees the raw conflicting evidence. No conflict label of any kind.
- **B1**: sees the same evidence, PLUS a plain-language label ("these two things conflict,
  escalate or recheck") — but the two numeric fields a full advisory would carry are replaced
  with the literal placeholder text `WITHHELD_CONTROL`. This arm exists specifically to
  isolate "value of being told there's a conflict" from "value of the actual computed
  numbers."
- **C**: identical to B1, except the two numeric fields are real — computed by actually
  running the case's two evidence claims through the real MeTTa `Truth_Revision` equation
  inside an isolated (network-disabled, scratch-storage-only) clone of the exact production
  container image.

**The primary comparison is C vs B1** — not C vs B0. B0 exists only as a secondary reference
(to confirm the plain conflict label itself is doing real work, which it is: +20.1 percentage
points over B0, essentially certain not to be chance, p≈1×10⁻⁷).

## The result

Across 189 held-out test cases (9 pre-declared confidence-pattern types × 3 history sizes ×
7 repeats, 567 real language-model calls), **C and B1 perform statistically
indistinguishably** (-1.1 percentage points, 95% confidence interval [-4.8, +2.7]pp,
p=0.77). This null result replicates across every one of the 9 confidence patterns tested,
including the ones specifically designed to be hardest (near-ties, extreme asymmetries), and
at every history size tested (10, 100, and 1000 background facts). A closer look at the dozen
individual cases where the two arms actually disagreed found something worth flagging on its
own merits regardless of the aggregate null: in at least two concrete cases, giving the model
the real numeric result appears to have encouraged it to treat an extreme number as
justification to assert a confident conclusion the system's own design says it should not
(the advisory's own semantics are "escalate, don't resolve," and in those cases the model
resolved anyway) — offset by two mirror cases where the plain-label arm made the identical
mistake with no numbers involved at all.

## What to conclude, and what not to

**Reasonable to conclude**: the currently-deployed production feature's practical benefit
almost certainly comes from making conflicts explicit and salient in the first place, not
from the specific mathematical computation used to score them. A simpler, cheaper, MeTTa-free
mechanism that just flags "these conflict" might do equally well — that specific comparison
was not run here but is the natural next experiment this result motivates.

**Not a reasonable conclusion**: that the mathematics is wrong (it was independently
hand-verified correct, see doc 149), that formal reasoning has no place in this system, or
that other operators (deduction, abduction) would show the same pattern — none of those were
tested here.

## How to check this yourself

Full runnable package, three levels of reproduction (no-cost verification through full paid
re-run), in the sibling `omega_real_formal_ablation_v1_release/` package —
`REPRODUCE.md` there is the entry point. All raw model completions, not just aggregated
scores, are included so you can read exactly what the model said in any specific case.
