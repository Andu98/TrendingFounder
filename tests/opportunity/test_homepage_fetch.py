"""Tests for homepage fetch logic."""

import pytest
from unittest.mock import patch, AsyncMock
from src.opportunity.update_opportunity_scores import fetch_homepage_excerpt


@pytest.mark.asyncio
async def test_fetch_homepage_excerpt_from_html():
    """Test extraction from a well-formed HTML page."""
    html = """
    <html>
    <head>
        <title>Test Product - AI Tool</title>
        <meta name="description" content="An AI-powered productivity tool.">
    </head>
    <body>
        <h1>Welcome to Test Product</h1>
        <h2>Features</h2>
        <h2>Pricing</h2>
        <p>This is a comprehensive AI tool that helps you be more productive.</p>
    </body>
    </html>
    """
    
    mock_response = AsyncMock()
    mock_response.text = html
    mock_response.raise_for_status = lambda: None
    
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)
    
    with patch("src.opportunity.update_opportunity_scores.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_homepage_excerpt("https://test.com")
        assert result is not None
        assert "Test Product" in result
        assert "AI-powered productivity" in result


@pytest.mark.asyncio
async def test_fetch_homepage_excerpt_on_failure():
    """Test that failures return None without raising."""
    import httpx
    
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    
    with patch("src.opportunity.update_opportunity_scores.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_homepage_excerpt("https://nonexistent.com")
        assert result is None
