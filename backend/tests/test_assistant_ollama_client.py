"""Tests for the Ollama HTTP client — connection, chat, streaming, health."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.assistant.ollama_client import OllamaClient
from app.observability import current_request_id, current_trace_id


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestOllamaClientInit:
    def test_stores_config(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b", timeout=60)
        assert client._base_url == "http://localhost:11434"
        assert client._model == "llama3.1:8b"
        assert client._timeout == 60

    def test_strips_trailing_slash(self):
        client = OllamaClient("http://localhost:11434/", "model")
        assert client._base_url == "http://localhost:11434"


# ---------------------------------------------------------------------------
# Non-streaming chat
# ---------------------------------------------------------------------------


class TestChat:
    def test_chat_sends_correct_payload(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Hello"}}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        with patch.object(OllamaClient, "_get_client", return_value=mock_http):
            result = _run(
                client.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    tools=[{"type": "function", "function": {"name": "test"}}],
                    temperature=0.2,
                    max_tokens=512,
                    num_ctx=4096,
                )
            )

        assert result == {"message": {"content": "Hello"}}
        call_args = mock_http.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["model"] == "llama3.1:8b"
        assert payload["stream"] is False
        assert payload["keep_alive"] == "30m"
        assert payload["options"]["temperature"] == 0.2
        assert payload["options"]["num_predict"] == 512
        assert payload["options"]["num_ctx"] == 4096
        assert len(payload["tools"]) == 1

    def test_chat_without_tools(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Hi"}}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        with patch.object(OllamaClient, "_get_client", return_value=mock_http):
            _run(client.chat(messages=[{"role": "user", "content": "Hi"}]))

        payload = mock_http.post.call_args.kwargs.get("json") or mock_http.post.call_args[1].get(
            "json"
        )
        assert "tools" not in payload

    def test_chat_without_num_ctx(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Hi"}}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        with patch.object(OllamaClient, "_get_client", return_value=mock_http):
            _run(client.chat(messages=[{"role": "user", "content": "Hi"}], num_ctx=None))

        payload = mock_http.post.call_args.kwargs.get("json") or mock_http.post.call_args[1].get(
            "json"
        )
        assert "num_ctx" not in payload["options"]

    def test_chat_forwards_request_and_trace_headers(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Hi"}}
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        request_token = current_request_id.set("request-123")
        trace_token = current_trace_id.set("trace-123")
        try:
            with patch.object(OllamaClient, "_get_client", return_value=mock_http):
                _run(client.chat(messages=[{"role": "user", "content": "Hi"}]))
        finally:
            current_request_id.reset(request_token)
            current_trace_id.reset(trace_token)

        headers = mock_http.post.call_args.kwargs.get("headers") or mock_http.post.call_args[1].get(
            "headers"
        )
        assert headers["X-Request-ID"] == "request-123"
        assert headers["X-Trace-ID"] == "trace-123"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_healthy_when_model_exists(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        with patch.object(
            client, "list_models", new_callable=AsyncMock, return_value=["llama3.1:8b", "mistral"]
        ):
            assert _run(client.is_healthy()) is True

    def test_unhealthy_when_model_missing(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        with patch.object(client, "list_models", new_callable=AsyncMock, return_value=["mistral"]):
            assert _run(client.is_healthy()) is False

    def test_unhealthy_on_connection_error(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        with patch.object(
            client,
            "list_models",
            new_callable=AsyncMock,
            side_effect=Exception("connection refused"),
        ):
            assert _run(client.is_healthy()) is False


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------


class TestWarmup:
    def test_warmup_sends_minimal_request(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.is_closed = False

        with patch.object(OllamaClient, "_get_client", return_value=mock_http):
            _run(client.warmup())

        payload = mock_http.post.call_args.kwargs.get("json") or mock_http.post.call_args[1].get(
            "json"
        )
        assert payload["options"]["num_predict"] == 1
        assert payload["keep_alive"] == "30m"

    def test_warmup_handles_failure_gracefully(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_http = AsyncMock()
        mock_http.post.side_effect = Exception("connection refused")
        mock_http.is_closed = False

        with patch.object(OllamaClient, "_get_client", return_value=mock_http):
            _run(client.warmup())  # Should not raise


# ---------------------------------------------------------------------------
# List models
# ---------------------------------------------------------------------------


class TestListModels:
    def test_list_models(self):
        client = OllamaClient("http://localhost:11434", "llama3.1:8b")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "mistral:7b"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get.return_value = mock_resp
        mock_http.is_closed = False

        with patch.object(OllamaClient, "_get_client", return_value=mock_http):
            models = _run(client.list_models())

        assert models == ["llama3.1:8b", "mistral:7b"]
