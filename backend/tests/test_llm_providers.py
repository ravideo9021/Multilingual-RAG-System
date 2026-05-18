"""Tests for LLM providers and factory.

ALL tests mock the underlying SDK calls — zero real API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.generation.llm_base import LLMProvider


# ---------------------------------------------------------------------- #
# LLMProvider ABC
# ---------------------------------------------------------------------- #


class TestLLMProviderABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            LLMProvider("model")  # type: ignore[abstract]

    def test_model_property(self):
        class _Concrete(LLMProvider):
            def generate(self, prompt, *, system=None, temperature=0.3):
                return "ok"

            async def stream(self, prompt, *, system=None, temperature=0.3):
                yield "ok"

        c = _Concrete("test-model")
        assert c.model == "test-model"


# ---------------------------------------------------------------------- #
# GeminiProvider
# ---------------------------------------------------------------------- #


class TestGeminiProvider:
    def test_generate_returns_text(self):
        """Create a GeminiProvider bypassing __init__, then mock the internals."""
        from app.generation.gemini_provider import GeminiProvider

        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-2.5-flash"

        mock_genai = MagicMock()
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = MagicMock(text="Hello from Gemini")
        mock_genai.GenerativeModel.return_value = mock_model_instance
        mock_genai.GenerationConfig.return_value = MagicMock()
        provider._genai = mock_genai

        result = provider.generate("Say hello")
        assert result == "Hello from Gemini"
        mock_genai.GenerativeModel.assert_called_once()

    def test_is_retryable_rate_limit(self):
        from app.generation.gemini_provider import GeminiProvider

        assert GeminiProvider._is_retryable(Exception("429 RESOURCE_EXHAUSTED"))
        assert GeminiProvider._is_retryable(Exception("rate limit exceeded"))
        assert not GeminiProvider._is_retryable(Exception("invalid api key"))


# ---------------------------------------------------------------------- #
# OpenAIProvider
# ---------------------------------------------------------------------- #


class TestOpenAIProvider:
    def test_generate_returns_text(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello from OpenAI"))]
        mock_client.chat.completions.create.return_value = mock_response

        from app.generation.openai_provider import OpenAIProvider

        with patch.object(OpenAIProvider, "__init__", lambda self, *a, **kw: None):
            provider = OpenAIProvider.__new__(OpenAIProvider)
            provider._model = "gpt-4o-mini"
            provider._client = mock_client
            provider._openai = MagicMock()

            result = provider.generate("Say hello", system="Be brief")
            assert result == "Hello from OpenAI"

            # Verify system message was included.
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert messages[0] == {"role": "system", "content": "Be brief"}
            assert messages[1] == {"role": "user", "content": "Say hello"}

    def test_generate_handles_none_content(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        from app.generation.openai_provider import OpenAIProvider

        with patch.object(OpenAIProvider, "__init__", lambda self, *a, **kw: None):
            provider = OpenAIProvider.__new__(OpenAIProvider)
            provider._model = "gpt-4o"
            provider._client = mock_client
            provider._openai = MagicMock()

            result = provider.generate("test")
            assert result == ""

    def test_build_messages_no_system(self):
        from app.generation.openai_provider import OpenAIProvider

        with patch.object(OpenAIProvider, "__init__", lambda self, *a, **kw: None):
            provider = OpenAIProvider.__new__(OpenAIProvider)
            msgs = provider._build_messages("hello", None)
            assert len(msgs) == 1
            assert msgs[0] == {"role": "user", "content": "hello"}

    def test_build_messages_with_system(self):
        from app.generation.openai_provider import OpenAIProvider

        with patch.object(OpenAIProvider, "__init__", lambda self, *a, **kw: None):
            provider = OpenAIProvider.__new__(OpenAIProvider)
            msgs = provider._build_messages("hello", "system text")
            assert len(msgs) == 2
            assert msgs[0]["role"] == "system"


# ---------------------------------------------------------------------- #
# Factory — auto-fallback logic
# ---------------------------------------------------------------------- #


class TestFactory:
    def test_gemini_primary_when_key_present(self):
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "fake-key"
            mock_settings.gemini_main_model = "gemini-2.5-pro"

            with patch("app.generation.factory._try_gemini") as mock_try:
                mock_llm = MagicMock(spec=LLMProvider)
                mock_try.return_value = mock_llm

                from app.generation.factory import get_llm

                result = get_llm()
                assert result is mock_llm
                mock_try.assert_called_once_with("gemini-2.5-pro")

    def test_fallback_to_openai_when_gemini_fails(self):
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "fake-key"
            mock_settings.gemini_main_model = "gemini-2.5-pro"
            mock_settings.openai_api_key = "fake-oai-key"
            mock_settings.openai_main_model = "gpt-4o"

            mock_oai = MagicMock(spec=LLMProvider)

            with patch("app.generation.factory._try_gemini", return_value=None), \
                 patch("app.generation.factory._try_openai", return_value=mock_oai):

                from app.generation.factory import get_llm

                result = get_llm()
                assert result is mock_oai

    def test_fallback_to_gemini_when_openai_primary_fails(self):
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = "fake-key"
            mock_settings.openai_main_model = "gpt-4o"
            mock_settings.gemini_api_key = "fake-gem-key"
            mock_settings.gemini_main_model = "gemini-2.5-pro"

            mock_gem = MagicMock(spec=LLMProvider)

            with patch("app.generation.factory._try_openai", return_value=None), \
                 patch("app.generation.factory._try_gemini", return_value=mock_gem):

                from app.generation.factory import get_llm

                result = get_llm()
                assert result is mock_gem

    def test_raises_when_no_provider_available(self):
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = None
            mock_settings.openai_api_key = None
            mock_settings.gemini_main_model = "m"
            mock_settings.openai_main_model = "m"

            with patch("app.generation.factory._try_gemini", return_value=None), \
                 patch("app.generation.factory._try_openai", return_value=None):

                from app.generation.factory import LLMInitError, get_llm

                with pytest.raises(LLMInitError):
                    get_llm()

    def test_get_llm_cheap_uses_cheap_models(self):
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "fake"
            mock_settings.gemini_cheap_model = "gemini-2.5-flash"
            mock_settings.openai_cheap_model = "gpt-4o-mini"

            mock_llm = MagicMock(spec=LLMProvider)

            with patch("app.generation.factory._try_gemini", return_value=mock_llm) as mock_try:

                from app.generation.factory import get_llm_cheap

                result = get_llm_cheap()
                assert result is mock_llm
                mock_try.assert_called_once_with("gemini-2.5-flash")

    def test_explicit_provider_override(self):
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.openai_api_key = "fake"
            mock_settings.openai_base_url = None
            mock_settings.openai_main_model = "gpt-4o"
            mock_settings.gemini_main_model = "gemini-2.5-pro"

            mock_oai = MagicMock(spec=LLMProvider)

            with patch("app.generation.factory._try_openai", return_value=mock_oai), \
                 patch("app.generation.factory._try_gemini") as mock_gem:

                from app.generation.factory import get_llm

                # Force OpenAI even though config says Gemini.
                result = get_llm(provider="openai")
                assert result is mock_oai
                mock_gem.assert_not_called()

    def test_openai_provider_passes_base_url(self):
        """``_try_openai`` should pass ``settings.openai_base_url`` through."""
        with patch("app.generation.factory.settings") as mock_settings:
            mock_settings.openai_api_key = "fake-key"
            mock_settings.openai_base_url = "https://openrouter.ai/api/v1"

            with patch("app.generation.openai_provider.OpenAIProvider") as MockProv:
                mock_inst = MagicMock(spec=LLMProvider)
                MockProv.return_value = mock_inst

                from app.generation.factory import _try_openai

                result = _try_openai("deepseek/deepseek-chat-v3-0324:free")
                assert result is mock_inst
                MockProv.assert_called_once_with(
                    "deepseek/deepseek-chat-v3-0324:free",
                    api_key="fake-key",
                    base_url="https://openrouter.ai/api/v1",
                )
