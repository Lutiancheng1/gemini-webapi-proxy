"""Unit tests for WebAPIClient upstream refusal handling."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from gemini_webapi_proxy.client.webapi import WebAPIClient
from gemini_webapi_proxy.errors import UpstreamRefusalError


@pytest.mark.asyncio
async def test_generate_content_raises_on_cannot_fulfill() -> None:
    client = WebAPIClient("psid", "psidts")
    refusal_output = SimpleNamespace(
        text="I cannot fulfill this request.",
        images=[],
    )
    with (
        patch.object(
            client._client,
            "generate_content",
            new=AsyncMock(return_value=refusal_output),
        ),
        pytest.raises(UpstreamRefusalError, match="cannot fulfill"),
    ):
        await client.generate_content("describe style", files=None, model="gemini-3-flash")


@pytest.mark.asyncio
async def test_generate_content_allows_json_style_answer() -> None:
    client = WebAPIClient("psid", "psidts")
    ok_output = SimpleNamespace(
        text='{"title_zh":"测试","scene_rules":"水彩插画。"}',
        images=[],
    )
    with patch.object(
        client._client,
        "generate_content",
        new=AsyncMock(return_value=ok_output),
    ):
        result = await client.generate_content("describe style", files=None, model="gemini-3-flash")
    assert "水彩" in result.text
