from any_agent import AgentConfig
import pytest
from unittest.mock import AsyncMock, patch, PropertyMock, MagicMock
from odinbot.agent import (
    MessageAnalyzerBot,
    UserTopicSummary,
    SummaryOutput,
    SubmissionOutput,
    SubmissionStatus,
    AgentResponse,
    StructuredOutput
)

class AsyncContextManagerMock:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): return None

def test_format_message_methods():
    # SummaryOutput
    summaries = [
        UserTopicSummary(user_handle="user1", topic="topic1", message_count=3),
        UserTopicSummary(user_handle="user2", topic="topic2", message_count=2)
    ]
    output = SummaryOutput(
        type="summary",
        date="2024-03-20",
        channel_id="123456",
        summaries=summaries,
        file_path="logs/test.txt"
    )
    formatted = output.format_message()
    assert "2024-03-20" in formatted
    assert "user1" in formatted
    assert "topic1" in formatted

    # SubmissionOutput
    submission_status = SubmissionStatus(
        uuid="test-uuid",
        status="processed",
        details="Test details"
    )
    sub_output = SubmissionOutput(
        type="submission_status",
        uuid="test-uuid",
        submission_status=submission_status
    )
    assert "test-uuid" in sub_output.format_message()

    # AgentResponse
    response = AgentResponse(
        type="agent_response",
        response_type="clarification",
        message="Test message"
    )
    assert "Test message" in response.format_message()

@pytest.mark.asyncio
async def test_health_command():
    bot = MessageAnalyzerBot(guild_id="123", channel_id="456")
    interaction = AsyncMock()
    await bot.health_command(interaction)
    interaction.response.send_message.assert_called_once_with("Bot is operational!")

@pytest.mark.asyncio
async def test_check_command():
    bot = MessageAnalyzerBot(guild_id="123", channel_id="456")
    interaction = AsyncMock()
    test_uuid = "test-uuid"
    with patch('odinbot.agent.check_submission', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = "Test result"
        await bot.check_command(interaction, test_uuid)
        mock_check.assert_called_once_with(test_uuid)
        interaction.response.send_message.assert_called_once_with("Test result")

@pytest.mark.asyncio
async def test_on_message():
    bot = MessageAnalyzerBot(guild_id="123", channel_id="456")
    with patch.object(type(bot), 'user', new_callable=PropertyMock) as mock_user:
        mock_user_instance = AsyncMock()
        mock_user_instance.id = 42
        mock_user.return_value = mock_user_instance

        # Not directed at bot
        message = AsyncMock()
        message.author = AsyncMock()
        message.author.id = 789
        message.mentions = []
        message.reference = None
        message.channel = AsyncMock()
        message.channel.typing = lambda: AsyncContextManagerMock()
        await bot.on_message(message)
        assert not message.channel.send.called

        # Directed at bot
        message = AsyncMock()
        message.author = AsyncMock()
        message.author.id = 789
        mention = AsyncMock()
        mention.id = mock_user_instance.id
        message.mentions = [mention]
        message.content = "Test message"
        message.reference = None
        message.channel = AsyncMock()
        message.channel.typing = lambda: AsyncContextManagerMock()
        mock_agent = AsyncMock()
        agent_response = AgentResponse(
            type="agent_response",
            response_type="response",
            message="Test response"
        )
        structured_output = StructuredOutput(response=agent_response)
        mock_agent.run_async.return_value = MagicMock(
            final_output=structured_output,
            model_dump_json=MagicMock(return_value="{}")
        )
        bot.agent = mock_agent
        await bot.on_message(message)
        mock_agent.run_async.assert_called_once_with(prompt="Test message")
        message.channel.send.assert_called_once_with("Test response")


def test_accepted_agent_config():
    """ This test makes sure that we can create an agent config with the complex output type"""
    agent = AgentConfig(
        model_id="o3",
        output_type=StructuredOutput,
        instructions="You are a helpful assistant.",
        tools=[],
        model_args={"tool_choice": "required"}
    )
    assert agent.output_type == StructuredOutput