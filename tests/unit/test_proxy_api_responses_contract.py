from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

import pytest

import app.modules.proxy.api as proxy_api_module
from app.core.openai.models import OpenAIErrorEnvelope

pytestmark = pytest.mark.unit


async def _iter_blocks(*blocks: str) -> AsyncIterator[str]:
    for block in blocks:
        yield block


@pytest.mark.asyncio
async def test_probe_stream_startup_error_surfaces_rate_limit_response_failed_event() -> None:
    stream, error = await proxy_api_module._probe_stream_startup_error(
        _iter_blocks(
            (
                'data: {"type":"response.failed","response":{"error":{"code":"rate_limit_exceeded",'
                '"type":"rate_limit_error","message":"slow down","resets_in_seconds":2}}}\n\n'
            )
        )
    )

    assert error is not None
    envelope = cast(OpenAIErrorEnvelope, error)
    assert envelope.error is not None
    assert envelope.error.code == "rate_limit_exceeded"
    assert envelope.error.resets_in_seconds == 2
    remaining = [block async for block in stream]
    assert remaining == []


@pytest.mark.asyncio
async def test_probe_stream_startup_error_keeps_non_rate_limit_response_failed_event_in_stream() -> None:
    stream, error = await proxy_api_module._probe_stream_startup_error(
        _iter_blocks(
            'data: {"type":"response.failed","response":{"error":{"code":"no_accounts","message":"none"}}}\n\n'
        )
    )

    assert error is None
    blocks = [block async for block in stream]
    assert len(blocks) == 1
    payload = proxy_api_module._parse_sse_payload(blocks[0])
    assert payload is not None
    assert payload["type"] == "response.failed"


def test_retry_after_header_from_rate_limit_error_content_uses_resets_in_seconds() -> None:
    envelope = proxy_api_module.OpenAIErrorEnvelopeModel.model_validate(
        {
            "error": {
                "code": "rate_limit_exceeded",
                "type": "rate_limit_error",
                "message": "slow down",
                "resets_in_seconds": 2,
            }
        }
    )

    headers = proxy_api_module._merge_rate_limit_retry_after_headers({}, envelope)

    assert headers["Retry-After"] == "2"


@pytest.mark.asyncio
async def test_collect_responses_payload_returns_contract_error_on_truncated_stream() -> None:
    result = await proxy_api_module._collect_responses_payload(
        _iter_blocks('data: {"type":"response.output_text.delta","delta":"hello"}\n\n')
    )

    body = result.model_dump(mode="json", exclude_none=True)
    assert body["error"]["code"] == "upstream_stream_truncated"


@pytest.mark.asyncio
async def test_collect_responses_payload_normalizes_unknown_output_item_to_message() -> None:
    result = await proxy_api_module._collect_responses_payload(
        _iter_blocks(
            (
                'data: {"type":"response.output_item.done","output_index":0,'
                '"item":{"id":"fa_1","type":"final_answer","text":"hello from final answer"}}\n\n'
            ),
            (
                'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
                '"status":"completed","output":[]}}\n\n'
            ),
        )
    )

    body = result.model_dump(mode="json", exclude_none=True)
    assert body["id"] == "resp_1"
    assert body["output"] == [
        {
            "id": "fa_1",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "hello from final answer"}],
        }
    ]


@pytest.mark.asyncio
async def test_normalize_public_responses_stream_appends_response_failed_on_invalid_json() -> None:
    blocks = [
        block
        async for block in proxy_api_module._normalize_public_responses_stream(_iter_blocks("data: {not-json}\n\n"))
    ]

    assert len(blocks) == 1
    payload = proxy_api_module._parse_sse_payload(blocks[0])
    assert payload is not None
    assert payload["type"] == "response.failed"
    response = payload["response"]
    assert isinstance(response, dict)
    error = response["error"]
    assert isinstance(error, dict)
    assert error["code"] == "invalid_json"


@pytest.mark.asyncio
async def test_normalize_public_responses_stream_normalizes_unknown_terminal_output_item() -> None:
    blocks = [
        block
        async for block in proxy_api_module._normalize_public_responses_stream(
            _iter_blocks(
                (
                    'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
                    '"status":"completed","output":[{"id":"fa_1","type":"final_answer","text":"normalized"}]}}\n\n'
                )
            )
        )
    ]

    assert len(blocks) == 2
    delta_payload = proxy_api_module._parse_sse_payload(blocks[0])
    assert delta_payload is not None
    assert delta_payload["type"] == "response.output_text.delta"
    assert delta_payload["delta"] == "normalized"
    payload = proxy_api_module._parse_sse_payload(blocks[1])
    assert payload is not None
    assert payload["type"] == "response.completed"
    response = payload["response"]
    assert isinstance(response, dict)
    output = response["output"]
    assert isinstance(output, list)
    assert output == [
        {
            "id": "fa_1",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "normalized"}],
        }
    ]


