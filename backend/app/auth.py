from __future__ import annotations

import json
from base64 import b64encode
from contextvars import ContextVar, Token
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen
from uuid import UUID

from fastapi import HTTPException, Request, status

from .schemas.enums import ProjectRole
from .settings import AppSettings, get_settings

DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000002")

TENANT_HEADER = "x-dros-tenant-id"
ACTOR_HEADER = "x-dros-actor-id"
PRINCIPAL_HEADER = "x-dros-principal-id"
PROJECT_ROLE_HEADER = "x-dros-project-role"
SCOPES_HEADER = "x-dros-scopes"
REQUEST_ID_HEADER = "x-request-id"
TRACE_ID_HEADER = "x-trace-id"
AUTHORIZATION_HEADER = "authorization"

ROLE_SCOPE_TOKENS: dict[ProjectRole, tuple[str, ...]] = {
    ProjectRole.OWNER: (
        "projects:read",
        "projects:write",
        "members:write",
        "datasets:read",
        "datasets:write",
        "workflows:read",
        "workflows:write",
        "artifacts:read",
        "artifacts:write",
        "assertions:read",
        "assertions:write",
        "evidence:read",
        "evidence:write",
        "manuscripts:read",
        "manuscripts:write",
        "reviews:read",
        "reviews:write",
        "exports:read",
        "exports:write",
        "uploads:write",
        "events:read",
        "downloads:read",
        "audit:read",
    ),
    ProjectRole.ADMIN: (
        "projects:read",
        "projects:write",
        "members:write",
        "datasets:read",
        "datasets:write",
        "workflows:read",
        "workflows:write",
        "artifacts:read",
        "artifacts:write",
        "assertions:read",
        "assertions:write",
        "evidence:read",
        "evidence:write",
        "manuscripts:read",
        "manuscripts:write",
        "reviews:read",
        "reviews:write",
        "exports:read",
        "exports:write",
        "uploads:write",
        "events:read",
        "downloads:read",
        "audit:read",
    ),
    ProjectRole.EDITOR: (
        "projects:read",
        "datasets:read",
        "datasets:write",
        "workflows:read",
        "workflows:write",
        "artifacts:read",
        "artifacts:write",
        "assertions:read",
        "assertions:write",
        "evidence:read",
        "evidence:write",
        "manuscripts:read",
        "manuscripts:write",
        "reviews:read",
        "exports:read",
        "exports:write",
        "uploads:write",
        "events:read",
        "downloads:read",
        "audit:read",
    ),
    ProjectRole.REVIEWER: (
        "projects:read",
        "datasets:read",
        "workflows:read",
        "artifacts:read",
        "assertions:read",
        "evidence:read",
        "manuscripts:read",
        "reviews:read",
        "reviews:write",
        "exports:read",
        "events:read",
        "downloads:read",
        "audit:read",
    ),
    ProjectRole.VIEWER: (
        "projects:read",
        "datasets:read",
        "workflows:read",
        "artifacts:read",
        "assertions:read",
        "evidence:read",
        "manuscripts:read",
        "reviews:read",
        "exports:read",
        "events:read",
        "downloads:read",
        "audit:read",
    ),
}


@dataclass(frozen=True, slots=True)
class AuthContext:
    tenant_id: UUID
    principal_id: UUID
    project_role: ProjectRole
    scope_tokens: tuple[str, ...]
    request_id: str | None
    trace_id: str | None
    auth_source: str


@dataclass(frozen=True, slots=True)
class JwksCacheEntry:
    keys_by_kid: dict[str, dict[str, Any]]
    expires_at_monotonic: float


@dataclass(frozen=True, slots=True)
class OidcProviderMetadata:
    issuer: str
    jwks_uri: str


@dataclass(frozen=True, slots=True)
class OidcDiscoveryCacheEntry:
    metadata: OidcProviderMetadata
    expires_at_monotonic: float


def default_auth_context() -> AuthContext:
    return AuthContext(
        tenant_id=DEFAULT_TENANT_ID,
        principal_id=DEFAULT_PRINCIPAL_ID,
        project_role=ProjectRole.OWNER,
        scope_tokens=ROLE_SCOPE_TOKENS[ProjectRole.OWNER],
        request_id=None,
        trace_id=None,
        auth_source="dev_default",
    )


