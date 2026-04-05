from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class AppSettings:
    ledger_backend: Literal["memory", "json", "postgres"]
    ledger_path: Path
    object_store_path: Path
    postgres_dsn: str | None
    postgres_schema: str
    auth_mode: Literal["dev_headers", "jwt", "mixed"]
    auth_jwt_secret: str | None
    auth_oidc_discovery_url: str | None
    auth_jwks_url: str | None
    auth_jwt_algorithms: tuple[str, ...]
    auth_oidc_cache_ttl_seconds: int
    auth_jwks_cache_ttl_seconds: int
    auth_jwks_timeout_seconds: float
    auth_jwt_issuer: str | None
    auth_jwt_audience: str | None
    auth_principal_claim: str
    auth_tenant_claim: str
    auth_project_role_claim: str
    auth_scopes_claim: str
    auth_jti_claim: str
    auth_require_jti: bool
    auth_revoked_jti_list: tuple[str, ...]
    auth_introspection_url: str | None
    auth_introspection_client_id: str | None
    auth_introspection_client_secret: str | None
    auth_introspection_token_type_hint: str | None
    auth_introspection_timeout_seconds: float
    ncbi_enabled: bool
    ncbi_base_url: str
    pmc_oa_base_url: str
    ncbi_tool: str
    ncbi_email: str | None
    ncbi_api_key: str | None
    ncbi_cache_ttl_hours: int
    ncbi_rate_limit_per_sec: float | None
    ncbi_timeout_seconds: float


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or default


