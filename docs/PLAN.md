# Extended Plan: Global Trending Sites Discovery Platform

## 1. Obiectivul produsului

Construim o platformă internă care descoperă zilnic domenii populare sau în creștere la nivel global, folosind Cloudflare Radar, apoi le deduplicatează, le îmbogățește cu un sumar LLM local și le pune într-un dashboard simplu, rapid și mobile-friendly.

Scopul nu este să clonezi site-uri, ci să descoperi pattern-uri: aplicații, platforme, nișe, mecanici de monetizare, trenduri geografice și idei care pot fi adaptate pentru România.

Platforma trebuie să răspundă rapid la întrebările:

„Ce site-uri noi au explodat azi?”

„Care par interesante pentru mine?”

„Pe care le-am analizat deja?”

„Câte țări au fost procesate azi?”

„Ce domenii apar în mai multe țări, fără să-mi dubleze lista?”

---

## 2. Stack recomandat

Pentru MVP:

| Componentă       | Alegere                                                        |
| ---------------- | -------------------------------------------------------------- |
| Limbaj           | Python                                                         |
| UI               | Streamlit                                                      |
| DB               | Supabase / PostgreSQL                                          |
| LLM local        | LM Studio cu model Qwen                                        |
| API data source  | Cloudflare Radar API                                           |
| Scheduling local | cron / Task Scheduler / GitHub Actions self-hosted, mai târziu |
| Config           | `.env` + `pydantic-settings`                                   |
| Validare date    | Pydantic                                                       |
| HTTP client      | `httpx`                                                        |
| Logging          | `loguru` sau logging standard                                  |
| Teste            | pytest                                                         |
| Code style       | ruff + black                                                   |

LM Studio are endpoint-uri OpenAI-compatible și permite folosirea unui client OpenAI-style prin schimbarea `base_url` către `http://localhost:1234/v1`, deci integrarea cu un model local este simplă. ([LM Studio][2])

---

## 3. Corecții importante față de planul Gemini

### 3.1 Nu stoca totul doar în `domains`

Nu vrem duplicate în UI, dar vrem istoric. Deci avem nevoie de două concepte:

| Concept               | Rol                                                           |
| --------------------- | ------------------------------------------------------------- |
| `domains`             | un singur rând per domeniu unic                               |
| `domain_observations` | fiecare apariție a domeniului într-o zi, țară și ranking type |

Așa poți avea `fanvue.com` o singură dată în UI, dar știi că a apărut azi în US, DE și RO, iar săptămâna trecută în UK.

### 3.2 Nu rula LLM pe duplicate

LLM rulează doar când `domains.normalized_domain` nu există deja. Dacă domeniul există, se inserează doar o nouă observație în `domain_observations`.

### 3.3 Nu confunda scorul domeniului cu scorul apariției

Un domeniu are sumar stabil. Dar scorul poate varia zilnic în funcție de țară, ranking type și poziție.

Deci:

| Scor                | Unde se ține          | De ce                                            |
| ------------------- | --------------------- | ------------------------------------------------ |
| `initial_score`     | `domains`             | scorul primei descoperiri                        |
| `observation_score` | `domain_observations` | scorul apariției într-o zi / țară / ranking type |
| `best_score_today`  | view SQL / query      | pentru dashboard                                 |
| `best_score_week`   | view SQL / query      | pentru dashboard                                 |

Asta rezolvă elegant problema ta: nu consumi LLM de două ori, dar scoring-ul zilnic rămâne viu.

---

## 4. Cloudflare Radar API rules

Agentul trebuie să trateze Cloudflare API ca sursă strictă, nu ca poveste de han digital.

### 4.1 Documentare obligatorie

Înainte să implementeze sau să modifice orice apel Cloudflare, agentul trebuie să verifice:

1. endpoint path;
2. query parameters;
3. autentificare;
4. rate limits;
5. response shape;
6. dacă există câmpuri opționale sau doar pentru anumite ranking types.

Cloudflare oferă documentație Markdown pentru agenți, iar pagina HTML chiar recomandă folosirea versiunii Markdown ca să nu se irosească context. ([Cloudflare Docs][3])

