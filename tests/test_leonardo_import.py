import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("LEONARDO_API_KEY"),
    reason="No LEONARDO_API_KEY; import-only smoke",
)


def test_leonardo_import():
    from leonardo_ai_sdk import LeonardoAiSDK

    assert LeonardoAiSDK is not None
