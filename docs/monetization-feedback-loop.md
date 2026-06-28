# Monetization Feedback Loop

A continuous, evidence-driven cycle for finding and growing revenue for WhisperFlow and the
products built on it ([Linga, LitMind, MetaVox, SlideCrafter](plans.md)). Strategy is never
"decided once" — it is a loop we run on a fixed cadence: **Plan → Do → Measure → (Learn) →
start over.**

The point of the loop is to treat every monetization idea from [monetizations.md](monetizations.md)
as a hypothesis to be tested cheaply, kept if it works, and dropped if it doesn't.

```
        ┌───────────────────────────────────────────────┐
        │                                               │
        ▼                                               │
   ┌─────────┐      ┌─────────┐      ┌──────────┐      ┌─┴────────┐
   │  PLAN   │ ───▶ │   DO    │ ───▶ │ MEASURE  │ ───▶ │  LEARN   │
   │hypothesis│      │ run the │      │ collect  │      │ decide:  │
   │ + metric │      │ smallest│      │ the data │      │ keep /   │
   │ + target │      │  test   │      │ vs target│      │ pivot /  │
   └─────────┘      └─────────┘      └──────────┘      │  kill    │
        ▲                                               └─┬────────┘
        │                                                 │
        └─────────────────────────────────────────────────┘
                         feeds the next Plan
```

**Cadence:** one full turn of the loop per **2-week iteration**, reviewed in a short retro.
Run only **1–2 hypotheses at a time** so the Measure step can attribute the result.

---

## 1. PLAN — form a hypothesis

Pick one monetization lever and turn it into a falsifiable bet. Write it down before doing
anything.

- **Choose a lever** from [monetizations.md](monetizations.md): paid support, dual licensing,
  freemium premium features, SaaS, sponsored development, donations, courses, enterprise
  customization.
- **Choose a segment**: open-source library users, a single product surface (e.g. MetaVox
  SaaS), or an enterprise buyer.
- **Write the hypothesis** in one sentence:
  > "We believe *[segment]* will pay for *[offer]* because *[value]*. We'll know it's true if
  > *[metric]* reaches *[target]* by *[date]*."
- **Define one primary metric and a target** (see the metric menu below). Targets are
  pass/fail thresholds, not vanity goals.
- **Define the smallest test** that can validate or kill the hypothesis (a pricing page, a
  "contact us for enterprise" button, a single sponsor email, a landing page).

**Exit criteria for PLAN:** a written hypothesis, one primary metric, a numeric target, and a
test that fits inside one iteration.

## 2. DO — run the smallest test

Build the least amount possible to get a real signal. Bias toward fake-door and
concierge tests over full features.

- **Demand tests:** pricing/landing pages, "Buy / Contact sales" buttons that capture intent,
  waitlists.
- **Manual-first delivery:** deliver the paid value by hand (concierge consulting, a manually
  run MetaVox job) before automating it.
- **Packaging tests:** publish a commercial-license page, a sponsorship tier, a GitHub
  Sponsors / Open Collective page.
- **Instrument everything** as you ship it — the Measure step is only as good as the events you
  capture (see Instrumentation below).

**Exit criteria for DO:** the test is live, instrumented, and exposed to real users for the
iteration window.

## 3. MEASURE — collect the data vs. the target

Compare the primary metric against the target set in PLAN. Be honest; a "no" is a successful
experiment.

### Metric menu (pick the one that matches the lever)

| Lever | Primary metric | Example target |
|-------|----------------|----------------|
| SaaS / freemium | Free → paid conversion rate | ≥ 3% of activated users |
| SaaS | MRR / net revenue retention | First $X MRR; NRR ≥ 100% |
| Pricing test | Willingness-to-pay (clicks on a priced tier) | ≥ N intent signals/week |
| Dual licensing | Qualified commercial-license leads | ≥ N inbound/quarter |
| Paid support | Closed support/consulting contracts | ≥ 1 paying account |
| Sponsorship / donations | Recurring sponsor revenue | First $X/month committed |
| Courses | Pre-orders / completed sales | ≥ N pre-orders before building |
| Any | CAC vs. LTV | LTV : CAC ≥ 3 : 1 |

### Supporting / guardrail metrics

- Activation rate (users who reach first transcription value)
- Retention / churn
- Funnel drop-off (visit → signup → activate → pay)
- Cost to serve (inference/compute per active user — relevant given WhisperFlow's latency goals)
- Community health (stars, contributors, issues) so monetization doesn't erode the open-source base

**Exit criteria for MEASURE:** a single recorded result — *metric, actual value, target, met /
not met* — plus any surprising qualitative signal.

## 4. LEARN — decide, then loop

Close the iteration with an explicit decision. This decision becomes the seed of the next PLAN.

- **Keep / double down** — target met: scale it, raise the target, invest in automation.
- **Pivot** — partial signal: change the segment, price, or packaging and re-test.
- **Kill** — no signal: archive the hypothesis (record *why*) and pick a different lever.

Log every iteration in the ledger below so the loop has memory and we don't re-test dead ideas.

### Iteration ledger

| # | Dates | Hypothesis (lever / segment) | Primary metric | Target | Result | Decision |
|---|-------|------------------------------|----------------|--------|--------|----------|
| 1 | _TBD_ | _e.g. SaaS / MetaVox creators_ | _e.g. free→paid %_ | _3%_ | _—_ | _Keep / Pivot / Kill_ |
| 2 | | | | | | |
| 3 | | | | | | |

---

## Instrumentation (so MEASURE is trustworthy)

- Capture funnel events: landing view → signup → activation (first transcript) → upgrade click
  → payment.
- Tag traffic by experiment/segment so results are attributable to one hypothesis.
- Track unit economics per active user (compute/inference cost) alongside revenue.
- Keep a lightweight dashboard; the loop depends on data being visible at retro time.

## Operating principles

- **One loop, fixed cadence** — review every iteration; don't let a test run open-ended.
- **Smallest test first** — validate demand before building features.
- **1–2 hypotheses at a time** — keep results attributable.
- **A "no" is a win** — killing a bad bet cheaply is the loop working as designed.
- **Protect the open-source core** — monetization must not degrade the free experience that
  drives adoption (community health is a guardrail metric).