### 4.2 Endpoint-uri Cloudflare folosite în MVP

| Scop                  | Endpoint                  |
| --------------------- | ------------------------- |
| Listă țări/geolocații | `GET /radar/geolocations` |
| Domenii top/trending  | `GET /radar/ranking/top`  |

`/radar/geolocations` returnează geolocații cu tipuri precum `CONTINENT`, `COUNTRY`, `ADM1`, iar query-ul acceptă `format`, `geoId`, `limit`, `location`, `offset`. Pentru proiect, agentul trebuie să filtreze doar geolocațiile de tip `COUNTRY`. ([Cloudflare Docs][4])

`/radar/ranking/top` returnează `result.meta` și `result.top_0`, iar fiecare item din `top_0` poate conține `categories`, `domain`, `rank`, și `pctRankChange`; `pctRankChange` este disponibil doar pentru ranking-uri de tip trending. ([Cloudflare Docs][1])

### 4.3 Parametri acceptați pentru ranking

Pentru fiecare țară:

```text
location=<country_alpha_2>
rankingType=TRENDING_RISE | TRENDING_STEADY | POPULAR
limit=100
format=JSON
date=<optional date>
```

Recomandare MVP:

| Ranking type      | Utilizare                                                                      |
| ----------------- | ------------------------------------------------------------------------------ |
| `TRENDING_RISE`   | principal, pentru descoperiri noi                                              |
| `TRENDING_STEADY` | secundar, pentru trenduri mai stabile                                          |
| `POPULAR`         | opțional, mai mult pentru context, dar va produce mulți giganți deja cunoscuți |

### 4.4 Rate limits

Cloudflare documentează limita globală API de `1200 requests / 5 minutes` per user/account token și `200 requests / second` per IP. Dacă se depășește limita, API-ul poate returna `HTTP 429` și blochează apelurile pentru următoarele 5 minute. ([Cloudflare Docs][3])

Implicație practică: pentru 200 de țări × 2 ranking types = aproximativ 400 request-uri pe run, ești confortabil în limită. Totuși, agentul trebuie să implementeze throttling și retry pe `429`, citind header-ele `Ratelimit`, `Ratelimit-Policy` și `retry-after` când există. ([Cloudflare Docs][3])

---

## 5. Arhitectură generală

Fluxul zilnic trebuie să fie:

```text
Scheduler
  -> create crawl_run
  -> fetch geolocations
  -> for each country:
       -> fetch TRENDING_RISE
       -> fetch TRENDING_STEADY
       -> normalize domains
       -> insert observations
       -> detect new domains
       -> run LLM only for new domains
       -> score observations
       -> update run progress
  -> mark crawl_run completed
```

Separat:

```text
Streamlit UI
  -> reads views from Supabase
  -> opens one main dashboard screen
  -> top navigation: Collected Data / Reports
  -> allows status update: OK / Exists / Bad
  -> allows comments popover per domain
```

---

## 6. Structura proiectului

Aș cere agentului să creeze structura asta:

```text
TrendingFounder/
  app/
    streamlit_app.py
    data_loader.py
    components/
      domain_table.py
      metrics_cards.py
      filters.py
      comments_dialog.py  # legacy/reference only
    pages/
      1_Today.py          # legacy/reference only
      2_This_Week.py      # legacy/reference only
      3_Stats.py          # legacy/reference only

  src/
    config/
      settings.py
      constants.py

    cloudflare/
      client.py
      radar_service.py
      schemas.py

    domains/
      normalize.py
      dedupe.py
      scoring.py

    llm/
      lmstudio_client.py
      prompts.py
      schemas.py

    db/
      supabase_client.py
      repositories.py
      queries.py

    crawler/
      run_daily.py
      orchestrator.py
      progress.py

    utils/
      logging.py

  supabase/
    schemas/
      001_core.sql
      002_views.sql
      003_rls.sql

  docs/
    AGENTS.md
    PLAN.md
    TASKS.md
    DECISIONS.md
    CHANGELOG.md
    API_CONTRACTS.md
    RUNBOOK.md
    PROMPTS.md

  tests/
    test_cloudflare_client.py
    test_cloudflare_radar_service.py
    test_cloudflare_schemas.py
    test_constants.py
    test_crawler.py
    test_db_repositories.py
    test_domain_dedupe.py
    test_domain_normalize.py
    test_llm_enrichment.py
    test_llm_prompts.py
    test_llm_schemas.py
    test_scoring.py
    test_settings.py
    test_ui_metrics.py

  .env.example
  pyproject.toml
  README.md
```

