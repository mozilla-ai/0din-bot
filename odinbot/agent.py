# agent.py

import os
from typing import List, Literal, Union
from dotenv import load_dotenv
from loguru import logger
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from any_agent import AgentConfig, AnyAgent
from any_agent.config import MCPStdio
from pydantic import BaseModel, Field
from odinbot.tools.odin import check_submission, get_threatfeed

# Configure logger
logger.add("bot.log", rotation="1 day", retention="7 days", level="DEBUG")

load_dotenv()

# ========= Structured output definition =========
class UserTopicSummary(BaseModel):
    user_handle: str = Field(..., description="Discord username or nickname of the poster")
    topic: str = Field(..., description="Main topic the user posted about on the given date")
    message_count: int = Field(..., description="Number of messages the user posted about that topic on that date")

class SubmissionStatus(BaseModel):
    uuid: str = Field(..., description="The UUID of the submission being checked")
    status: str = Field(..., description="The status of the submission, either 'processed' or 'not_processed'")
    details: str = Field(..., description="Additional details about the submission status")

class SummaryOutput(BaseModel):
    type: Literal["summary"] = "summary"
    date: str = Field(..., description="ISO formatted date (YYYY-MM-DD) that was summarised")
    channel_id: str = Field(..., description="Discord channel ID that was summarised")
    summaries: List[UserTopicSummary] = Field(..., description="List of unique users with their main topic and message count")
    file_path: str = Field(..., description="Relative file path where the summary was saved locally")

    def format_message(self) -> str:
        summary_lines = []
        for user_summary in self.summaries:
            summary_lines.append(
                f"**{user_summary.user_handle}**: {user_summary.topic} "
                f"({user_summary.message_count} messages)"
            )
        
        return (
            f"📊 Summary for {self.date}\n\n" +
            "\n".join(summary_lines) +
            f"\n\nSummary saved to: `{self.file_path}`"
        )

class SubmissionOutput(BaseModel):
    type: Literal["submission_status"] = "submission_status"
    uuid: str = Field(..., description="The UUID of the submission being checked")
    submission_status: SubmissionStatus = Field(..., description="Status of a submission check")

    def format_message(self) -> str:
        status = self.submission_status
        return (
            f"🔍 Submission Status for {status.uuid}\n"
            f"Status: {status.status}\n"
            f"Details: {status.details}"
        )

class AgentResponse(BaseModel):
    type: Literal["agent_response"] = "agent_response"
    response_type: str = Field(..., description="The type of response (e.g., 'refusal', 'question', 'clarification')")
    message: str = Field(..., description="The actual response message from the agent")

    def format_message(self) -> str:
        return f"{self.message}"

StructuredOutput = Union[SummaryOutput, SubmissionOutput, AgentResponse]

# ========= System Instructions =========
INSTRUCTIONS_TEMPLATE = """You are a Discord assistant agent embedded in server ID {guild_id} and channel ID {channel_id}.
Follow this deterministic multi-step workflow for every user message you receive:

1. INTENT CHECK  ➜  This is the most important step. First decide whether the user's intent is more towards getting insight and/or summaries of discord messages or checking ODIN submissions. Depending on that, 
look at custom instructions and hints for each intent below.

A) MESSAGE SUMMARY INTENTS: 
    1. DATE RESOLUTION ➜  Determine the target date to summarise.
    • If the user explicitly mentions a calendar date in any format (if they use numbers, ask them to clarify if it's MM-DD or DD-MM) and later use that date to filter.
    • If they don't specify a date, don't assume for now and leave it empty.

    2. READ MESSAGES ➜  Call `discord_read_messages` with the date the user provided and "channel_id": "{channel_id}".

    3. OPTIONAL FILTERING:
    • If the user requested messages of a specific user, filter by that specific user.
    • If the user specified a date follow the steps i to iv.
        i. Check the first retrieved message's date. If the year was unknown, take the one from this message. If the requested date is before this first message's date, proceed to Step 5 with the output "I can only see as early as <date_of_first_message>".
        ii. Store the resolved date as string ISO-formatted YYYY-MM-DD.
        iii. Filter the returned messages, keeping only those whose timestamp matches the resolved date (UTC).
    • If no messages exist after filtering, proceed to Step 4.    

    3. ANALYSE TOPICS ➜  For the remaining messages:
    • Read the user's request carefully and tray to answer their question with the messages you retrieved and the tools available to you.
    • If you were asked for a global summary of topics, group messages by **author username**.
        • For each user, analyse the content of all their messages to identify the **main topic of concern** (few-word description).
            – Use semantic similarity: pick the most recurring subject or summarise the common theme.
        • Count how many messages from that user relate to that topic (length of that user's message list).
        • Create rows in the form: `user_handle, topic, message_count`.
   • For other questions on messages, again, use the tools available and analyse the messages with the user's request in mind. Do not make up information, use what you see in the retrieved messages.

    5. SAVE OUTPUT ➜  Save the summary text locally to
    `logs/discord_daily_summary_<date>.txt`.

    6. FINAL JSON OUTPUT ➜  Respond with a Structured JSON object having:
    – date, channel_id, summaries (array of objects with user_handle, topic, message_count), file_path (relative path saved in Step 6).

   

B) ODIN API or SUBMISSION INFORMATION:
1. UUID EXTRACTION ➜  For submission checks:
   • Extract the UUID from the user's message. The UUID should be a valid UUID v4 format.
   • If no valid UUID is found in the message, respond with a polite message asking for a valid UUID.
   • If a valid UUID is found, proceed to Step 8.

2. SUBMISSION CHECK ➜  Call `check_submission` with:
   {{
     "uuid": "<extracted_uuid>"
   }}
   • If the submission is not found, respond with: "Submission not found."

3. SUBMISSION FINAL JSON OUTPUT ➜  Respond with a Structured JSON object having:
   – uuid, submission status.


General rules:
• ALWAYS use the provided tools for reading and sending Discord messages – do NOT invent data.
• NEVER expose raw tool responses or internal reasoning to the end-user.
• Keep all tool calls minimal and correct.
• Always remember to do the INTENT CHECK first and skip the tools if the intent is not supported. 
"""


