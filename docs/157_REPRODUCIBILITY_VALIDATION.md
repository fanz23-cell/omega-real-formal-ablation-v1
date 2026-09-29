# 157. Reproducibility Validation (Clean-Room)

Package extracted into a fresh directory (`/tmp/omega_real_formal_repro_cleanroom/`), NOT the
original research directory, per directive section 41.

## Results

| check | command | exit code | result |
|---|---|---|---|
| MANIFEST verify | `scripts/verify_package.sh` | 0 (after 1 fix) | PASS — 68/68 files match |
| Level 1 analysis | `scripts/reproduce_analysis.sh` | 0 | PASS — byte-identical `154_statistical_analysis.json` recomputed from raw rows alone |
| Level 2 component witness | `scripts/reproduce_component_witness.sh` | 0 | PASS — all 9 negative controls reject correctly; real MeTTa witness reproduces the exact same G6 result (frequency=0.5555, confidence=0.9479) from the clean-room copy |

## One real bug found and fixed during this validation

The first clean-room copy (`cp -r package/* dest/`) silently omitted `.env.example` — a
dotfile the shell glob `*` doesn't match. `scripts/verify_package.sh` caught this
immediately (`sha256sum: WARNING: 1 listed file could not be read`) rather than silently
passing. Fixed by copying the dotfile explicitly; documented here as a real packaging lesson
(the actual release tarball is built with `tar czf` directly against the source directory,
not a glob-based copy, avoiding this class of bug entirely).

## Secret scan

`results/secret_scan.txt`: PASS (no gitleaks available in this environment; conservative
regex scan for private-key markers, AWS-style keys, and hardcoded `api_key=` assignments
found 0 matches across the whole package).

## Portability

`grep -rn "/home/mindbot" harness/*.py`: 0 matches — no machine-specific absolute paths in
any runnable script. `docker/IMAGE_PROVENANCE.md` and `REPRODUCE.md` mention the original
run's paths for context only, never inside code that executes.

## Level 3 (full paid reproduction)

Not run as part of this validation (would spend real money redundantly — the actual
confirmatory run already IS this level 3, at real cost $48.60, see doc 153's disclosed cost
correction). `scripts/reproduce_full_benchmark.sh` is present and its invocation pattern was
exercised structurally (argument parsing, isolated-container existence check) but not run
to completion against a fresh seed pool, per the directive's own "do not rerun the entire
paid benchmark merely for packaging validation" instruction.