@pytest.mark.asyncio
async def test_normalize_public_responses_stream_synthesizes_delta_from_done_message() -> None:
    blocks = [
        block
        async for block in proxy_api_module._normalize_public_responses_stream(
            _iter_blocks(
                (
                    'data: {"type":"response.output_item.done","output_index":0,'
                    '"item":{"id":"msg_1","type":"message","role":"assistant",'
                    '"content":[{"type":"output_text","text":"visible text"}]}}\n\n'
                ),
                (
                    'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
                    '"status":"completed","output":[]}}\n\n'
                ),
            )
        )
    ]

    payloads = [proxy_api_module._parse_sse_payload(block) for block in blocks]
    assert payloads[0] == {
        "type": "response.output_text.delta",
        "output_index": 0,
        "content_index": 0,
        "delta": "visible text",
        "item_id": "msg_1",
    }
    assert payloads[1] is not None
    assert payloads[1]["type"] == "response.output_item.done"
    assert payloads[2] is not None
    assert payloads[2]["type"] == "response.completed"


@pytest.mark.asyncio
async def test_normalize_public_responses_stream_synthesizes_delta_from_completed_output() -> None:
    blocks = [
        block
        async for block in proxy_api_module._normalize_public_responses_stream(
            _iter_blocks(
                (
                    'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
                    '"status":"completed","output":[{"id":"msg_1","type":"message",'
                    '"content":[{"type":"output_text","text":"terminal text"}]}]}}\n\n'
                )
            )
        )
    ]

    payloads = [proxy_api_module._parse_sse_payload(block) for block in blocks]
    assert payloads[0] == {
        "type": "response.output_text.delta",
        "output_index": 0,
        "content_index": 0,
        "delta": "terminal text",
        "item_id": "msg_1",
    }
    assert payloads[1] is not None
    assert payloads[1]["type"] == "response.completed"


@pytest.mark.asyncio
async def test_normalize_public_responses_stream_does_not_duplicate_existing_delta() -> None:
    blocks = [
        block
        async for block in proxy_api_module._normalize_public_responses_stream(
            _iter_blocks(
                'data: {"type":"response.output_text.delta","item_id":"msg_1","delta":"already visible"}\n\n',
                (
                    'data: {"type":"response.output_item.done","output_index":0,'
                    '"item":{"id":"msg_1","type":"message","role":"assistant",'
                    '"content":[{"type":"output_text","text":"already visible"}]}}\n\n'
                ),
                (
                    'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
                    '"status":"completed","output":[]}}\n\n'
                ),
            )
        )
    ]

    payloads = [proxy_api_module._parse_sse_payload(block) for block in blocks]
    event_types = [payload["type"] for payload in payloads if payload is not None]
    assert event_types == [
        "response.output_text.delta",
        "response.output_item.done",
        "response.completed",
    ]


@pytest.mark.asyncio
async def test_collect_responses_payload_preserves_apply_patch_call_output_item() -> None:
    result = await proxy_api_module._collect_responses_payload(
        _iter_blocks(
            (
                'data: {"type":"response.output_item.done","output_index":0,'
                '"item":{"id":"apc_1","type":"apply_patch_call","status":"completed",'
                '"call_id":"call_1","patch":"*** Begin Patch\\n*** End Patch\\n"}}\n\n'
            ),
            (
                'data: {"type":"response.completed","response":{"id":"resp_1","object":"response",'
                '"status":"completed","output":[]}}\n\n'
            ),
        )
    )

    body = result.model_dump(mode="json", exclude_none=True)
    assert body["id"] == "resp_1"
    assert body["output"] == [
        {
            "id": "apc_1",
            "type": "apply_patch_call",
            "status": "completed",
            "call_id": "call_1",
            "patch": "*** Begin Patch\n*** End Patch\n",
        }
    ]


@pytest.mark.asyncio
async def test_collect_responses_payload_preserves_mcp_approval_request_output_item() -> None:
    result = await proxy_api_module._collect_responses_payload(
        _iter_blocks(
            (
                'data: {"type":"response.output_item.done","output_index":0,'
                '"item":{"id":"mcp_1","type":"mcp_approval_request","status":"in_progress",'
                '"request_id":"req_1","server_label":"github","tool_name":"repos/list"}}\n\n'
            ),
            (
                'data: {"type":"response.completed","response":{"id":"resp_2","object":"response",'
                '"status":"completed","output":[]}}\n\n'
            ),
        )
    )

    body = result.model_dump(mode="json", exclude_none=True)
    assert body["id"] == "resp_2"
    assert body["output"] == [
        {
            "id": "mcp_1",
            "type": "mcp_approval_request",
            "status": "in_progress",
            "request_id": "req_1",
            "server_label": "github",
            "tool_name": "repos/list",
        }
    ]


@pytest.mark.asyncio
async def test_collect_responses_payload_preserves_output_image_item() -> None:
    result = await proxy_api_module._collect_responses_payload(
        _iter_blocks(
            (
                'data: {"type":"response.output_item.done","output_index":0,'
                '"item":{"id":"img_1","type":"output_image","image_url":"https://example.com/a.png"}}\n\n'
            ),
            (
                'data: {"type":"response.completed","response":{"id":"resp_3","object":"response",'
                '"status":"completed","output":[]}}\n\n'
            ),
        )
    )

    body = result.model_dump(mode="json", exclude_none=True)
    assert body["id"] == "resp_3"
    assert body["output"] == [
        {
            "id": "img_1",
            "type": "output_image",
            "image_url": "https://example.com/a.png",
        }
    ]
