from datetime import date, datetime

from supabase import Client

from src.config.constants import CrawlRunStatus, ReviewStatus
from src.db.supabase_client import get_supabase_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DomainRepository:
    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    def upsert_domain(
        self,
        normalized_domain: str,
        display_url: str | None = None,
        first_seen_at: datetime | None = None,
        first_seen_date: date | None = None,
        first_country_code: str | None = None,
        first_country_name: str | None = None,
        first_ranking_type: str | None = None,
        initial_score: float | None = None,
    ) -> dict:
        now = datetime.now()
        row = {
            "normalized_domain": normalized_domain,
            "display_url": display_url,
            "first_seen_at": first_seen_at.isoformat() if first_seen_at else now.isoformat(),
            "first_seen_date": first_seen_date.isoformat() if first_seen_date else now.date().isoformat(),
            "first_country_code": first_country_code,
            "first_country_name": first_country_name,
            "first_ranking_type": first_ranking_type,
            "initial_score": initial_score,
            "review_status": ReviewStatus.PENDING.value,
        }

        result = self._client.table("domains").upsert(row, on_conflict="normalized_domain").execute()

        if result.data:
            logger.debug(f"Upserted domain: {normalized_domain}")
        return result.data[0] if result.data else {}

    def get_by_normalized_domain(self, normalized_domain: str) -> dict | None:
        result = self._client.table("domains").select("*").eq("normalized_domain", normalized_domain).execute()
        return result.data[0] if result.data else None

    def update_review_status(
        self,
        domain_id: str,
        status: ReviewStatus,
        reviewed_by: str | None = None,
    ) -> dict:
        row = {
            "review_status": status.value,
            "reviewed_at": datetime.now().isoformat(),
        }
        if reviewed_by:
            row["reviewed_by"] = reviewed_by

        result = self._client.table("domains").update(row).eq("id", domain_id).execute()
        return result.data[0] if result.data else {}

    def update_llm_fields(
        self,
        domain_id: str,
        summary: str,
        category: str,
        business_model: str,
        target_users: str,
        localization_angle: str,
        risk_notes: str,
    ) -> dict:
        row = {
            "llm_summary": summary,
            "llm_category": category,
            "llm_business_model": business_model,
            "llm_target_users": target_users,
            "llm_localization_angle": localization_angle,
            "llm_risk_notes": risk_notes,
        }

        result = self._client.table("domains").update(row).eq("id", domain_id).execute()
        return result.data[0] if result.data else {}


class ObservationRepository:
    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    def insert_observation(
        self,
        domain_id: str,
        crawl_run_id: str | None,
        observed_date: date,
        country_code: str,
        country_name: str,
        ranking_type: str,
        rank: int,
        pct_rank_change: float | None = None,
        categories: list | None = None,
        observation_score: float | None = None,
        raw_payload: dict | None = None,
    ) -> dict:
        row = {
            "domain_id": domain_id,
            "crawl_run_id": crawl_run_id,
            "observed_date": observed_date.isoformat(),
            "country_code": country_code,
            "country_name": country_name,
            "ranking_type": ranking_type,
            "rank": rank,
            "pct_rank_change": pct_rank_change,
            "categories": categories or [],
            "observation_score": observation_score,
            "raw_payload": raw_payload,
        }

        result = (
            self._client.table("domain_observations")
            .upsert(row, on_conflict="domain_id,observed_date,country_code,ranking_type")
            .execute()
        )

        if result.data:
            logger.debug(f"Inserted observation for {domain_id} in {country_code}/{ranking_type}")
        return result.data[0] if result.data else {}


class CrawlRunRepository:
    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    def create_run(self, run_date: date | None = None) -> dict:
        today = run_date or date.today()
        row = {
            "run_date": today.isoformat(),
            "status": CrawlRunStatus.RUNNING.value,
            "started_at": datetime.now().isoformat(),
        }

        result = self._client.table("crawl_runs").insert(row).execute()
        run = result.data[0] if result.data else {}
        logger.info(f"Created crawl_run {run.get('id')} for {today}")
        return run

    def update_progress(
        self,
        run_id: str,
        countries_total: int | None = None,
        countries_completed: int | None = None,
        countries_failed: int | None = None,
        requests_total: int | None = None,
        requests_failed: int | None = None,
        new_domains_count: int | None = None,
        duplicate_domains_count: int | None = None,
        llm_processed_count: int | None = None,
        llm_skipped_count: int | None = None,
    ) -> dict:
        row = {
            k: v
            for k, v in {
                "countries_total": countries_total,
                "countries_completed": countries_completed,
                "countries_failed": countries_failed,
                "requests_total": requests_total,
                "requests_failed": requests_failed,
                "new_domains_count": new_domains_count,
                "duplicate_domains_count": duplicate_domains_count,
                "llm_processed_count": llm_processed_count,
                "llm_skipped_count": llm_skipped_count,
            }.items()
            if v is not None
        }

        if not row:
            return {}

        result = self._client.table("crawl_runs").update(row).eq("id", run_id).execute()
        return result.data[0] if result.data else {}

    def complete_run(
        self,
        run_id: str,
        status: CrawlRunStatus = CrawlRunStatus.COMPLETED,
        error_message: str | None = None,
    ) -> dict:
        row = {
            "status": status.value,
            "finished_at": datetime.now().isoformat(),
        }
        if error_message:
            row["error_message"] = error_message

        result = self._client.table("crawl_runs").update(row).eq("id", run_id).execute()
        return result.data[0] if result.data else {}

    def get_today_run(self) -> dict | None:
        result = self._client.table("crawl_runs").select("*").eq("run_date", date.today().isoformat()).execute()
        return result.data[0] if result.data else None

    def get_run_by_id(self, run_id: str) -> dict | None:
        result = self._client.table("crawl_runs").select("*").eq("id", run_id).execute()
        return result.data[0] if result.data else None


class CrawlCountryStatusRepository:
    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    def get_country_statuses_for_run(self, crawl_run_id: str) -> list[dict]:
        result = (
            self._client.table("crawl_country_status")
            .select("country_code,country_name,status")
            .eq("crawl_run_id", crawl_run_id)
            .execute()
        )
        return result.data or []

    def upsert_country_status(
        self,
        crawl_run_id: str,
        country_code: str,
        country_name: str,
        status: str,
        items_found: int = 0,
        new_domains: int = 0,
        duplicate_domains: int = 0,
        error_message: str | None = None,
    ) -> dict:
        row = {
            "crawl_run_id": crawl_run_id,
            "country_code": country_code,
            "country_name": country_name,
            "status": status,
            "items_found": items_found,
            "new_domains": new_domains,
            "duplicate_domains": duplicate_domains,
        }
        if error_message:
            row["error_message"] = error_message

        result = (
            self._client.table("crawl_country_status").upsert(row, on_conflict="crawl_run_id,country_code").execute()
        )
        return result.data[0] if result.data else {}


class CommentRepository:
    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    def add_comment(self, domain_id: str, author_name: str, message: str) -> dict:
        row = {
            "domain_id": domain_id,
            "author_name": author_name,
            "message": message,
        }

        result = self._client.table("domain_comments").insert(row).execute()
        return result.data[0] if result.data else {}

    def get_comments(self, domain_id: str) -> list[dict]:
        result = (
            self._client.table("domain_comments")
            .select("*")
            .eq("domain_id", domain_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