Supabase declarative schemas sunt potrivite aici: definești starea dorită în fișiere SQL și folosești diff/migrations generate, în loc să împrăștii modificări manuale prin fișiere de migrare. ([Supabase][5])

---

## 7. Model de date recomandat

### 7.1 `domains`

Un rând per domeniu unic.

Câmpuri:

```text
id
normalized_domain              unique, ex: "fanvue.com"
display_url                    ex: "https://fanvue.com"
first_seen_at                  timestamptz
first_seen_date                date
first_country_code             text
first_country_name             text
first_ranking_type             text
llm_summary                    text
llm_category                   text
llm_business_model             text
llm_target_users               text
llm_localization_angle         text
llm_risk_notes                 text
initial_score                  numeric
latest_best_score              numeric
review_status                 pending | ok | exists | bad
reviewed_at                    timestamptz nullable
reviewed_by                    text nullable
created_at                     timestamptz
updated_at                     timestamptz
```

### 7.2 `domain_observations`

Un rând per apariție într-o țară / zi / ranking type.

```text
id
domain_id                      FK domains.id
crawl_run_id                   FK crawl_runs.id
observed_date                  date
observed_at                    timestamptz
country_code                   text
country_name                   text
ranking_type                   popular | trending_rise | trending_steady
rank                           integer
pct_rank_change                numeric nullable
categories                     jsonb
observation_score              numeric
raw_payload                    jsonb
created_at                     timestamptz
```

Constrângere unică:

```text
unique(domain_id, observed_date, country_code, ranking_type)
```

### 7.3 `crawl_runs`

Pentru pagina de progres.

```text
id
run_date                       date
status                         pending | running | completed | failed | partial
started_at                     timestamptz
finished_at                    timestamptz nullable
countries_total                integer
countries_completed            integer
countries_failed               integer
requests_total                 integer
requests_failed                integer
new_domains_count              integer
duplicate_domains_count        integer
llm_processed_count            integer
llm_skipped_count              integer
error_message                  text nullable
created_at                     timestamptz
updated_at                     timestamptz
```

### 7.4 `crawl_country_status`

Pentru progres granular.

```text
id
crawl_run_id
country_code
country_name
status                         pending | running | completed | failed
started_at
finished_at
error_message
items_found
new_domains
duplicate_domains
```

### 7.5 `domain_comments`

```text
id
domain_id
author_name
message
created_at                     timestamptz
```

Important: în DB se salvează UTC cu `timestamptz`; în UI se afișează Europe/Bucharest.

---

## 8. Deduplicare

Regula principală:

```text
normalized_domain este cheia globală.
```

Normalizarea trebuie să facă:

```text
https://www.Example.com/path?x=1 -> example.com
http://m.example.com -> example.com, doar dacă decidem explicit că m. este subdomeniu mobil
subdomain.example.com -> păstrat sau mapat după regulă
```

Recomandare: pentru MVP deduplici la registrable domain, folosind o librărie de tip public suffix, nu doar split pe punct. Altfel vei strica domenii gen `co.uk`.

Regulă de business:

| Situație                                          | Acțiune                                                   |
| ------------------------------------------------- | --------------------------------------------------------- |
| Domeniu nou                                       | insert în `domains`, rulează LLM, calculează scor inițial |
| Domeniu existent, țară nouă azi                   | insert în `domain_observations`, nu rula LLM              |
| Domeniu existent, altă zi                         | insert observation, nu rula LLM                           |
| Domeniu deja observat azi în aceeași țară/ranking | skip / upsert                                             |

UI-ul afișează un singur rând per domeniu, dar poate arăta:

