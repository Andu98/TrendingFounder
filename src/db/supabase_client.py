from supabase import Client, create_client

from src.config.settings import settings


def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
