from __future__ import annotations

from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.app import dependencies
from backend.app import auth as auth_module
from backend.app.auth import build_dev_jwt_claims
from backend.app.main import create_app
from backend.app.settings import get_settings


def _configure_jwks_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_OIDC_DISCOVERY_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", "")
    monkeypatch.setenv("DROS_AUTH_JWKS_URL", "https://idp.dros.local/.well-known/jwks.json")
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "RS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    monkeypatch.setenv("DROS_AUTH_JWKS_CACHE_TTL_SECONDS", "300")
    monkeypatch.setenv("DROS_AUTH_JWKS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("DROS_AUTH_REQUIRE_JTI", "false")
    monkeypatch.setenv("DROS_AUTH_REVOKED_JTI_LIST", "")
    _reload_runtime_caches()


def _reload_runtime_caches() -> None:
    get_settings.cache_clear()
    auth_module.clear_auth_caches()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()


def _configure_oidc_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", "")
    monkeypatch.setenv("DROS_AUTH_JWKS_URL", "")
    monkeypatch.setenv("DROS_AUTH_OIDC_DISCOVERY_URL", "https://idp.dros.local/.well-known/openid-configuration")
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "RS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    monkeypatch.setenv("DROS_AUTH_OIDC_CACHE_TTL_SECONDS", "300")
    monkeypatch.setenv("DROS_AUTH_JWKS_CACHE_TTL_SECONDS", "300")
    monkeypatch.setenv("DROS_AUTH_JWKS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("DROS_AUTH_REQUIRE_JTI", "false")
    monkeypatch.setenv("DROS_AUTH_REVOKED_JTI_LIST", "")
    _reload_runtime_caches()


def _configure_introspection_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", "")
    monkeypatch.setenv("DROS_AUTH_JWKS_URL", "")
    monkeypatch.setenv("DROS_AUTH_OIDC_DISCOVERY_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_URL", "https://idp.dros.local/oauth2/introspect")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_CLIENT_ID", "dros-control-plane")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_CLIENT_SECRET", "introspection-secret")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_TOKEN_TYPE_HINT", "access_token")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("DROS_AUTH_REQUIRE_JTI", "false")
    monkeypatch.setenv("DROS_AUTH_REVOKED_JTI_LIST", "")
    _reload_runtime_caches()


def _generate_rsa_signing_material(kid: str) -> tuple[object, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return private_key, jwk


def test_jwt_bearer_auth_supports_rs256_jwks_validation_and_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_jwks_auth(monkeypatch)
    private_key, jwk = _generate_rsa_signing_material("kid-rs256-cache")
    fetch_count = 0

    def fake_fetch_jwks_document(*, url: str, timeout_seconds: float) -> dict[str, object]:
        nonlocal fetch_count
        fetch_count += 1
        assert url == "https://idp.dros.local/.well-known/jwks.json"
        assert timeout_seconds == 2
        return {"keys": [dict(jwk)]}

    monkeypatch.setattr(auth_module, "_fetch_jwks_document", fake_fetch_jwks_document)

    tenant_id = uuid4()
    principal_id = uuid4()
    token = jwt.encode(
        build_dev_jwt_claims(
            principal_id=principal_id,
            tenant_id=tenant_id,
            issuer="https://idp.dros.local",
            audience="dros-control-plane",
        ),
        private_key,
        algorithm="RS256",
        headers={"kid": "kid-rs256-cache"},
    )

    client = TestClient(create_app())
    first_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})
    second_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["principal_id"] == str(principal_id)
    assert second_response.json()["tenant_id"] == str(tenant_id)
    assert second_response.json()["scopes_json"]["auth_source"] == "jwt_bearer"
    assert fetch_count == 1


def test_jwt_bearer_auth_refreshes_jwks_when_signing_key_rotates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_jwks_auth(monkeypatch)
    private_key_v1, jwk_v1 = _generate_rsa_signing_material("kid-rotation-v1")
    private_key_v2, jwk_v2 = _generate_rsa_signing_material("kid-rotation-v2")
    documents = [
        {"keys": [dict(jwk_v1)]},
        {"keys": [dict(jwk_v1), dict(jwk_v2)]},
    ]
    fetch_count = 0

    def fake_fetch_jwks_document(*, url: str, timeout_seconds: float) -> dict[str, object]:
        nonlocal fetch_count
        fetch_count += 1
        assert url == "https://idp.dros.local/.well-known/jwks.json"
        assert timeout_seconds == 2
        return documents[min(fetch_count - 1, len(documents) - 1)]

    monkeypatch.setattr(auth_module, "_fetch_jwks_document", fake_fetch_jwks_document)

    token_v1 = jwt.encode(
        build_dev_jwt_claims(
            principal_id=uuid4(),
            tenant_id=uuid4(),
            issuer="https://idp.dros.local",
            audience="dros-control-plane",
        ),
        private_key_v1,
        algorithm="RS256",
        headers={"kid": "kid-rotation-v1"},
    )
    principal_id_v2 = uuid4()
    token_v2 = jwt.encode(
        build_dev_jwt_claims(
            principal_id=principal_id_v2,
            tenant_id=uuid4(),
            issuer="https://idp.dros.local",
            audience="dros-control-plane",
        ),
        private_key_v2,
        algorithm="RS256",
        headers={"kid": "kid-rotation-v2"},
    )

    client = TestClient(create_app())
    first_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token_v1}"})
    second_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token_v2}"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["principal_id"] == str(principal_id_v2)
    assert fetch_count == 2