```text
Popular also in: US, DE, FR, BR
Seen today in 7 countries
Seen this week in 18 countries
```

---

## 9. Enrichment LLM

### 9.1 Ce trimiți către LLM

Nu trimite tot HTML-ul paginii. E scump și gălăgios.

Pentru MVP, trimite:

```text
domain
title dacă poate fi extras
meta description
Cloudflare categories
country where first seen
ranking type
rank
pctRankChange
homepage text extras scurt, max 2-4 KB, doar dacă fetch-ul e rapid
```

Qwen2.5-VL folosește-l doar dacă faci screenshot sau analiză vizuală. Dacă nu faci screenshot, un model text este suficient.

### 9.2 Output LLM strict JSON

Agentul trebuie să ceară output JSON valid:

```json
{
  "summary": "Short explanation of what this site does.",
  "category": "AI | SaaS | Ecommerce | Community | Entertainment | Finance | Education | Other",
  "business_model": "ads | subscription | marketplace | ecommerce | lead generation | unknown",
  "target_users": "short description",
  "localization_angle": "how this could be adapted for Romania",
  "risk_notes": "legal, adult, gambling, low-value, scammy, infrastructure, etc.",
  "novelty": 1,
  "idea_potential": 1,
  "confidence": 1
}
```

Scorurile 1-5.

Dacă LLM returnează JSON invalid, agentul trebuie:

1. să salveze eroarea;
2. să marcheze domeniul ca `llm_status=failed`;
3. să nu blocheze tot crawl-ul.

---

## 10. Scoring engine

Scorul trebuie să fie explicabil, nu magie cu pălărie neagră.

Propunere MVP:

```text
score =
  base_score
  + ranking_type_bonus
  + rank_bonus
  + pct_rank_change_bonus
  + multi_country_bonus
  + category_bonus
  + novelty_bonus
  + llm_potential_bonus
  - known_giant_penalty
  - risky_category_penalty
  - already_reviewed_penalty
```

### 10.1 Valori inițiale

```text
base_score = 20

ranking_type_bonus:
  TRENDING_RISE = +30
  TRENDING_STEADY = +18
  POPULAR = +5

rank_bonus:
  rank 1-10 = +20
  rank 11-25 = +12
  rank 26-50 = +7
  rank 51-100 = +3

pct_rank_change_bonus:
  if pctRankChange exists:
    min(20, pctRankChange / 5)

multi_country_bonus:
  +2 per country seen today, max +20

category_bonus:
  AI / SaaS / Productivity / Education / Developer Tools = +15
  Ecommerce / Marketplace / Finance = +10
  Entertainment / Games / Social = +5
  Adult / Gambling / Piracy / Scam-risk = -30

novelty_bonus:
  first_seen_today = +20
  first_seen_this_week = +8
  older = 0

llm_potential_bonus:
  idea_potential 1-5 => +0, +5, +10, +15, +20

known_giant_penalty:
  google, youtube, facebook, amazon, microsoft, apple, cloudflare etc. = -50

already_reviewed_penalty:
  ok / exists / bad = -100 for default triage views
```

Important: scoring-ul trebuie calculat pentru observații, apoi agregat în UI.

Pentru “Today”:

```text
best_score_today = max(observation_score for today)
```

Pentru “This week”:

```text
best_score_week = max(observation_score from last 7 days)
```

---

## 11. UI Streamlit

Dashboard-ul principal este o singură aplicație Streamlit în `app/streamlit_app.py`, cu top navigation intern. Fișierele vechi din `app/pages/` pot rămâne ca referință, dar nu sunt UX-ul principal.

### 11.1 Tab Collected Data

Titlu:

```text
Collected Data
```

Conținut:

```text
Domain link
Category pill
Business model pill
Score badge
Summary
First country
Status checkboxes
Comments popover
Details expander
```

Comportament:

* date range default: Today;
* sort default: `best_score_today desc`;
* filtre: date range / status checkboxes / category / show reviewed;
* paginare server-side: 50 rows default, opțiuni 10 / 25 / 50 / 100;
* datele principale vin prin RPC-ul Supabase `get_domains_for_range(...)`, care agregă, filtrează, sortează și aplică `LIMIT/OFFSET` în DB;
* optional sort: score / newest / country count;
* click pe site deschide URL;
* statusurile sunt exclusive prin `review_status`;
* schimbarea statusului se salvează prin repository-ul existent;
* comentariile se văd și se adaugă în popover per domeniu.

Detalii care stau în expander:

```text
Countries found in
Ranking types
Target users
Localization angle
Risk notes
First seen
First seen in range
Last seen in range
Times observed
Initial score
```

### 11.2 Tab Reports

Înlocuiește vechea pagină Stats ca suprafață principală de raportare.

```text
Countries crawled today: 137 / 210
Daily crawl progress: 65%
New domains today
Duplicates skipped today
LLM processed today
LLM skipped due to dedupe
Marked today
Marked total
High score today > 80
Failed countries
```

Progress bar:

```text
countries_completed / countries_total
```

Mai adaugă o secțiune:

```text
Today's crawl status by country
```

cu tabel mic:

```text
Country | Status | Items found | New | Duplicates | Error
```

### 11.3 Theme

Dashboard-ul are switcher light/dark în navbar. CSS-ul stă centralizat în `streamlit_app.py` prin variabile de temă.

### 11.4 Comments modal

Cerința ta cu modal e bună.

Comportament:

* buton `Comments (3)`;
* deschide modal;
* listează comentarii existente;
* afișează ora în Europe/Bucharest;
* input `Name`;
* input `Message`;
* buton `Add comment`.

---

## 12. Agent files obligatorii

### 12.1 `AGENTS.md`

Trebuie să conțină:

```text
Role of agent:
- Build carefully.
- Do not invent Cloudflare params.
- Update TASKS.md after each completed task.
- Update DECISIONS.md when making architecture choices.
- Update CHANGELOG.md after every meaningful code change.
- Run tests after changing domain normalization, scoring, DB mappings, Cloudflare parsing.
- Never expose API tokens.
- Prefer small, reviewable changes.
```

### 12.2 `API_CONTRACTS.md`

Aici agentul va nota explicit:

```text
Cloudflare endpoint:
GET /radar/ranking/top

Verified params:
- date
- domainCategory
- format
- limit
- location
- name
- rankingType

Ranking values:
- POPULAR
- TRENDING_RISE
- TRENDING_STEADY

Response:
- result.meta
- result.top_0[]
- top_0[].domain
- top_0[].rank
- top_0[].pctRankChange only for TRENDING rankings
```

### 12.3 `DECISIONS.md`

ADR-uri minime:

```text
ADR-001: Use domains + domain_observations instead of one flat table
ADR-002: Run LLM only once per normalized domain
ADR-003: Store timestamps in UTC, display Europe/Bucharest in UI
ADR-004: Store review status as enum, not 3 booleans
ADR-005: Use Cloudflare Markdown docs as API source of truth
ADR-006: Use Streamlit for MVP despite mobile limitations
```

### 12.4 `TASKS.md`

Inițial:

```text
[ ] Create project skeleton
[ ] Add settings and .env.example
[ ] Add Cloudflare client
[ ] Verify Radar endpoints from official docs
[ ] Implement geolocation fetch
[ ] Implement ranking fetch
[ ] Add response schemas
[ ] Add domain normalization
[ ] Add Supabase schema
[ ] Add repositories
[ ] Add daily crawl run orchestration
[ ] Add LM Studio client
[ ] Add LLM enrichment prompt
[ ] Add scoring engine
[ ] Add Streamlit main dashboard
[ ] Add Collected Data tab
[ ] Add Reports tab
[ ] Add comments popover
[ ] Add tests
[ ] Add runbook
```

---

## 13. MVP phases

### Phase 1: Foundation

Scop: proiectul pornește curat.

Livrabile:

```text
project skeleton
.env.example
settings.py
logging
README
AGENTS.md
PLAN.md
TASKS.md
DECISIONS.md
CHANGELOG.md
```

### Phase 2: Cloudflare ingestion

Scop: să poți extrage date raw.

Livrabile:

```text
Cloudflare client
get_geolocations()
get_top_domains(location, rankingType, limit)
Pydantic response models
basic tests
raw payload logging on failure
```

### Phase 3: Supabase schema

Scop: persistență corectă.

Livrabile:

```text
domains
domain_observations
crawl_runs
crawl_country_status
domain_comments
views for today/week/stats
```

### Phase 4: Deduplication

Scop: fără duplicate în UI, dar cu istoric complet.

Livrabile:

```text
normalize_domain()
upsert_domain()
insert_observation()
skip LLM if domain exists
```

### Phase 5: LLM enrichment

Scop: sumar doar pentru domenii noi.

Livrabile:

```text
LM Studio client
strict JSON prompt
parse/validate response
save summary/category/business_model
fallback on LLM error
```

### Phase 6: Scoring

Scop: ranking util pentru triere.

Livrabile:

```text
score_observation()
known giants penalty list
category weights config
tests for scoring
```

### Phase 7: Streamlit UI

Scop: dashboard folosibil pe mobil.

Livrabile:

```text
single main Streamlit app
Collected Data tab
Reports tab
status update
comments popover
light/dark theme switcher
basic responsive layout
```

### Phase 8: Hardening

Scop: să nu crape după 3 zile.

Livrabile:

```text
retry/backoff
429 handling
run resume
partial failure support
tests
runbook
```

---

## 14. Reguli stricte pentru agent

Aș pune asta aproape mot-à-mot în `AGENTS.md`:

```text
Do not guess API parameters.

Before changing Cloudflare code:
1. read Cloudflare Radar llms.txt or endpoint markdown docs;
2. verify endpoint path;
3. verify query params;
4. verify auth;
5. verify response shape;
6. update API_CONTRACTS.md.

After every code change:
1. update TASKS.md;
2. update CHANGELOG.md;
3. if architecture changed, update DECISIONS.md;
4. run relevant tests.

Never run LLM enrichment for an already known normalized_domain.

Never create duplicate domain rows.

Always create observations for repeated appearances.

Store timestamps in UTC. Convert to Europe/Bucharest only for display.

Use review_status as the source of truth. UI controls are only presentation.
```

---

## 15. Recomandarea mea finală

Pentru MVP, nu încerca din prima “toate țările + POPULAR + RISE + STEADY + homepage crawling + screenshots”. E prea mult, o mică junglă cu cravată.

Fă prima versiune așa:

```text
Countries: toate țările Cloudflare de tip COUNTRY
Ranking types: TRENDING_RISE + TRENDING_STEADY
Limit: 50 sau 100
LLM: doar domenii noi
UI: single Streamlit dashboard with Collected Data + Reports tabs
Review: pending / ok / exists / bad
Comments: simplu
```

După ce merge stabil 3-5 zile, adaugi:

```text
POPULAR ca sursă secundară
homepage metadata fetch
screenshot/VL analysis pentru domenii cu scor mare
export CSV
notificări pentru scor > 85
blacklist/whitelist custom categories
```

Cel mai important design choice: **un rând unic în UI, dar observații multiple în DB**. Asta îți păstrează interfața curată, nu arde LLM-ul inutil și totuși îți dă date istorice bune pentru scoring.

[1]: https://developers.cloudflare.com/api/resources/radar/subresources/ranking/methods/top/index.md "developers.cloudflare.com"
[2]: https://lmstudio.ai/docs/developer/openai-compat?utm_source=chatgpt.com "OpenAI Compatibility Endpoints"
[3]: https://developers.cloudflare.com/fundamentals/api/reference/limits/ "Rate limits · Cloudflare Fundamentals docs"
[4]: https://developers.cloudflare.com/api/resources/radar/subresources/geolocations/methods/list/index.md "developers.cloudflare.com"
[5]: https://supabase.com/docs/guides/local-development/declarative-database-schemas?utm_source=chatgpt.com "Declarative database schemas | Supabase Docs"
[6]: https://docs.streamlit.io/develop/api-reference/data/st.data_editor?utm_source=chatgpt.com "st.data_editor - Streamlit Docs"