_CURRENT_AUTH_CONTEXT: ContextVar[AuthContext] = ContextVar("dros_auth_context", default=default_auth_context())
_OIDC_DISCOVERY_CACHE_LOCK = Lock()
_OIDC_DISCOVERY_CACHE: dict[str, OidcDiscoveryCacheEntry] = {}
_JWKS_CACHE_LOCK = Lock()
_JWKS_CACHE: dict[str, JwksCacheEntry] = {}


def current_auth_context() -> AuthContext:
    return _CURRENT_AUTH_CONTEXT.get()


def bind_auth_context(context: AuthContext) -> Token[AuthContext]:
    return _CURRENT_AUTH_CONTEXT.set(context)


def reset_auth_context(token: Token[AuthContext]) -> None:
    _CURRENT_AUTH_CONTEXT.reset(token)


def clear_auth_caches() -> None:
    with _OIDC_DISCOVERY_CACHE_LOCK:
        _OIDC_DISCOVERY_CACHE.clear()
    with _JWKS_CACHE_LOCK:
        _JWKS_CACHE.clear()


def resolve_auth_context(request: Request) -> AuthContext:
    settings = get_settings()
    if settings.auth_mode in {"jwt", "mixed"}:
        bearer_context = _resolve_bearer_auth_context(request)
        if bearer_context is not None:
            return bearer_context
        if settings.auth_mode == "jwt":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    headers = request.headers
    has_auth_headers = any(
        header in headers
        for header in (
            TENANT_HEADER,
            ACTOR_HEADER,
            PRINCIPAL_HEADER,
            PROJECT_ROLE_HEADER,
            SCOPES_HEADER,
            REQUEST_ID_HEADER,
            TRACE_ID_HEADER,
        )
    )
    tenant_id = _parse_uuid_header(headers.get(TENANT_HEADER), TENANT_HEADER, DEFAULT_TENANT_ID)
    principal_id = _parse_principal_id(headers)
    project_role = _parse_project_role(headers.get(PROJECT_ROLE_HEADER))
    scope_tokens = _parse_scope_tokens(headers.get(SCOPES_HEADER), project_role)
    request_id = _optional_header(headers.get(REQUEST_ID_HEADER))
    trace_id = _optional_header(headers.get(TRACE_ID_HEADER))
    return AuthContext(
        tenant_id=tenant_id,
        principal_id=principal_id,
        project_role=project_role,
        scope_tokens=scope_tokens,
        request_id=request_id,
        trace_id=trace_id,
        auth_source="headers" if has_auth_headers else "dev_default",
    )


def auth_context_to_scopes_json(context: AuthContext) -> dict[str, Any]:
    return {
        "project_role": context.project_role.value,
        "capabilities": list(context.scope_tokens),
        "scope_tokens": list(context.scope_tokens),
        "auth_source": context.auth_source,
        "request_id": context.request_id,
        "trace_id": context.trace_id,
    }


def _optional_header(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _parse_uuid_header(raw: str | None, header_name: str, default: UUID) -> UUID:
    value = _optional_header(raw)
    if value is None:
        return default
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"invalid {header_name}: expected UUID",
        ) from exc


def _parse_principal_id(headers) -> UUID:
    actor_raw = _optional_header(headers.get(ACTOR_HEADER))
    principal_raw = _optional_header(headers.get(PRINCIPAL_HEADER))
    if actor_raw is not None and principal_raw is not None and actor_raw != principal_raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{ACTOR_HEADER} must match {PRINCIPAL_HEADER} when both are provided",
        )
    chosen_raw = principal_raw or actor_raw
    chosen_header = PRINCIPAL_HEADER if principal_raw is not None else ACTOR_HEADER
    return _parse_uuid_header(chosen_raw, chosen_header, DEFAULT_PRINCIPAL_ID)


def _parse_project_role(raw: str | None) -> ProjectRole:
    value = _optional_header(raw)
    if value is None:
        return ProjectRole.OWNER
    try:
        return ProjectRole(value.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(role.value for role in ProjectRole)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"invalid {PROJECT_ROLE_HEADER}: expected one of {allowed}",
        ) from exc


def _parse_scope_tokens(raw: str | None, project_role: ProjectRole) -> tuple[str, ...]:
    value = _optional_header(raw)
    if value is None:
        return ROLE_SCOPE_TOKENS[project_role]
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"invalid {SCOPES_HEADER}: expected JSON array or comma-separated string",
            ) from exc
        if not isinstance(parsed, list) or any(not isinstance(item, str) or not item.strip() for item in parsed):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"invalid {SCOPES_HEADER}: expected JSON array of non-empty strings",
            )
        return tuple(dict.fromkeys(item.strip() for item in parsed))
    return tuple(dict.fromkeys(token.strip() for token in value.split(",") if token.strip()))


