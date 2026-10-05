# SECTION-D PATTERNS — what the out-of-scope scan actually covers

**Purpose.** Phase 2 claims that nothing out of scope (train dynamics, signalling, headway,
capacity, timetable) was implemented. That claim is supported by a **pattern scan**, not by
an exhaustive proof. This file lists exactly which patterns the scan looks for, where the
scan runs, and what a pass therefore does and does not guarantee.

> **Canonical claim wording.** Use this sentence everywhere instead of "no dynamics exist"
> or "verified absent":
>
> *"No forbidden pattern was detected by the Section-D scan (P2-028, BA-12). The scan covers
> the patterns listed in `docs/SECTION_D_PATTERNS.md`; it is a detection guarantee over that
> list, not a proof of absence."*

## 1. The four scan surfaces

| # | Surface | Implemented by | Mechanism | Scope of the check |
|---|---|---|---|---|
| S1 | Package **code** — no function/class named after an out-of-scope concept | `TEST P2-028`, first assertion (`tests/test_phase2_facade_and_app.py`) | AST walk of every `*.py` under `railway_headway_sim/`, excluding `tests/`, `codes.py` and `grr_audit.py` (the catalogue/audit modules may *name* the concepts in order to forbid them); substring match on lowered `FunctionDef`/`AsyncFunctionDef`/`ClassDef` names, plus the allowed-surface assertion of §2.1 | names only — a differently named implementation is **not** covered |
| S2 | **Reference project data** — no result keys | Section-BA check **BA-12** (`infrastructure/grr_audit.py`), re-asserted by `TEST P2-028` | recursive key walk of the GRR-01 document; exact match against `FORBIDDEN_RESULT_KEYS` (list below) | keys, case-insensitively; values are not interpreted |
| S3 | **Static-geometry module API** — no time/dynamics entry points | `test_phase2_static_geometry_has_no_dynamics` (`tests/test_phase2_static_geometry.py`) | public-name scan of the module namespace (`dir(module)`) for substring tokens | public names of that one module |
| S4 | **UI** — planned pages still declared unimplemented | `test_placeholder_pages_do_not_implement_engineering_calculations` (`tests/test_ui_shell.py`), re-asserted by `TEST P2-028` | asserts the six remaining pages (every entry of `PLANNED_PAGES`) render only the `PLANNED FOR LATER DEVELOPMENT PHASE` + "performs no calculations" text, and that `FUNCTIONAL_PAGES` is exactly the five implemented pages, disjoint from `PLANNED_PAGES` and together with it covering `NAVIGATION_TITLES` | the delivered pages only |

## 2. S1 — forbidden implementation names (9 tokens)

`headway`, `blocking_time`, `occupation_time`, `residual_occupancy`, `speed_envelope`,
`traction`, `braking_curve`, `monte_carlo`, `uic406`

Matching rule: token is searched as a substring of the **lower-cased declared name** of every
function, async function and class in the scanned modules. Files `tests/*`, `codes.py`,
`grr_audit.py` are excluded (they name the concepts to forbid them). Phase 5A moved `davis`
and `roeckl` out of this list into the allowed list of **§2.1**; the S1 scan asserts that every
declared name carrying one of those five allowed tokens lives in the
`railway_headway_sim/physics/` package (see §2.1) - the tokens are therefore *not* merely
"no longer forbidden": the surface on which they may appear is checked explicitly.

## 2.1 Phase-5A allowed physics utilities (5 tokens)

`Davis`, `Roeckl`, `rolling resistance`, `curve resistance`, `gradient force`

Stage 5A (application version 0.6.0) delivers the resistance and force utilities that precede
any train motion, so these five quantities are **in scope from Phase 5A on**. They are moved
from the forbidden lists of §2 and §5 to this allowed list; rationale, one line per token:

| Token | Why it is allowed, and where |
|---|---|
| `Davis` | the Davis running resistance `R(V) = A + B*V + C*V**2` [kN] is Stage 5A's deliverable, as `railway_headway_sim/physics/resistance.py::davis_resistance_n` - a pure function of numbers that reads no project, keeps no state and produces no motion quantity. |
| `Roeckl` | the Roeckl curve resistance `W_c = 650 / (R - 55)` [permille] - `roeckl_curve_resistance_n`, `roeckl_equivalent_gradient_permille` and `is_roeckl_radius_usable` in the same module, with the applicability condition `R > 55 m` enforced as a reported error. |
| `rolling resistance` | the plain-language name of the Davis term; it names a force, not a motion, and appears in Stage 5A only as prose in the physics module's documentation and here. |
| `curve resistance` | the plain-language name of the Roeckl term; same boundary - a pure function of mass and stored radius, with no route, no speed, no integration and no time. |
| `gradient force` | the signed force `F = m * g * (gradient_permille / 1000)` [N] - `gradient_force_n`, a pure function of mass and grade, using the frozen normal-railway approximation `sin(theta) ~ tan(theta) ~ gradient_permille / 1000`. |

Matching rule: these five tokens may appear in a declared function/class name **only** inside
the `railway_headway_sim/physics/` package. In the rest of `railway_headway_sim/` (and in every
other surface of §1) a declared name carrying one of them is a finding, exactly as a §2 token
would be: `TEST P2-028` asserts the allowed surface explicitly, and `TEST P5-023` re-asserts it,
together with the fact that the five tokens are absent from the lists of §2 and §3. Nothing else
changed: no other token was moved, removed or weakened, and no surface was removed from the scan.

