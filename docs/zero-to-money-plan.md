# WhisperFlow: 0 → Money Plan

A concise, step-by-step plan to go from zero revenue to a sustainable business, paced for a
**part-time solo founder (~10–15 hrs/week)**. Milestones are in **weeks from Week 1**.

This is the *strategy*. Run each step through the
[monetization-feedback-loop.md](monetization-feedback-loop.md) (Plan → Do → Measure → Learn).
Levers come from [monetizations.md](monetizations.md); the broader product ideas in
[plans.md](plans.md) are deliberately **out of scope** until after ramen profitability.

---

## TL;DR

- **Don't sell "another real-time STT API."** That market is commoditized (Deepgram,
  AssemblyAI, OpenAI, Speechmatics, Google). A part-time founder can't win on scale or price.
- **Sell WhisperFlow's two real edges:** **sub-500ms latency** + **self-hostable (audio never
  leaves the customer's infra)**. That attracts privacy- and cost-sensitive buyers.
- **The wedge is one narrative, two phases:**
  1. **Cash bridge — a fixed-price integration service.** Fastest first dollar, zero product
     build, and it doubles as a design-partner funnel that tells you what to build.
  2. **Compounding product — a thin hosted + self-host transcription service** for one narrow
     ICP, built only as design partners pull it.

| Milestone | Target week | What it means |
|-----------|:-----------:|---------------|
| **M1** First paying customer | ~Week 6 | First dollar in (paid integration sprint / pilot) |
| **M2** First $1k MRR | ~Week 16 | A few recurring paying accounts |
| **M3** Ramen profitable | ~Week 30–40 | Recurring revenue covers your monthly burn |

---

## Positioning

> **"The real-time, self-hostable, cost-predictable transcription engine."**
> Sub-500ms latency. Run it in your own cloud — audio never leaves your infrastructure.

**Pick ONE narrow ICP** (the plan is ICP-agnostic; swap if you have a stronger candidate).
**Default recommendation:** *developers building live voice features* — live captioning, voice
agents, telehealth/scribing — who need low latency **and** on-prem/privacy and want predictable
cost. Narrow beats broad: a specific buyer makes outreach, messaging, and pricing concrete.

---

## The plan, week by week

Paced for ~10–15 hrs/week. Each 2-week block is one turn of the feedback loop.

### Phase A → M1: First paying customer (target ~Week 6)

- **Week 1 — Set the trap.** Pick the ONE ICP. Write a one-line offer. Stand up a simple
  landing page with three calls to action: a priced **"integration sprint,"** a **hosted-beta
  waitlist,** and **"commercial / self-host license — contact."** Add funnel instrumentation
  (visit → CTA click → call booked) per the feedback loop's Instrumentation section.
- **Week 2 — Mine warm demand.** Work existing signals: repo stargazers, GitHub issues/users,
  your network, and 1–2 communities where the ICP lives. ~20–30 targeted outreach touches.
  Lead with the fixed-price integration sprint (concrete, low-risk for the buyer).
- **Weeks 3–4 — Close one.** Run discovery calls. Close **1 paid integration sprint**, paid
  pilot, or a **prepaid design-partner slot**. → **M1: first dollar in.**
- **Weeks 5–6 — Deliver by hand (concierge).** Integrate WhisperFlow into their product
  manually. Extract the three things that drive Phase B: (a) what they'd pay *monthly* for,
  (b) the #1 missing feature, (c) a testimonial / mini case study.

### Phase B → M2: First $1k MRR (target ~Week 16)

- **Weeks 6–8 — Minimum hosted product.** Build the thinnest product layer on top of the
  existing FastAPI server ([whisperflow/fast_server.py](../whisperflow/fast_server.py): `/ws`,
  `/health`, `/transcribe_pcm_chunk`): **API keys + per-minute metering + Stripe usage billing
  + self-serve signup.** No new ML work — the engine already exists.
- **Weeks 8–10 — First recurring revenue.** Convert the Phase-A design partner(s) onto a paid
  monthly plan. Onboard 2–4 waitlist leads as paying beta accounts.
- **Weeks 10–14 — Tighten the funnel.** One hypothesis per iteration: pricing, activation
  (time-to-first-transcript), and a **self-host/commercial-license tier** for any privacy buyer
  who can't use the cloud. Kill what doesn't convert; double down on what does.