def _resolve_bearer_auth_context(request: Request) -> AuthContext | None:
    settings = get_settings()
    authorization = _optional_header(request.headers.get(AUTHORIZATION_HEADER))
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims, auth_source = _decode_bearer_token(token.strip(), settings=settings)
    principal_raw = claims.get(settings.auth_principal_claim) or claims.get("sub")
    tenant_raw = claims.get(settings.auth_tenant_claim)
    if not isinstance(principal_raw, str) or not principal_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"missing principal claim: {settings.auth_principal_claim}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not isinstance(tenant_raw, str) or not tenant_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"missing tenant claim: {settings.auth_tenant_claim}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    principal_id = _parse_uuid_claim(principal_raw, settings.auth_principal_claim or "sub")
    tenant_id = _parse_uuid_claim(tenant_raw, settings.auth_tenant_claim)
    project_role = _parse_role_claim(claims.get(settings.auth_project_role_claim))
    scope_tokens = _parse_scope_claim(claims.get(settings.auth_scopes_claim), project_role)
    return AuthContext(
        tenant_id=tenant_id,
        principal_id=principal_id,
        project_role=project_role,
        scope_tokens=scope_tokens,
        request_id=_optional_header(request.headers.get(REQUEST_ID_HEADER)),
        trace_id=_optional_header(request.headers.get(TRACE_ID_HEADER)),
        auth_source=auth_source,
    )


def _decode_bearer_token(token: str, *, settings: AppSettings | None = None) -> tuple[dict[str, Any], str]:
    settings = settings or get_settings()
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError("PyJWT is required when JWT auth is enabled") from exc

    claims: dict[str, Any] = {}
    auth_source = "bearer_introspection" if settings.auth_introspection_url else "jwt_bearer"

    if _has_local_bearer_validation_source(settings):
        effective_issuer = _resolve_effective_issuer(settings=settings)
        effective_jwks_url = _resolve_effective_jwks_url(settings=settings, force_refresh_discovery=False)
        decode_kwargs: dict[str, Any] = {
            "algorithms": list(settings.auth_jwt_algorithms),
            "options": {
                "require": ["exp", "iat"],
                "verify_aud": settings.auth_jwt_audience is not None,
                "verify_iss": effective_issuer is not None,
            },
        }
        if settings.auth_jwt_audience is not None:
            decode_kwargs["audience"] = settings.auth_jwt_audience
        if effective_issuer is not None:
            decode_kwargs["issuer"] = effective_issuer

        try:
            if effective_jwks_url:
                signing_key = _resolve_jwks_signing_key(jwt_module=jwt, token=token, settings=settings)
                claims = jwt.decode(token, signing_key, **decode_kwargs)
            else:
                claims = jwt.decode(token, settings.auth_jwt_secret, **decode_kwargs)
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"invalid bearer token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if not isinstance(claims, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid bearer token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if settings.auth_introspection_url is not None:
            auth_source = "jwt_bearer_introspection"

    if settings.auth_introspection_url is not None:
        introspection_claims = _introspect_bearer_token(token=token, settings=settings)
        claims = {**claims, **introspection_claims}

    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _validate_token_jti_claim(claims=claims, settings=settings)
    return claims, auth_source


