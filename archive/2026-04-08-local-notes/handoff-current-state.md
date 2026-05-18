# pre-Elixis working name Project Handoff Document
## Current State & Pending Items
**Date:** 2026-04-08
**Author:** Claude Code Session
**Status:** Translation service complete, naming decision pending

---

## ✅ COMPLETED WORK

### 1. Kyanite Translation Service (Shared Infrastructure)

**Location:** `/Users/simongonzalezdecruz/workspaces/kyanite-translation-service/`

**Status:** Fully operational, documented, licensed

**Features Implemented:**
- SHA256-based translation caching with 30-day TTL
- Local LLM inference via Ollama with intelligent fallback
- SSE streaming for real-time translation responses
- 29-language support with intelligent language detection
- Docker containerization with docker-compose
- Python client library (`kyanite_translate`)
- JavaScript/TypeScript client (`kyanite-translate.js`)

**Key Files:**
- `app.py` — Flask service with `/translate` endpoint
- `cache_manager.py` — SQLite-based persistent caching
- `clients/python/kyanite_translate.py` — Python client
- `clients/js/kyanite-translate.js` — Browser/Node client
- `INTEGRATION.md` — Integration guide for all projects
- `docker-compose.yml` — Production-ready container setup
- `LICENSE` — MIT License (Kyanite Labs 2026)

**Environment:**
- Service runs on port 3111
- Requires `LLM_BASE_URL` pointing to Ollama instance
- Default model: `phi4:latest` (configurable)

---

### 2. pre-Elixis working name Core (Python Project)

**Location:** `/Users/simongonzalezdecruz/workspaces/pre-Elixis working name/`

**Status:** Core engine functional, translation integration ready

**Integration with Translation Service:**
- pre-Elixis working name now uses Kyanite Translation Service client
- Replaced inline translation with service-based architecture
- 29-language persona generation capability

**Key Files:**
- `src/` — Core Python modules
- `docs/marketing-pass-pre-elixis-working-name.md` — Full marketing strategy
- `docs/trademark-pass-pre-elixis-working-name.md` — Legal risk assessment
- `LICENSE` — MIT License (Kyanite Labs 2026)

---

### 3. Marketing Strategy Pass

**Document:** `docs/marketing-pass-pre-elixis-working-name.md`

**Key Decisions:**
- **Category:** AI Identity Synthesis & Specification (new category)
- **Positioning:** Identity layer between user intent and agent execution
- **Metaphor:** Cross-domain synthesis (use conceptually, do not brand around the prior literary source)
- **Tagline:** "Give Your AI a Soul" / "Find the Thread"
- **Target Audiences:**
  1. Framework Architects (OpenClaw devs) — PRIMARY
  2. Creative Technologists (writers, game designers)
  3. Enterprise Integrators (consultants)

