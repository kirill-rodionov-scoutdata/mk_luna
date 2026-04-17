from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def make_mock_http_client():
    def _factory(post_return: Any = None, post_side_effect: Any = None) -> AsyncMock:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        if post_side_effect is not None:
            mock_client.post = AsyncMock(side_effect=post_side_effect)
        else:
            mock_client.post = AsyncMock(return_value=post_return or mock_response)

        return mock_client

    return _factory