def _resolve_jwks_signing_key(*, jwt_module, token: str, settings) -> Any:
    try:
        header = jwt_module.get_unverified_header(token)
    except jwt_module.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not isinstance(header, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    kid_raw = header.get("kid")
    if not isinstance(kid_raw, str) or not kid_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: missing kid header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jwk = _get_jwk_for_kid(kid=kid_raw.strip(), settings=settings)
    algorithm = header.get("alg")
    try:
        return jwt_module.PyJWK.from_dict(
            jwk,
            algorithm=algorithm if isinstance(algorithm, str) else None,
        ).key
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: unable to load signing key for kid {kid_raw.strip()}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _get_jwk_for_kid(*, kid: str, settings: AppSettings) -> dict[str, Any]:
    jwks_url = _resolve_effective_jwks_url(settings=settings, force_refresh_discovery=False)
    if jwks_url is None:
        raise RuntimeError("JWKS URL is required to resolve signing keys")
    keys_by_kid = _get_jwks_keys(url=jwks_url, settings=settings, force_refresh=False)
    jwk = keys_by_kid.get(kid)
    if jwk is not None:
        return jwk
    refreshed_jwks_url = _resolve_effective_jwks_url(
        settings=settings,
        force_refresh_discovery=settings.auth_oidc_discovery_url is not None and settings.auth_jwks_url is None,
    )
    if refreshed_jwks_url is None:
        raise RuntimeError("JWKS URL is required to resolve signing keys")
    keys_by_kid = _get_jwks_keys(url=refreshed_jwks_url, settings=settings, force_refresh=True)
    jwk = keys_by_kid.get(kid)
    if jwk is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: unknown signing key kid {kid}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return jwk


def _resolve_effective_issuer(*, settings: AppSettings) -> str | None:
    if settings.auth_oidc_discovery_url is None:
        return settings.auth_jwt_issuer
    metadata = _get_oidc_provider_metadata(settings=settings, force_refresh=False)
    if settings.auth_jwt_issuer is not None and settings.auth_jwt_issuer != metadata.issuer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: OIDC discovery issuer mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return settings.auth_jwt_issuer or metadata.issuer


def _resolve_effective_jwks_url(*, settings: AppSettings, force_refresh_discovery: bool) -> str | None:
    if settings.auth_jwks_url is not None:
        return settings.auth_jwks_url
    if settings.auth_oidc_discovery_url is None:
        return None
    return _get_oidc_provider_metadata(settings=settings, force_refresh=force_refresh_discovery).jwks_uri


def _has_local_bearer_validation_source(settings: AppSettings) -> bool:
    return settings.auth_jwt_secret is not None or settings.auth_jwks_url is not None or settings.auth_oidc_discovery_url is not None


def _get_oidc_provider_metadata(*, settings: AppSettings, force_refresh: bool) -> OidcProviderMetadata:
    discovery_url = settings.auth_oidc_discovery_url
    if discovery_url is None:
        raise RuntimeError("OIDC discovery URL is required to resolve provider metadata")
    now = monotonic()
    if not force_refresh:
        with _OIDC_DISCOVERY_CACHE_LOCK:
            cached = _OIDC_DISCOVERY_CACHE.get(discovery_url)
        if cached is not None and cached.expires_at_monotonic > now:
            return cached.metadata

    metadata = _load_oidc_provider_metadata(url=discovery_url, timeout_seconds=settings.auth_jwks_timeout_seconds)
    with _OIDC_DISCOVERY_CACHE_LOCK:
        _OIDC_DISCOVERY_CACHE[discovery_url] = OidcDiscoveryCacheEntry(
            metadata=metadata,
            expires_at_monotonic=now + settings.auth_oidc_cache_ttl_seconds,
        )
    return metadata


def _load_oidc_provider_metadata(*, url: str, timeout_seconds: float) -> OidcProviderMetadata:
    payload = _fetch_oidc_discovery_document(url=url, timeout_seconds=timeout_seconds)
    issuer_raw = payload.get("issuer")
    jwks_uri_raw = payload.get("jwks_uri")
    if not isinstance(issuer_raw, str) or not issuer_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: OIDC discovery missing issuer",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not isinstance(jwks_uri_raw, str) or not jwks_uri_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: OIDC discovery missing jwks_uri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return OidcProviderMetadata(
        issuer=issuer_raw.strip(),
        jwks_uri=jwks_uri_raw.strip(),
    )


def _get_jwks_keys(*, url: str, settings, force_refresh: bool) -> dict[str, dict[str, Any]]:
    now = monotonic()
    if not force_refresh:
        with _JWKS_CACHE_LOCK:
            cached = _JWKS_CACHE.get(url)
        if cached is not None and cached.expires_at_monotonic > now:
            return cached.keys_by_kid

    keys_by_kid = _load_jwks_keys(url=url, timeout_seconds=settings.auth_jwks_timeout_seconds)
    with _JWKS_CACHE_LOCK:
        _JWKS_CACHE[url] = JwksCacheEntry(
            keys_by_kid=keys_by_kid,
            expires_at_monotonic=now + settings.auth_jwks_cache_ttl_seconds,
        )
    return keys_by_kid


def _load_jwks_keys(*, url: str, timeout_seconds: float) -> dict[str, dict[str, Any]]:
    payload = _fetch_jwks_document(url=url, timeout_seconds=timeout_seconds)
    keys = payload.get("keys")
    if not isinstance(keys, list):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: JWKS document missing keys array",
            headers={"WWW-Authenticate": "Bearer"},
        )
    keys_by_kid: dict[str, dict[str, Any]] = {}
    for candidate in keys:
        if not isinstance(candidate, dict):
            continue
        kid_raw = candidate.get("kid")
        if not isinstance(kid_raw, str) or not kid_raw.strip():
            continue
        keys_by_kid[kid_raw.strip()] = candidate
    if not keys_by_kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: JWKS document contained no usable keys",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return keys_by_kid