**Competitive Position:**
- Complements OpenClaw (generates SOUL.md that OpenClaw consumes)
- Different from Character.AI (produces specs, not chatbots)
- Different from prompt marketplaces (synthesizes custom, doesn't sell templates)

**GTM Phases:**
- Phase 1: Developer Evangelism (GitHub, Show HN)
- Phase 2: Creative Adoption (Twitter/X content, YouTube)
- Phase 3: Enterprise Expansion (hosted cloud version)

---

### 4. Trademark Risk Assessment Pass

**Document:** `docs/trademark-pass-pre-elixis-working-name.md`

**⚠️ CRITICAL FINDING:**
- **PRE-ELIXIS WORKING NAME** is a LIVE registered trademark (#5439421)
- **Owner:** Hubbub Brewing LLC (Salida, CO)
- **Class:** 032 (beers, beverages)
- **Registered:** April 3, 2018
- **Risk Level:** MODERATE to HIGH

**Context:**
Hubbub Brewing CHANGED its name FROM "Hubbub" TO "pre-Elixis working name" in 2017 after settling a trademark infringement suit—indicating litigious history and willingness to defend marks.

**Analysis:**
- Different industries (beer vs AI software) = LOW likelihood of confusion
- BUT identical mark creates legal exposure
- Dilution risk if pre-Elixis working name AI becomes famous
- Coexistence agreement: 60% chance if approached professionally
- Opposition outcome: 70% chance of winning (but $10K-50K legal fees)

---

## 🔄 PENDING DECISIONS

### DECISION 1: Company/Product Name

**Status:** User favorites identified — **Prism** and **Lattice**

**Exploration History:**
- ❌ pre-Elixis working name — trademark conflict with brewery
- ❌ PatternSoul, AnimaCraft — rejected by user
- ❌ Short words (Loom, Knot, Echo, etc.) — rejected as "sucking"
- ❌ Prior literary source terms (Knecht, Castalia, Ludus) — not quite right
- ✅ **Prism** — refracts light into spectrum (references into pattern)
- ✅ **Lattice** — interconnected structure, ordered framework

**Next Agent Tasks:**
1. Run USPTO trademark search on "Prism" and "Lattice" in Classes 009 and 042
2. Check domain availability:
   - prism.ai, prism.dev, prism.software
   - lattice.ai, lattice.dev, lattice.software
   - Variations: prismforge, prismlabs, latticework, latticeai
3. Run common law search (GitHub repos, social media handles)
4. Present trademark risk assessment for both names
5. Recommend final name with trademark availability score

**User Preference:** Build something with Prism + Lattice concepts (possibly compound or choose one)

---

### DECISION 2: Trademark Filing Strategy (Blocked on Name Decision)

**Pending:**
- Choose Classes 009 (software) and/or 042 (SaaS)
- Filing basis: 1(b) Intent to Use or 1(a) Actual Use
- Estimated cost: $1,500-3,000 with attorney
- Timeline: 8-12 months to registration

**Cannot proceed until name is finalized.**

---

### DECISION 3: Cross-Domain Synthesis Metaphor Usage

**Status:** Approved for conceptual use, NOT for trademark

**Guidelines Established:**
- ✅ SAFE: Describing the process as cross-domain synthesis
- ✅ SAFE: Using generic "synthesis game" language in internal notes
- ❌ RISKY: Trademarking or foregrounding prior literary phrases
- ❌ RISKY: Using direct literary-source quotes
- ❌ RISKY: Implying endorsement by a literary estate

**Next Agent:** No action needed—guidelines are clear.

---

## 📋 NEXT STEPS FOR PICKING UP AGENT

### Immediate (This Session)

1. **Complete Naming Research**
   - [ ] USPTO TESS search: "PRISM" in Class 009, 042
   - [ ] USPTO TESS search: "LATTICE" in Class 009, 042
   - [ ] Domain availability check for both
   - [ ] Social media handle availability
   - [ ] GitHub org/repo name availability
   - [ ] Common law usage scan

2. **If Prism or Lattice Clear:**
   - [ ] Present trademark risk summary
   - [ ] Recommend final name
   - [ ] Get user confirmation

3. **If Both Have Conflicts:**
   - [ ] Generate 5-10 compound variations (PrismForge, LatticeAI, etc.)
   - [ ] Run searches on compounds
   - [ ] Present alternatives

### Short-Term (Next 24-48 Hours)

4. **After Name Confirmed:**
   - [ ] Order comprehensive trademark search ($500-2000)
   - [ ] Consult with IP attorney for legal opinion
   - [ ] Secure domains immediately
   - [ ] Reserve social media handles
   - [ ] Update all documentation with new name

5. **Rebranding Tasks:**
   - [ ] Rename pre-Elixis working name references in codebase
   - [ ] Update marketing materials
   - [ ] Update GitHub repo
   - [ ] Create new logo/visual identity concepts

### Medium-Term (Next 1-2 Weeks)

6. **Trademark Filing:**
   - [ ] File trademark application (or intent-to-use)
   - [ ] Document current use (screenshots, repos, etc.)
   - [ ] Monitor USPTO for oppositions

7. **Launch Preparation:**
   - [ ] Polish GitHub repo README
   - [ ] Prepare "Show HN" launch
   - [ ] OpenClaw community integration
   - [ ] Content strategy (Pattern Analysis series)

---

## 🔧 TECHNICAL CONTEXT

### Translation Service Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  pre-Elixis working name      │────▶│ Kyanite Translate│────▶│   Ollama    │
│  (Python/Flask) │     │ Service (Port    │     │   (Local    │
│                 │     │ 3111)            │     │   LLM)      │
└─────────────────┘     └──────────────────┘     └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ SQLite Cache│
                        │ (30-day TTL)│
                        └─────────────┘
```

### Key Integration Points

**For pre-Elixis working name:**
```python
from kyanite_translate import KyaniteTranslator
translator = KyaniteTranslator('http://localhost:3111')
result = translator.translate(text, target_lang="es")
```

**For Frontend:**
```javascript
import { KyaniteTranslator } from '/static/js/kyanite-translate.js';
const translator = new KyaniteTranslator('/api/translate-proxy');
```

---

## 📚 KEY DOCUMENTS

| Document | Location | Purpose |
|----------|----------|---------|
| Marketing Strategy | `docs/marketing-pass-pre-elixis-working-name.md` | Positioning, messaging, GTM |
| Trademark Assessment | `docs/trademark-pass-pre-elixis-working-name.md` | Legal risk, name options, filing strategy |
| Integration Guide | `kyanite-translation-service/INTEGRATION.md` | How to use translation service |
| This Handoff | `docs/handoff-current-state.md` | You are here |

---

## 🎯 SUCCESS CRITERIA FOR NEXT AGENT

**Deliverable:** Final company/product name with:
- [ ] Clean USPTO search in Classes 009 and 042
- [ ] Available .ai or .dev domain
- [ ] Available GitHub organization name
- [ ] Risk assessment (< MEDIUM priority)
- [ ] User approval

**Current Working Hypothesis:**
User is leaning toward **Prism** or **Lattice**—verify these are legally and digitally available before proposing alternatives.

---

## 📞 CONTACT / CONTEXT

**Project Owner:** Simon (Kyanite Labs)
**Recent Work:** Translation service shared infrastructure, marketing strategy, trademark risk assessment
**Mood/Context:** User rejected multiple naming rounds; Prism and Lattice are the first genuine enthusiasm. Move quickly on verification to maintain momentum.

**Related Projects:**
- OpenClaw ecosystem (SOUL.md standard)
- Kyanite Translation Service (shared infrastructure)
- Future: Hosted cloud version, enterprise features

---

*End of Handoff Document*
*Next update: After name decision finalized*
