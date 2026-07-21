"""
app.core.security modülü için unit testler.

_is_valid_key: sabit-zamanlı (timing-safe) key karşılaştırması.
verify_api_key: FastAPI dependency - geçerli key'i döner, değilse HTTPException fırlatır.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.security import _is_valid_key, verify_api_key


class TestIsValidKey:
    def test_returns_true_for_matching_key(self):
        assert _is_valid_key("secret-1", ["secret-1", "secret-2"]) is True

    def test_returns_false_for_non_matching_key(self):
        assert _is_valid_key("wrong-key", ["secret-1", "secret-2"]) is False

    def test_returns_false_for_empty_valid_keys_list(self):
        assert _is_valid_key("anything", []) is False

    def test_skips_falsy_entries_in_valid_keys(self):
        # "" gibi boş bir key listede olsa bile candidate ile eşleşmemeli
        assert _is_valid_key("", ["secret-1", ""]) is False

    def test_matches_any_key_in_list_not_just_first(self):
        assert _is_valid_key("secret-2", ["secret-1", "secret-2", "secret-3"]) is True

    def test_non_ascii_candidate_does_not_raise(self):
        """hmac.compare_digest Unicode ile TypeError fırlatabilir; utf-8 encode ile bu önleniyor."""
        result = _is_valid_key("çalışan-key-ı", ["secret-1"])
        assert result is False

    def test_non_ascii_candidate_matches_non_ascii_valid_key(self):
        result = _is_valid_key("ceng-abi-key-ı", ["ceng-abi-key-ı"])
        assert result is True

    def test_is_case_sensitive(self):
        assert _is_valid_key("Secret-1", ["secret-1"]) is False


def fake_settings(api_keys):
    return SimpleNamespace(API_KEYS=api_keys)


class TestVerifyApiKey:
    async def test_returns_key_when_valid(self):
        settings = fake_settings(["argeset-dev-key"])

        result = await verify_api_key(api_key="argeset-dev-key", settings=settings)

        assert result == "argeset-dev-key"

    async def test_raises_401_when_key_missing(self):
        settings = fake_settings(["argeset-dev-key"])

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key=None, settings=settings)

        assert exc_info.value.status_code == 401

    async def test_raises_401_when_key_invalid(self):
        settings = fake_settings(["argeset-dev-key"])

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="yanlis-key", settings=settings)

        assert exc_info.value.status_code == 401

    async def test_raises_500_when_no_keys_configured(self):
        """API_KEYS boşsa (yanlış konfigürasyon), 401 yerine 500 dönmeli - bu bir server hatası."""
        settings = fake_settings([])

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="herhangi-bir-key", settings=settings)

        assert exc_info.value.status_code == 500

    async def test_401_response_includes_www_authenticate_header(self):
        settings = fake_settings(["argeset-dev-key"])

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key=None, settings=settings)

        assert exc_info.value.headers["WWW-Authenticate"] == "X-API-Key"

    async def test_accepts_any_key_from_multiple_configured_keys(self):
        settings = fake_settings(["key-for-n8n", "key-for-setxrm"])

        result = await verify_api_key(api_key="key-for-setxrm", settings=settings)

        assert result == "key-for-setxrm"
