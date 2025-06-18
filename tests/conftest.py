import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_env_vars():
    """Fixture to set up mock environment variables for testing."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("DISCORD_TOKEN", "test-token")
        m.setenv("ODIN_API_KEY", "test-api-key")
        yield

@pytest.fixture
def mock_discord_message():
    """Fixture to create a mock Discord message."""
    message = AsyncMock()
    message.author = AsyncMock()
    message.author.id = 123
    message.content = "Test message"
    message.channel = AsyncMock()
    message.mentions = []
    message.reference = None
    return message

@pytest.fixture
def mock_discord_interaction():
    """Fixture to create a mock Discord interaction."""
    interaction = AsyncMock()
    interaction.user = AsyncMock()
    interaction.user.id = 123
    interaction.response = AsyncMock()
    return interaction 