Stage 5B keeps the same five tokens and the same forbidden lists; it adds the along-route module
`railway_headway_sim/physics/along_route.py` to the allowed package, so the allowed surface is
the package rather than the single module of Stage 5A (declared adaptations A1/A2 of Stage 5B,
recorded in `VERIFICATION.md` §17 and `docs/PHASE1_CHAIN_OF_CUSTODY.md` §7.5). The forbidden
lists of §2 and §3 are byte-identical to their post-5A state, and the new module carries no
forbidden token (`TEST P5-042`).

## 3. S2 — forbidden result keys (14 tokens)

`headway`, `headway_s`, `headway_result`, `blocking_time`, `capacity`, `occupancy`,
`occupation_time`, `timetable`, `arrival_time`, `departure_time`, `residual_occupancy`,
`speed_envelope`, `monte_carlo`, `uic406`

Matching rule: lower-cased key equality anywhere in the document (`$`-rooted walk), for both
the in-memory fixture and the exported text (`"<key>"` substring test in `TEST P2-028`).
`TEST P2-028` additionally asserts that the serialized document contains neither
`arrival_time` nor `departure_time` and that the project declares
`SYNTHETIC` / `REFERENCE_ASSUMPTIONS` / `REFERENCE_TEST_PROJECT`.

## 4. S3 — static-geometry API tokens (7 tokens)

`time`, `speed`, `acceleration`, `brake`, `braking`, `occupation`, `headway`

Matching rule: substring match against every public name in
`railway_headway_sim.infrastructure.static_geometry`. The module's public API is
`compute_static_footprint`, `evaluate_static_footprint`, `traversal_for_direction`,
`StaticFootprint`. Note the deliberate inclusion of the broad token `time`: it means the
module can never grow a timing entry point without failing this check.

## 5. Concepts listed by the Section-D scope statement that the scan does NOT pattern-match

The Phase-2 scope statement also rules out these; they are currently covered by **design and
by the S1-S4 anatomy above**, not by a dedicated token. They are recorded here so the claim's
boundary is explicit (reported as finding F19; no silent widening of the claim):

| Concept | Current coverage | Note |
|---|---|---|
| Davis/Roeckl resistance equations | **delivered in Stage 5A** and allowed in `railway_headway_sim/physics/resistance.py` only (§2.1); the S1 scan asserts the allowed surface, and the equation written *outside* that module under any name is still not pattern-matched | the equation itself is a pure utility since 5A; what stays out of scope is every use of it that needs a train, a route, a speed profile or a time |
| Gradient forces | **delivered in Stage 5A** as the signed `gradient_force_n` and allowed in the same module only (§2.1); `gradient` stays a *unit* label elsewhere and `gradients[]` stays a preserved Phase-1 opaque catalogue | `gradients` is deliberately **not** forbidden (Phase-1 container), exactly as before |
| Traction / braking / speed envelopes | S1 (`traction`, `braking_curve`, `speed_envelope`), S3 | — |
| ETCS movement authority ("MA") | not token-matched (`ma` is too short to match safely) | covered by S1's `headway`/`blocking_time` absence and by the fact that no signalling module exists |
| TVP blocking / route locking / resource occupation | S1 (`blocking_time`, `occupation_time`), S2 (`occupancy`) | "route locking" and "TVP" are not token-matched |
| 7-component decomposition | not token-matched | no module or field carries it; `PLANNED_PAGES` names it only as planned work |
| Technical headway / H(i,j) | S1, S2 (`headway*`) | — |
| Capacity / UIC 406 | S2 (`capacity`, `uic406`), S1 (`uic406`) | `capacity` is **not** an S1 name token (it would match e.g. a future list-capacity helper); recorded as a limitation |
| Timetable simulation / simulated times | S2 (`timetable`, `arrival_time`, `departure_time`) | — |
| Monte-Carlo / sensitivity runs | S1, S2 (`monte_carlo`) | — |
| PDF engineering report | S4 (the Report page is an explicit placeholder) | no report generator exists to scan |
| Placeholder result values (`headway = 0`, `capacity = 0`) | S2 forbids the **keys**; S4 forbids placeholder text in the UI | a placeholder value under an unnamed key would pass S2 |

## 6. What a pass guarantees (and what it does not)

**Guaranteed by a passing scan, over the listed patterns:** no module declares a function or
class whose *name* contains any S1 token, and the five Phase-5A tokens of §2.1 appear in a
declared name only inside `railway_headway_sim/physics/resistance.py`; the reference project
contains no S2 token as a key, and no arrival/departure time field; the static-geometry module
exposes no public name containing any S3 token; the six unimplemented pages still declare
themselves unimplemented (the five functional pages are enumerated by `FUNCTIONAL_PAGES`).

**Not guaranteed:** the absence of an out-of-scope *computation* written under a different
name, encoded numerically, or introduced later without touching the scanned surfaces. This
is why the boundary sentence in the header is the canonical claim.

## 7. Reproduction

```bash
python3 -m pytest railway_headway_sim/tests/test_phase2_facade_and_app.py::test_p2_028_no_out_of_scope_capability_or_result -q
python3 -m pytest railway_headway_sim/tests/test_phase2_static_geometry.py::test_phase2_static_geometry_has_no_dynamics -q
python3 -c "from railway_headway_sim.infrastructure import grr_audit; f={x.check_id:x for x in grr_audit.scan_contradictions()}; print(f['BA-12'].severity, f['BA-12'].evidence)"
# expected: OK {'forbidden_keys_checked': 14}
```

Recorded result: `P2-028` PASS, `test_phase2_static_geometry_has_no_dynamics` PASS,
`BA-12` = OK (`forbidden_keys_checked: 14`). See `docs/TEST_INVENTORY.md` for the collected
counts.