class MessageAnalyzerBot(commands.Bot):
    def __init__(self, guild_id: str, channel_id: str) -> None:
        """Initialize the Discord bot with message content intent.
        
        Args:
            guild_id: The Discord server ID to connect to
            channel_id: The Discord channel ID to monitor
        """
        logger.info("Initializing MessageAnalyzerBot...")
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.agent = None  # Will be initialized in setup_hook
        self.guild_id = guild_id
        self.channel_id = channel_id
        os.makedirs("logs", exist_ok=True)         

    async def _create_agent(self) -> AnyAgent:
        """Create the AnyAgent instance with MCP tools asynchronously.
        
        Returns:
            AnyAgent: The configured agent instance.
        """
        instructions = INSTRUCTIONS_TEMPLATE.format(
            guild_id=self.guild_id,
            channel_id=self.channel_id
        )
        
        return await AnyAgent.create_async(
            "openai",
            AgentConfig(
                model_id="o3",
                instructions=instructions,
                tools=[
                    MCPStdio(
                        command="docker",
                        args=[
                            "run",
                            "-i",
                            "--rm",
                            "-e",
                            "DISCORD_TOKEN",
                            "mcp/mcp-discord",
                        ],
                        env={
                            "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN"),
                        },
                        tools=[
                            "test",
                            "discord_read_messages",
                            "discord_login",
                            "discord_send",
                        ],
                        client_session_timeout_seconds=30.0,  # Increased timeout to 60 seconds
                    ),
                    check_submission,
                    get_threatfeed,

                ],
                agent_args={"output_type": StructuredOutput},
                model_args={"tool_choice": "required"},
            ),
        )

    async def setup_hook(self) -> None:
        """Set up bot hooks and register slash commands."""
        logger.info("Setting up bot hooks...")
        # Initialize the agent
        self.agent = await self._create_agent()
        logger.info("Agent initialized successfully")
        
        # Register slash commands
        self.tree.add_command(app_commands.Command(
            name="health",
            description="Check the status of the bot",
            callback=self.health_command
        ))
        self.tree.add_command(app_commands.Command(
            name="check",
            description="Check a UUID in the ODIN threat feed",
            callback=self.check_command
        ))
        await self.tree.sync()
        logger.info("Slash commands registered")

    async def on_ready(self) -> None:
        """Handle bot ready event."""
        logger.info(f'Logged in as {self.user}')
        logger.info("Bot is ready!")

    async def health_command(self, interaction: discord.Interaction) -> None:
        """Handle the /health command.
        
        Args:
            interaction: The Discord interaction object.
        """
        logger.debug(f"Received /health command from {interaction.user}")
        await interaction.response.send_message("Bot is operational!")

    async def check_command(self, interaction: discord.Interaction, uuid: str) -> None:
        """Handle the /check command.
        
        Args:
            interaction: The Discord interaction object.
            uuid: The UUID to check in the ODIN threat feed.
        """
        logger.debug(f"Received /check command from {interaction.user} for UUID {uuid}")
        
        result = await check_submission(uuid)
        await interaction.response.send_message(result)

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages.
        
        Args:
            message: The Discord message that was received.
        """
        # Don't respond to our own messages
        if message.author == self.user:
            return

        # Check if the message is directed at the bot
        is_directed: bool = (
            message.reference and 
            message.reference.resolved and 
            message.reference.resolved.author == self.user
        ) or any(mention.id == self.user.id for mention in message.mentions)

        if not is_directed:
            return
        logger.debug(f"Received directed message from {message.author}: {message.content}")

        try:
            # Show typing indicator while processing
            async with message.channel.typing():
                logger.info("Starting agent processing...")
                # Run the agent directly in the async context
                agent_trace = await self.agent.run_async(prompt=message.content)
                logger.info("Agent processing completed successfully")
                
                timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
                trace_filename: str = f"logs/{timestamp}_agent_trace.json"
                
                with open(trace_filename, "w", encoding="utf-8") as f:
                    f.write(agent_trace.model_dump_json(indent=2))
                logger.info(f"Trace saved to {trace_filename}")

                # Get the structured output from the trace
                if not hasattr(agent_trace, 'final_output') or not agent_trace.final_output:
                    await message.channel.send("I couldn't process your request. Please try again in a few moments.")
                    return

                logger.debug(f"Final output type: {type(agent_trace.final_output)}")

                # Format and send the response message
                if isinstance(agent_trace.final_output, (SummaryOutput, SubmissionOutput, AgentResponse)):
                    response_message = agent_trace.final_output.format_message()
                    await message.channel.send(response_message)
                else:
                    await message.channel.send("I couldn't process your request. Please try again in a few moments.")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception("Full traceback:")
            await message.channel.send("I encountered an error while processing your request. Please try again in a few moments.")

def run_agent(guild_id: str, channel_id: str) -> None:
    """Run the message analyzer bot that monitors a Discord channel.
    
    Args:
        guild_id: The Discord GUILD_ID (server) to connect to.
        channel_id: The Discord channel ID to monitor.
    """
    logger.info(f"Starting bot for guild {guild_id}, channel {channel_id}")
    bot: MessageAnalyzerBot = MessageAnalyzerBot(guild_id=guild_id, channel_id=channel_id)
    bot.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    from fire import Fire
    Fire(run_agent)