def _introspect_bearer_token(*, token: str, settings: AppSettings) -> dict[str, Any]:
    payload = _fetch_token_introspection(
        token=token,
        url=settings.auth_introspection_url,
        client_id=settings.auth_introspection_client_id,
        client_secret=settings.auth_introspection_client_secret,
        token_type_hint=settings.auth_introspection_token_type_hint,
        timeout_seconds=settings.auth_introspection_timeout_seconds,
    )
    active = payload.get("active")
    if active is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="inactive bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {key: value for key, value in payload.items() if key != "active"}


def _fetch_oidc_discovery_document(*, url: str, timeout_seconds: float) -> dict[str, Any]:
    try:
        return _fetch_json_document(url=url, timeout_seconds=timeout_seconds)
    except HTTPException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: unable to load OIDC discovery metadata from {url}",
            headers=exc.headers or {"WWW-Authenticate": "Bearer"},
        ) from exc


def _fetch_jwks_document(*, url: str, timeout_seconds: float) -> dict[str, Any]:
    try:
        return _fetch_json_document(url=url, timeout_seconds=timeout_seconds)
    except HTTPException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: unable to load JWKS from {url}",
            headers=exc.headers or {"WWW-Authenticate": "Bearer"},
        ) from exc


def _fetch_token_introspection(
    *,
    token: str,
    url: str | None,
    client_id: str | None,
    client_secret: str | None,
    token_type_hint: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    if url is None:
        raise RuntimeError("introspection URL is required to introspect bearer tokens")
    form_fields: dict[str, str] = {"token": token}
    if token_type_hint is not None:
        form_fields["token_type_hint"] = token_type_hint
    body = urlencode(form_fields).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if client_id is not None and client_secret is not None:
        basic = b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"
    request = UrlRequest(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: unable to introspect token via {url}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: introspection response must be a JSON object",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def _fetch_json_document(*, url: str, timeout_seconds: float) -> dict[str, Any]:
    request = UrlRequest(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid bearer token: unable to load JSON document from {url}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token: JSON document must be an object",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def _validate_token_jti_claim(*, claims: dict[str, Any], settings: AppSettings) -> None:
    jti_raw = claims.get(settings.auth_jti_claim)
    if jti_raw is None:
        if settings.auth_require_jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"missing jti claim: {settings.auth_jti_claim}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return
    if not isinstance(jti_raw, str) or not jti_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid jti claim: {settings.auth_jti_claim}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if jti_raw.strip() in set(settings.auth_revoked_jti_list):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="revoked bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _parse_uuid_claim(value: str, claim_name: str) -> UUID:
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid UUID claim for {claim_name}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _parse_role_claim(value: Any) -> ProjectRole:
    if value is None:
        return ProjectRole.VIEWER
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid project_role claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return ProjectRole(value.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unsupported project_role claim",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _parse_scope_claim(value: Any, project_role: ProjectRole) -> tuple[str, ...]:
    if value is None:
        return ROLE_SCOPE_TOKENS[project_role]
    if isinstance(value, str):
        tokens = [token.strip() for token in value.replace(",", " ").split() if token.strip()]
        return tuple(dict.fromkeys(tokens)) or ROLE_SCOPE_TOKENS[project_role]
    if isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        return tuple(dict.fromkeys(item.strip() for item in value))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid scope claim",
        headers={"WWW-Authenticate": "Bearer"},
    )


def build_dev_jwt_claims(
    *,
    principal_id: UUID,
    tenant_id: UUID,
    project_role: ProjectRole = ProjectRole.OWNER,
    scope_tokens: tuple[str, ...] | None = None,
    issuer: str = "https://dev-idp.dros.local",
    audience: str = "dros-control-plane",
    expires_in_seconds: int = 3600,
    token_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    claims = {
        "sub": str(principal_id),
        "principal_id": str(principal_id),
        "tenant_id": str(tenant_id),
        "project_role": project_role.value,
        "scope": " ".join(scope_tokens or ROLE_SCOPE_TOKENS[project_role]),
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "nbf": now - timedelta(seconds=1),
        "exp": now + timedelta(seconds=expires_in_seconds),
    }
    if token_id is not None:
        claims["jti"] = token_id
    return claims