@lru_cache
def get_settings() -> AppSettings:
    ledger_backend = os.getenv("DROS_LEDGER_BACKEND", "memory").strip().lower() or "memory"
    if ledger_backend not in {"memory", "json", "postgres"}:
        raise ValueError(f"unsupported DROS_LEDGER_BACKEND: {ledger_backend}")

    ledger_path_raw = os.getenv("DROS_LEDGER_PATH", str(ROOT / ".dros" / "ledger.json"))
    object_store_path_raw = os.getenv("DROS_OBJECT_STORE_PATH", str(ROOT / ".dros" / "object-store"))
    postgres_dsn = os.getenv("DROS_POSTGRES_DSN", "").strip() or None
    postgres_schema = os.getenv("DROS_POSTGRES_SCHEMA", "dr_os_dev").strip() or "dr_os_dev"
    auth_mode = os.getenv("DROS_AUTH_MODE", "dev_headers").strip().lower() or "dev_headers"
    if auth_mode not in {"dev_headers", "jwt", "mixed"}:
        raise ValueError(f"unsupported DROS_AUTH_MODE: {auth_mode}")
    auth_jwt_secret = os.getenv("DROS_AUTH_JWT_SECRET", "").strip() or None
    auth_oidc_discovery_url = os.getenv("DROS_AUTH_OIDC_DISCOVERY_URL", "").strip() or None
    auth_jwks_url = os.getenv("DROS_AUTH_JWKS_URL", "").strip() or None
    auth_jwt_algorithms = _env_list(
        "DROS_AUTH_JWT_ALGORITHMS",
        ("RS256",) if auth_jwks_url or auth_oidc_discovery_url else ("HS256",),
    )
    auth_oidc_cache_ttl_seconds = int(os.getenv("DROS_AUTH_OIDC_CACHE_TTL_SECONDS", "300").strip() or "300")
    auth_jwks_cache_ttl_seconds = int(os.getenv("DROS_AUTH_JWKS_CACHE_TTL_SECONDS", "300").strip() or "300")
    auth_jwks_timeout_seconds = float(os.getenv("DROS_AUTH_JWKS_TIMEOUT_SECONDS", "5").strip() or "5")
    auth_jwt_issuer = os.getenv("DROS_AUTH_JWT_ISSUER", "").strip() or None
    auth_jwt_audience = os.getenv("DROS_AUTH_JWT_AUDIENCE", "").strip() or None
    auth_principal_claim = os.getenv("DROS_AUTH_PRINCIPAL_CLAIM", "principal_id").strip() or "principal_id"
    auth_tenant_claim = os.getenv("DROS_AUTH_TENANT_CLAIM", "tenant_id").strip() or "tenant_id"
    auth_project_role_claim = (
        os.getenv("DROS_AUTH_PROJECT_ROLE_CLAIM", "project_role").strip() or "project_role"
    )
    auth_scopes_claim = os.getenv("DROS_AUTH_SCOPES_CLAIM", "scope").strip() or "scope"
    auth_jti_claim = os.getenv("DROS_AUTH_JTI_CLAIM", "jti").strip() or "jti"
    auth_require_jti = _env_flag("DROS_AUTH_REQUIRE_JTI", False)
    auth_revoked_jti_list = _env_list("DROS_AUTH_REVOKED_JTI_LIST", ())
    auth_introspection_url = os.getenv("DROS_AUTH_INTROSPECTION_URL", "").strip() or None
    auth_introspection_client_id = os.getenv("DROS_AUTH_INTROSPECTION_CLIENT_ID", "").strip() or None
    auth_introspection_client_secret = os.getenv("DROS_AUTH_INTROSPECTION_CLIENT_SECRET", "").strip() or None
    auth_introspection_token_type_hint = os.getenv("DROS_AUTH_INTROSPECTION_TOKEN_TYPE_HINT", "").strip() or None
    auth_introspection_timeout_seconds = float(
        os.getenv("DROS_AUTH_INTROSPECTION_TIMEOUT_SECONDS", "5").strip() or "5"
    )
    ncbi_enabled = _env_flag("DROS_NCBI_ENABLED", False)
    ncbi_base_url = (
        os.getenv("DROS_NCBI_BASE_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils").strip().rstrip("/")
    )
    pmc_oa_base_url = (
        os.getenv("DROS_PMC_OA_BASE_URL", "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi").strip()
    )
    ncbi_tool = os.getenv("DROS_NCBI_TOOL", "dros-control-plane").strip() or "dros-control-plane"
    ncbi_email = os.getenv("DROS_NCBI_EMAIL", "").strip() or None
    ncbi_api_key = os.getenv("DROS_NCBI_API_KEY", "").strip() or None
    ncbi_cache_ttl_hours = int(os.getenv("DROS_NCBI_CACHE_TTL_HOURS", "24").strip() or "24")
    ncbi_rate_limit_raw = os.getenv("DROS_NCBI_RATE_LIMIT_PER_SEC", "").strip()
    ncbi_rate_limit_per_sec = float(ncbi_rate_limit_raw) if ncbi_rate_limit_raw else None
    ncbi_timeout_seconds = float(os.getenv("DROS_NCBI_TIMEOUT_SECONDS", "10").strip() or "10")
    if ledger_backend == "postgres" and not postgres_dsn:
        raise ValueError("DROS_POSTGRES_DSN is required when DROS_LEDGER_BACKEND=postgres")
    if (
        auth_mode in {"jwt", "mixed"}
        and not auth_jwt_secret
        and not auth_jwks_url
        and not auth_oidc_discovery_url
        and not auth_introspection_url
    ):
        raise ValueError(
            "DROS_AUTH_JWT_SECRET, DROS_AUTH_JWKS_URL, DROS_AUTH_OIDC_DISCOVERY_URL, or DROS_AUTH_INTROSPECTION_URL is required when JWT auth is enabled"
        )
    if auth_oidc_cache_ttl_seconds <= 0:
        raise ValueError("DROS_AUTH_OIDC_CACHE_TTL_SECONDS must be > 0")
    if auth_jwks_cache_ttl_seconds <= 0:
        raise ValueError("DROS_AUTH_JWKS_CACHE_TTL_SECONDS must be > 0")
    if auth_jwks_timeout_seconds <= 0:
        raise ValueError("DROS_AUTH_JWKS_TIMEOUT_SECONDS must be > 0")
    if auth_introspection_timeout_seconds <= 0:
        raise ValueError("DROS_AUTH_INTROSPECTION_TIMEOUT_SECONDS must be > 0")
    return AppSettings(
        ledger_backend=ledger_backend,
        ledger_path=Path(ledger_path_raw).expanduser(),
        object_store_path=Path(object_store_path_raw).expanduser(),
        postgres_dsn=postgres_dsn,
        postgres_schema=postgres_schema,
        auth_mode=auth_mode,
        auth_jwt_secret=auth_jwt_secret,
        auth_oidc_discovery_url=auth_oidc_discovery_url,
        auth_jwks_url=auth_jwks_url,
        auth_jwt_algorithms=auth_jwt_algorithms,
        auth_oidc_cache_ttl_seconds=auth_oidc_cache_ttl_seconds,
        auth_jwks_cache_ttl_seconds=auth_jwks_cache_ttl_seconds,
        auth_jwks_timeout_seconds=auth_jwks_timeout_seconds,
        auth_jwt_issuer=auth_jwt_issuer,
        auth_jwt_audience=auth_jwt_audience,
        auth_principal_claim=auth_principal_claim,
        auth_tenant_claim=auth_tenant_claim,
        auth_project_role_claim=auth_project_role_claim,
        auth_scopes_claim=auth_scopes_claim,
        auth_jti_claim=auth_jti_claim,
        auth_require_jti=auth_require_jti,
        auth_revoked_jti_list=auth_revoked_jti_list,
        auth_introspection_url=auth_introspection_url,
        auth_introspection_client_id=auth_introspection_client_id,
        auth_introspection_client_secret=auth_introspection_client_secret,
        auth_introspection_token_type_hint=auth_introspection_token_type_hint,
        auth_introspection_timeout_seconds=auth_introspection_timeout_seconds,
        ncbi_enabled=ncbi_enabled,
        ncbi_base_url=ncbi_base_url,
        pmc_oa_base_url=pmc_oa_base_url,
        ncbi_tool=ncbi_tool,
        ncbi_email=ncbi_email,
        ncbi_api_key=ncbi_api_key,
        ncbi_cache_ttl_hours=ncbi_cache_ttl_hours,
        ncbi_rate_limit_per_sec=ncbi_rate_limit_per_sec,
        ncbi_timeout_seconds=ncbi_timeout_seconds,
    )