def test_jwt_bearer_auth_supports_oidc_discovery_for_issuer_and_jwks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_oidc_auth(monkeypatch)
    private_key, jwk = _generate_rsa_signing_material("kid-oidc-discovery")
    fetch_counts = {"discovery": 0, "jwks": 0}

    def fake_fetch_oidc_discovery_document(*, url: str, timeout_seconds: float) -> dict[str, object]:
        fetch_counts["discovery"] += 1
        assert url == "https://idp.dros.local/.well-known/openid-configuration"
        assert timeout_seconds == 2
        return {
            "issuer": "https://idp.dros.local",
            "jwks_uri": "https://idp.dros.local/.well-known/jwks.json",
        }

    def fake_fetch_jwks_document(*, url: str, timeout_seconds: float) -> dict[str, object]:
        fetch_counts["jwks"] += 1
        assert url == "https://idp.dros.local/.well-known/jwks.json"
        assert timeout_seconds == 2
        return {"keys": [dict(jwk)]}

    monkeypatch.setattr(auth_module, "_fetch_oidc_discovery_document", fake_fetch_oidc_discovery_document)
    monkeypatch.setattr(auth_module, "_fetch_jwks_document", fake_fetch_jwks_document)

    principal_id = uuid4()
    tenant_id = uuid4()
    token = jwt.encode(
        build_dev_jwt_claims(
            principal_id=principal_id,
            tenant_id=tenant_id,
            issuer="https://idp.dros.local",
            audience="dros-control-plane",
        ),
        private_key,
        algorithm="RS256",
        headers={"kid": "kid-oidc-discovery"},
    )

    client = TestClient(create_app())
    first_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})
    second_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["principal_id"] == str(principal_id)
    assert fetch_counts == {"discovery": 1, "jwks": 1}


def test_jwt_bearer_auth_refreshes_oidc_discovery_when_kid_moves_to_new_jwks_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_oidc_auth(monkeypatch)
    private_key_v1, jwk_v1 = _generate_rsa_signing_material("kid-oidc-v1")
    private_key_v2, jwk_v2 = _generate_rsa_signing_material("kid-oidc-v2")
    fetch_counts = {"discovery": 0, "jwks_v1": 0, "jwks_v2": 0}

    def fake_fetch_oidc_discovery_document(*, url: str, timeout_seconds: float) -> dict[str, object]:
        fetch_counts["discovery"] += 1
        assert url == "https://idp.dros.local/.well-known/openid-configuration"
        assert timeout_seconds == 2
        if fetch_counts["discovery"] == 1:
            return {
                "issuer": "https://idp.dros.local",
                "jwks_uri": "https://idp.dros.local/jwks/v1.json",
            }
        return {
            "issuer": "https://idp.dros.local",
            "jwks_uri": "https://idp.dros.local/jwks/v2.json",
        }

    def fake_fetch_jwks_document(*, url: str, timeout_seconds: float) -> dict[str, object]:
        assert timeout_seconds == 2
        if url == "https://idp.dros.local/jwks/v1.json":
            fetch_counts["jwks_v1"] += 1
            return {"keys": [dict(jwk_v1)]}
        if url == "https://idp.dros.local/jwks/v2.json":
            fetch_counts["jwks_v2"] += 1
            return {"keys": [dict(jwk_v2)]}
        raise AssertionError(f"unexpected jwks url: {url}")

    monkeypatch.setattr(auth_module, "_fetch_oidc_discovery_document", fake_fetch_oidc_discovery_document)
    monkeypatch.setattr(auth_module, "_fetch_jwks_document", fake_fetch_jwks_document)

    token_v1 = jwt.encode(
        build_dev_jwt_claims(
            principal_id=uuid4(),
            tenant_id=uuid4(),
            issuer="https://idp.dros.local",
            audience="dros-control-plane",
        ),
        private_key_v1,
        algorithm="RS256",
        headers={"kid": "kid-oidc-v1"},
    )
    principal_id_v2 = uuid4()
    token_v2 = jwt.encode(
        build_dev_jwt_claims(
            principal_id=principal_id_v2,
            tenant_id=uuid4(),
            issuer="https://idp.dros.local",
            audience="dros-control-plane",
        ),
        private_key_v2,
        algorithm="RS256",
        headers={"kid": "kid-oidc-v2"},
    )

    client = TestClient(create_app())
    first_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token_v1}"})
    second_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token_v2}"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["principal_id"] == str(principal_id_v2)
    assert fetch_counts == {"discovery": 2, "jwks_v1": 1, "jwks_v2": 1}


