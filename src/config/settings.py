from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    cloudflare_api_token: str = Field(
        ...,
        description="Cloudflare API token with Radar read access.",
    )

    supabase_url: str = Field(
        default="",
        description="Supabase project URL.",
    )

    supabase_anon_key: str = Field(
        default="",
        description="Supabase anon (publishable) key.",
    )

    supabase_service_role_key: str = Field(
        default="",
        description="Supabase service role key (server-side only).",
    )

    lmstudio_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="OpenAI-compatible LLM base URL (e.g. NVIDIA NIM or LM Studio).",
    )

    lmstudio_model: str = Field(
        default="meta/llama-3.1-8b-instruct",
        description="Model name to use in LLM requests.",
    )

    nvidia_api_key: str | None = Field(
        default=None,
        description="Bearer token for the LLM endpoint. Required when calling NVIDIA NIM directly.",
    )

    github_token: str | None = Field(
        default=None,
        description="Optional GitHub token for authenticated repository search API requests.",
    )

    app_timezone: str = Field(
        default="Europe/Bucharest",
        description="Timezone for UI display conversions.",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )


settings = Settings()
