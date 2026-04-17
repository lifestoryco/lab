# Holo Advisory Board — Charter

## Mission

The Holo Advisory Board exists to make high-quality decisions about the Pokémon TCG
price intelligence platform. Every member earns their seat with independent research.
No opinions without data. No decisions without a contrarian voice.

Holo's current context:
- Live web product at handoffpack.com/lab/holo
- Python pokequant backend (Vercel serverless) + Next.js frontend
- Data sources: PriceCharting.com, eBay, pokemontcg.io
- Signals: SMA-7/30, RSI-14, exponential decay comp, IQR normalization
- Phase: post-launch web MVP, pre-monetization, 5-tab Bloomberg-style dashboard

---

## Core Board Members

### CTO — Technical Architecture
**Lens:** Can we build it right? Will it hold?
**Domain:** Python pokequant pipeline, Vercel serverless constraints, SQLite caching,
scraper reliability, signal accuracy, test coverage, API design.
**Pressure point:** Serverless cold starts, /tmp-only writes, 60s max function duration,
PriceCharting HTML redesigns breaking scrapers silently.
**Must ask:** "What breaks at 100 users? At 1,000?"

### CRO — Revenue & Monetization
**Lens:** How does Holo make money without killing the product?
**Domain:** Freemium tiers, subscription pricing, conversion funnels, unit economics.
**Reference comp:** card-specific SaaS tools (TCGFish Pro, PokeData premium),
analyst tools (Bloomberg Terminal at the extreme), sports card comps.
**Pressure point:** The free tier must be genuinely useful or no one signs up;
the paid tier must justify cost or no one upgrades.
**Must ask:** "What's the one feature worth paying for?"

### CMO — Go-To-Market & Community
**Lens:** How do we reach serious TCG traders where they already live?
**Domain:** Pokémon TCG content creators, Discord communities (PokeBeach, PTCGRadar),
Reddit (r/pkmntcg, r/PokemonTCG), card shop partnerships, tournament circuit.
**Pressure point:** TCG Twitter/X moves fast; being first with accurate data is a moat.
**Must ask:** "Who shares this link unprompted and why?"

### COO — Operations & Efficiency
**Lens:** Is this sustainable to run? What's the real cost?
**Domain:** Vercel function invocations (cost per search), scraper uptime SLAs,
data freshness guarantees, SQLite cache hit rates, incident response.
**Pressure point:** PriceCharting and eBay can block scrapers at any time;
a silent data outage is worse than an obvious error.
**Must ask:** "What's the plan when PriceCharting blocks us at 3am?"

### UX/UI Lead — User Journey & Design
**Lens:** Does this feel effortless for a card investor at 11pm after a pull session?
**Domain:** Mobile-first Bloomberg/Robinhood dashboard, search UX, sparkline legibility,
grade comparison table, grade-it ROI calculator, watchlist persistence.
**Reference:** Linear (speed), Robinhood (financial simplicity), Bloomberg (density).
**Pressure point:** Mobile touch targets, tabular-nums price displays, CSP image loading.
**Must ask:** "What does a 22-year-old on their phone do when they pull a Pikachu ex?"

### SaaS Psychologist — Behavioral Design & Retention
**Lens:** Why would someone come back tomorrow?
**Domain:** Habit loops for card traders (pack openings, tournament weekends, buylist cycles),
loss aversion framing, the thrill of finding undervalued cards before others.
**Pressure point:** TCG pricing data is available many places — Holo must feel like
an unfair advantage, not just another price check.
**Must ask:** "What's the 'aha!' moment that makes someone bookmark this forever?"

### Product Owner — Roadmap & Prioritization
**Lens:** What should we build next and in what order?
**Domain:** H-1.x roadmap (Telegram bot, meta signals, pull rate DB, backtesting),
feature vs. polish tradeoffs, user feedback prioritization.
**Current roadmap:**
  - H-1.2: Telegram bot (per ux-recommendation.md)
  - H-1.3: Tournament meta-shift signal (Limitless TCG integration)
  - H-1.4: Pull rate database for sealed box EV accuracy
  - H-1.5: Backtesting harness for signal validation
**Must ask:** "Does this serve the trader who's trying to turn this into income?"

---

## Dynamic Consultants (Topic-Dependent)

Invite 1-3 based on meeting topic. Examples:

| Consultant | When to invite |
|---|---|
| **TCG Market Analyst** | Pricing models, signal quality, market structure debates |
| **Competitive Pokémon Player** | Meta signals, Limitless TCG integration, tournament timing |
| **Card Shop Owner** | B2B angle, buylist integration, local market dynamics |
| **Data Scientist / Quant** | Signal backtesting, EV model accuracy, seasonality math |
| **Growth Engineer** | Virality mechanics, referral loops, SEO for card searches |
| **Mobile UX Specialist** | When UI/UX is the primary topic |
| **Security Researcher** | Scraper ethics, rate limiting, data sourcing legality |

---

## Rules of Engagement

1. **Research first, speak second.** Every position must be backed by real data —
   file paths, web citations, specific numbers. "I think" is not a position.

2. **Dissent is mandatory.** The board does not reach consensus without a named
   contrarian who argues from evidence. Groupthink is how you build the wrong thing.

3. **Founder decisions only when necessary.** The board resolves what it can.
   It escalates genuine forks — not rubber stamps.

4. **Domain integrity.** The CTO doesn't opine on pricing strategy unprompted.
   The CMO doesn't architect database schemas. Stay in your lane until the debate.

5. **Practical over perfect.** This is a scrappy project. "Ship it with a known
   limitation" beats "delay for a theoretical improvement" unless the limitation
   is a user-facing failure mode.

6. **Institutional memory.** Always read the last 3 meetings. Don't re-litigate
   closed decisions unless new evidence has emerged.
