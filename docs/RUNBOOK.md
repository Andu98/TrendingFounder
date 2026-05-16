# Runbook: TrendingFounder Operations

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run daily crawl (all countries, 100 domains each)
python -m src.crawler.run_daily

# Run with fewer domains (faster)
python -m src.crawler.run_daily --limit 50

# Run without LLM enrichment
python -m src.crawler.run_daily --skip-llm

# Run for a specific date
python -m src.crawler.run_daily --date 2026-05-15

# Launch dashboard
streamlit run app/streamlit_app.py
```

## Pause & Resume Crawl

To pause a running crawl gracefully:

```bash
# Create the stop signal file — crawl will pause after the current country finishes
touch .crawl_stop
```

To resume:

```bash
# Just run the crawl again — it will detect the partial run and continue
python -m src.crawler.run_daily
```

The run status is saved as "partial" and all already-processed countries are skipped on resume.

## Daily Operations

### Morning: Check crawl status

1. Open Streamlit dashboard → Stats page
2. Check "Countries Crawled" metric
3. Review "Failed countries" table
4. If crawl is stuck (status = "running" for > 2 hours), investigate logs

### Midday: Review domains

1. Open Today page
2. Sort by Score (desc)
3. Review top domains, mark as OK / Exists / Bad
4. Add comments for interesting finds

### Evening: Verify completion

1. Check Stats page for completed status
2. Verify new_domains_count matches expectations
3. Check LLM processed count

## Troubleshooting

### Crawl stuck in "running" state

```bash
# Check logs
tail -f logs/app.log

# If LM Studio is not running, restart it
# If Cloudflare API is rate-limited, wait 5 minutes

# To force-reset a stuck run, use Supabase SQL console:
# UPDATE crawl_runs SET status = 'failed', finished_at = NOW()
# WHERE run_date = '2026-05-15' AND status = 'running';
```

### LLM enrichment failing

1. Verify LM Studio is running on `http://localhost:1234`
2. Check the model is loaded in LM Studio
3. Test manually: `curl http://localhost:1234/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen/qwen2.5-vl-7b","messages":[{"role":"user","content":"hello"}]}'`
4. If LM Studio is unavailable, re-run with `--skip-llm`

### Cloudflare API rate limited (429)

The client automatically retries with exponential backoff. If you see persistent 429 errors:

1. Check if another process is using the same API token
2. Reduce `--limit` to decrease total requests
3. Wait 5 minutes for the rate limit window to reset

### Supabase connection errors

1. Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`
2. Check Supabase project status at https://app.supabase.com
3. Verify network connectivity: `curl -I $SUPABASE_URL/rest/v1/`

## Database Maintenance

### Clean up old crawl runs (keep last 30 days)

```sql
DELETE FROM crawl_runs
WHERE run_date < CURRENT_DATE - INTERVAL '30 days';
```

### Reset review status for re-triage

```sql
UPDATE domains
SET review_status = 'pending', reviewed_at = NULL, reviewed_by = NULL
WHERE review_status = 'ok';
```

### Find domains with failed LLM enrichment

```sql
SELECT normalized_domain, llm_risk_notes
FROM domains
WHERE llm_summary LIKE 'LLM enrichment failed%'
ORDER BY first_seen_date DESC;
```

## Monitoring

### Key metrics to watch

| Metric | Normal | Alert |
|---|---|---|
| Countries crawled | > 180 / 210 | < 150 |
| New domains per day | 50-500 | < 10 or > 2000 |
| LLM success rate | > 95% | < 80% |
| Avg response time (Cloudflare) | < 2s | > 5s |
| Failed countries | 0-5 | > 20 |

## Backup

Supabase handles automated backups. For manual backup:

```bash
# Export domains table
pg_dump -h db.<project-ref>.supabase.co -U postgres -t domains trendingfounder > backup_domains.sql
```

## Contact

- Project docs: `docs/PLAN.md`
- API contracts: `docs/API_CONTRACTS.md`
- Decisions: `docs/DECISIONS.md`
