"""Real-API-only structured-output smoke test for DeepSeek V4 Flash."""

import os

import pytest
from pydantic import BaseModel

from tradingagents.llm_clients.openai_client import DeepSeekChatOpenAI


def _has_real_deepseek_key() -> bool:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    return bool(key) and key != "placeholder"


@pytest.mark.integration
@pytest.mark.skipif(
    not _has_real_deepseek_key(),
    reason="DEEPSEEK_API_KEY not set (or placeholder); skipping live API call",
)
class TestDeepSeekLiveStructuredOutput:
    """Preserved upstream live test; never part of the default offline suite."""

    class _Pick(BaseModel):
        action: str
        confidence: float

    def test_v4_flash_returns_structured_output(self):
        client = DeepSeekChatOpenAI(
            model="deepseek-v4-flash",
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
            timeout=60,
        )
        bound = client.with_structured_output(self._Pick)
        result = bound.invoke(
            "Pick BUY or SELL or HOLD for a tech stock with strong earnings. "
            "Confidence is a float between 0 and 1."
        )
        assert isinstance(result, self._Pick)
        assert result.action in {"BUY", "SELL", "HOLD"}
        assert 0.0 <= result.confidence <= 1.0
