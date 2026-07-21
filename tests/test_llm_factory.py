"""
app.llm.factory.get_llm fonksiyonu için unit testler.

Gerçek Settings nesnesi yerine, factory'nin sadece attribute-erişimi
(getattr) kullandığı gerçeğinden faydalanarak hafif bir sahte (fake)
settings nesnesi kullanılır. Böylece SLACK_BOT_TOKEN gibi ilgisiz
zorunlu alanları doldurmaya gerek kalmaz.
"""
from types import SimpleNamespace

import pytest

from app.llm.factory import get_llm
from app.llm.anthropic_llm import AnthropicLLM
from app.llm.mistral_llm import MistralLLM
from app.llm.openai_llm import OpenAILLM


def fake_settings(**overrides):
    defaults = dict(
        LLM_PROVIDER="mock",
        ANTHROPIC_API_KEY=None,
        MISTRAL_API_KEY=None,
        MISTRAL_MODEL="mistral-large-latest",
        OPENAI_API_KEY=None,
        OPENAI_MODEL="gpt-4o-mini",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestGetLLMOpenAI:
    def test_returns_openai_llm_instance(self):
        settings = fake_settings(LLM_PROVIDER="openai", OPENAI_API_KEY="sk-test")

        llm = get_llm(settings)

        assert isinstance(llm, OpenAILLM)

    def test_uses_configured_api_key_and_model(self):
        settings = fake_settings(
            LLM_PROVIDER="openai",
            OPENAI_API_KEY="sk-test-123",
            OPENAI_MODEL="gpt-4o",
        )

        llm = get_llm(settings)

        assert llm.model == "gpt-4o"
        # AsyncOpenAI client'ının doğru api_key ile kurulduğunu client üzerinden kontrol edelim
        assert llm.client.api_key == "sk-test-123"

    def test_falls_back_to_default_model_when_not_set(self):
        settings = fake_settings(LLM_PROVIDER="openai", OPENAI_API_KEY="sk-test")
        del settings.OPENAI_MODEL  # OPENAI_MODEL hiç tanımlı değilmiş gibi davran

        llm = get_llm(settings)

        assert llm.model == "gpt-4o-mini"

    def test_provider_selection_is_case_insensitive(self):
        settings = fake_settings(LLM_PROVIDER="OpenAI", OPENAI_API_KEY="sk-test")

        llm = get_llm(settings)

        assert isinstance(llm, OpenAILLM)


class TestGetLLMOtherProviders:
    def test_returns_anthropic_llm_instance(self):
        settings = fake_settings(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="ant-test")

        llm = get_llm(settings)

        assert isinstance(llm, AnthropicLLM)

    def test_returns_mistral_llm_instance(self):
        settings = fake_settings(LLM_PROVIDER="mistral", MISTRAL_API_KEY="mis-test")

        llm = get_llm(settings)

        assert isinstance(llm, MistralLLM)


class TestGetLLMUnsupportedProvider:
    def test_raises_value_error_for_unknown_provider(self):
        settings = fake_settings(LLM_PROVIDER="mock")

        with pytest.raises(ValueError, match="Desteklenmeyen LLM sağlayıcısı"):
            get_llm(settings)

    def test_raises_value_error_for_typo_in_provider_name(self):
        settings = fake_settings(LLM_PROVIDER="opnai")

        with pytest.raises(ValueError):
            get_llm(settings)