def test_jwt_bearer_auth_rejects_missing_jti_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "require-jti-secret-0123456789abcdef"
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DROS_AUTH_OIDC_DISCOVERY_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWKS_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://dev-idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    monkeypatch.setenv("DROS_AUTH_JTI_CLAIM", "jti")
    monkeypatch.setenv("DROS_AUTH_REQUIRE_JTI", "true")
    monkeypatch.setenv("DROS_AUTH_REVOKED_JTI_LIST", "")
    _reload_runtime_caches()

    token = jwt.encode(
        build_dev_jwt_claims(
            principal_id=uuid4(),
            tenant_id=uuid4(),
        ),
        secret,
        algorithm="HS256",
    )

    client = TestClient(create_app())
    response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "missing jti claim: jti"


def test_jwt_bearer_auth_rejects_revoked_jti(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "revoked-jti-secret-0123456789abcdef"
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DROS_AUTH_OIDC_DISCOVERY_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWKS_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://dev-idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    monkeypatch.setenv("DROS_AUTH_JTI_CLAIM", "jti")
    monkeypatch.setenv("DROS_AUTH_REQUIRE_JTI", "true")
    monkeypatch.setenv("DROS_AUTH_REVOKED_JTI_LIST", "revoked-token-001")
    _reload_runtime_caches()

    token = jwt.encode(
        build_dev_jwt_claims(
            principal_id=uuid4(),
            tenant_id=uuid4(),
            token_id="revoked-token-001",
        ),
        secret,
        algorithm="HS256",
    )

    client = TestClient(create_app())
    response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "revoked bearer token"


def test_bearer_auth_supports_introspection_only_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_introspection_auth(monkeypatch)

    def fake_fetch_token_introspection(**kwargs) -> dict[str, object]:
        assert kwargs["url"] == "https://idp.dros.local/oauth2/introspect"
        assert kwargs["client_id"] == "dros-control-plane"
        assert kwargs["client_secret"] == "introspection-secret"
        assert kwargs["token_type_hint"] == "access_token"
        assert kwargs["timeout_seconds"] == 2
        assert kwargs["token"] == "opaque-access-token-001"
        return {
            "active": True,
            "sub": str(uuid4()),
            "principal_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "project_role": "editor",
            "scope": "projects:read datasets:write manuscripts:read",
            "jti": "opaque-jti-001",
        }

    monkeypatch.setattr(auth_module, "_fetch_token_introspection", fake_fetch_token_introspection)

    client = TestClient(create_app())
    response = client.get("/v1/session", headers={"Authorization": "Bearer opaque-access-token-001"})

    assert response.status_code == 200
    assert response.json()["scopes_json"]["auth_source"] == "bearer_introspection"
    assert response.json()["scopes_json"]["project_role"] == "editor"
    assert "datasets:write" in response.json()["scopes_json"]["scope_tokens"]


def test_valid_jwt_is_rejected_when_introspection_reports_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "jwt-with-introspection-secret-0123456789abcdef"
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DROS_AUTH_JWKS_URL", "")
    monkeypatch.setenv("DROS_AUTH_OIDC_DISCOVERY_URL", "")
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://dev-idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_URL", "https://idp.dros.local/oauth2/introspect")
    monkeypatch.setenv("DROS_AUTH_INTROSPECTION_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("DROS_AUTH_REQUIRE_JTI", "false")
    monkeypatch.setenv("DROS_AUTH_REVOKED_JTI_LIST", "")
    _reload_runtime_caches()

    token = jwt.encode(
        build_dev_jwt_claims(
            principal_id=uuid4(),
            tenant_id=uuid4(),
        ),
        secret,
        algorithm="HS256",
    )

    monkeypatch.setattr(auth_module, "_fetch_token_introspection", lambda **_: {"active": False})

    client = TestClient(create_app())
    response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "inactive bearer token"