- **Weeks 14–16 — Cross $1k MRR** across hosted usage + license + any retainer. → **M2.**

### Phase C → M3: Ramen profitable (target ~Week 30–40, depends on your burn)

- **Weeks 16–24 — Double down on what worked.** Keep only the 1–2 channels that actually
  converted in Phase B (content built on the **latency/benchmark story** — you already have
  real numbers in the README; the OSS repo as a funnel; design-partner referrals). Productize
  the most-requested feature into a higher-priced tier.
- **Weeks 24–40 — Stack recurring + license revenue.** Grow MRR alongside a small number of
  **annual self-host/commercial licenses** (lumpy but high-value — a few of these move the
  needle fast) until recurring revenue covers your personal monthly burn. → **M3.**

> **Assumption to fill in:** "ramen profitable" = your real monthly cost of living (call it
> **$Z/mo**). The Week 30–40 target assumes a modest $Z; set your number and the date shifts
> accordingly. This is the one milestone that depends on a fact only you know.

---

## Pricing & packaging

Starting points — treat every number as a **hypothesis to validate** via the feedback loop, not
a commitment.

| Tier | Shape | Starting hypothesis |
|------|-------|---------------------|
| **Integration sprint** (services) | Fixed-price, time-boxed delivery | One-off fee; your fastest cash + design-partner funnel |
| **Hosted** | Per audio-minute + a monthly minimum | Usage-based; minimum makes small accounts worth serving |
| **Self-host / commercial license + SLA** | Annual | High-value, lumpy; the dual-license lever from [monetizations.md](monetizations.md) |

Positioning anchor: customers pay for **predictable cost + privacy + latency**, not raw
transcription minutes.

## Distribution (cheap first, no paid ads early)

1. **Founder-led outreach** — direct, targeted, to the one ICP. This is the whole game in
   Phase A.
2. **OSS repo as funnel** — add a clear "hosted version / commercial license" CTA in the README
   and repo. Stars and issues are warm leads.
3. **Latency/benchmark content** — you already have real sub-500ms / ~7% WER numbers. Turn the
   benchmark into posts; technical buyers trust numbers.
4. **Design-partner referrals** — happy Phase-A customers introduce the next ones.

## What we build vs. refuse to build

- **Build (only this, in Phase B):** API keys, per-minute metering, Stripe billing, a landing
  page, basic onboarding.
- **Refuse until a paying customer pulls it:** dashboards, multi-region, new/larger models,
  fancy UI, and the full product apps in [plans.md](plans.md) (MetaVox, Linga, LitMind,
  SlideCrafter). **Those are post-ramen expansion bets, not the wedge.**

## Operating cadence

Run the whole plan through [monetization-feedback-loop.md](monetization-feedback-loop.md):
**1–2 hypotheses per 2-week iteration**, each with a metric and a target, logged in the
iteration ledger. A "no" is a successful experiment — kill cheaply and move on.

## Risks & honest caveats

| Risk | Mitigation |
|------|------------|
| Part-time pace slips the timeline | Keep scope brutally small; one hypothesis at a time; protect a fixed weekly block |
| STT is commoditized | Don't compete on raw API — sell latency + self-host + predictable cost to a narrow ICP |
| Self-host/enterprise sales cycles are long and lumpy | Lead with the fast services/hosted revenue; treat licenses as upside, not the base case |
| Single-founder bus factor | Document as you go (these docs); automate billing early; avoid bespoke per-customer code |
| Building before demand is proven | The "refuse to build" list is the guardrail; nothing ships until a customer pulls it |

---

## Milestone summary

| Milestone | Target week | Definition of done | Primary metric |
|-----------|:-----------:|--------------------|----------------|
| **M1** First paying customer | ~Week 6 | First paid sprint / pilot / prepaid slot closed | First dollar collected |
| **M2** First $1k MRR | ~Week 16 | Recurring revenue ≥ $1k/mo across hosted + license + retainer | MRR |
| **M3** Ramen profitable | ~Week 30–40* | Recurring revenue ≥ your monthly burn ($Z) | MRR vs. personal burn |

\* Depends on your actual monthly burn ($Z) — set it and the date firms up.
