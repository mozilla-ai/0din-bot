# agent.py

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fire import Fire
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger
from litellm import completion
from datetime import datetime
import json
from any_agent.tools.mcp_stdio import MCPStdio

load_dotenv()

# ========= Structured Output definition =========
class SummaryRow(BaseModel):
    user_handle: str = Field(..., description="The Discord handle of the user.")
    main_topic_of_concern: str = Field(..., description="The main topic this user posted about.")
    num_messages: int = Field(..., description="The number of messages from this user with essentially the same main topic.")

class StructuredOutput(BaseModel):
    summary_csv: str = Field(
        ..., description="CSV, where each row is: user_handle,main_topic_of_concern_the_user_posted_about,number_of_messages_with_the_same_topic"
    )
    file_path: str = Field(..., description="The relative path to the saved CSV summary file.")
    message_id: str = Field(..., description="The Discord message ID of the summary post.")

# ========= System Instructions =========
INSTRUCTIONS = '''
You are an assistant tasked with analyzing messages in a Discord channel. Follow this exact workflow:
1. When a message is received, analyze its content and context.
2. Identify the main topic of concern in the message.
3. Keep track of messages per user and their topics.
4. When requested (via a specific command), create a summary CSV in this schema: user_handle,main_topic_of_concern_the_user_posted_about,number_of_messages_with_the_same_topic (one row per main topic of each user).
5. Post the complete summary CSV as a single message to the same Discord channel, prepending the message with 'Topic Summary:'.
6. Save the summary CSV file locally with a timestamp in the filename, and confirm the relative path in your final output.
7. Return a JSON object containing: the summary_csv (as a string), the local file path, and the Discord message ID of your posted summary message.
'''

class MessageAnalyzerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Store message history
        self.message_history = {}
        
        # Initialize Discord MCP tool
        self.discord_mcp = MCPStdio(
            command="docker",
            args=[
                "run",
                "-i",
                "--rm",
                "-e",
                "DISCORD_TOKEN",
                "mcp/mcp-discord",
            ],
            env={"DISCORD_TOKEN": os.getenv("DISCORD_TOKEN")},
            tools=[
                "discord_read_messages",
                "discord_send"
            ],
        )

    async def setup_hook(self):
        # Register slash commands
        self.tree.add_command(app_commands.Command(
            name="summarize",
            description="Generate a summary of all messages in the current channel",
            callback=self.summarize
        ))
        self.tree.add_command(app_commands.Command(
            name="summarize-day",
            description="Generate a summary of messages from a specific day",
            callback=self.summarize_day
        ))
        await self.tree.sync()

    async def on_ready(self):
        logger.info(f'Logged in as {self.user}')
        await self.tree.sync()
        logger.info("Resynced global commands.")
        for guild in self.guilds:
            logger.info(f'Connected to guild: {guild.name} (id: {guild.id})')
            for channel in guild.text_channels:
                logger.info(f'  Text channel: {channel.name} (id: {channel.id})')

    async def on_message(self, message):
        # Don't respond to our own messages
        if message.author == self.user:
            return

        # Store message in history
        if message.channel.id not in self.message_history:
            self.message_history[message.channel.id] = []
        self.message_history[message.channel.id].append({
            'user': str(message.author),
            'content': message.content,
            'timestamp': message.created_at
        })

        # Process message with LLM to determine if it's a request for summarization
        system_prompt = """You are an assistant that analyzes Discord messages to determine if they are requests for message summarization.
        If the message is a request to summarize messages, you should:
        1. Determine if it's a request for a specific date or all messages
        2. If a date is mentioned, extract it in YYYY-MM-DD format
        3. Respond with a JSON object in this format:
           {
               "is_summarize_request": true/false,
               "target_date": "YYYY-MM-DD" or null,
               "explanation": "Brief explanation of your decision"
           }
        If the message is not a summarize request, set is_summarize_request to false.
        IMPORTANT: Your response must be valid JSON."""

        try:
            response = completion(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message.content}
                ]
            )
            
            # Parse the LLM response as JSON
            result_str = response.choices[0].message.content
            logger.info(f"LLM analysis result: {result_str}")
            
            try:
                result = json.loads(result_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response: {result_str}")
                return
            
            # Create a simple message sender for natural language commands
            async def send_message(content):
                await message.channel.send(content)

            # If it's a summarize request, process it
            if result.get("is_summarize_request", False):
                target_date = result.get("target_date")
                if target_date:
                    logger.info(f"LLM detected summarize request for date {target_date}")
                    await self.summarize_day(message.channel.id, target_date, send_message)
                else:
                    logger.info("LLM detected general summarize request")
                    await self.summarize(message.channel.id, send_message)

        except Exception as e:
            logger.error(f"Error processing message with LLM: {e}")

    def analyze_messages(self, messages):
        """Analyze messages using LLM to generate a summary."""
        # Prepare the messages for analysis
        messages_text = "\n".join([
            f"User: {msg['user']}\nMessage: {msg['content']}\nTimestamp: {msg['timestamp']}\n"
            for msg in messages
        ])

        system_prompt = """You are an expert at analyzing conversations and identifying main topics of discussion.
        Your task is to analyze the provided messages and create a CSV summary where:
        - Each row represents a unique user and their main topic of discussion
        - The CSV should have columns: user_handle,main_topic_of_concern,num_messages
        - Group messages by user and their main topic
        - Count how many messages each user has about each topic
        - Only include the most significant topics (ignore small talk, greetings, etc.)
        - Format the output as a valid CSV string"""

        user_prompt = f"Please analyze these messages and create a summary CSV:\n\n{messages_text}"

        try:
            response = completion(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            raise

    async def summarize(self, channel_id, send_message):
        """Generate a summary of all messages in the current channel."""
        logger.info(f"Received summarize command in channel {channel_id}")
        
        await send_message("Working on it...")
        
        if channel_id not in self.message_history:
            await send_message("No messages to summarize yet.")
            return

        try:
            # Get messages for this channel
            messages = self.message_history[channel_id]
            logger.info(f"Found {len(messages)} messages to summarize")
            
            # Generate summary using LLM
            summary_csv = self.analyze_messages(messages)
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"discord_summary_{timestamp}.csv"
            with open(filename, "w") as f:
                f.write(summary_csv)
            
            # Post the summary
            await send_message(f"Topic Summary:\n```\n{summary_csv}\n```")
            
            # Clear message history after successful summary
            self.message_history[channel_id] = []
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            await send_message(f"Error generating summary: {e}")

    async def summarize_day(self, channel_id, date_str, send_message):
        """Generate a summary of messages from a specific day.
        
        Args:
            date_str: The date to summarize in YYYY-MM-DD format
        """
        logger.info(f"Received summarize-day command in channel {channel_id} for date {date_str}")
        
        await send_message("Working on it...")
        
        try:
            # Parse the date
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Use Discord MCP to fetch messages for the target date
            channel = self.get_channel(channel_id)
            if not channel:
                await send_message("Could not find the channel.")
                return

            # Fetch messages using Discord MCP
            messages = await self.discord_mcp.discord_read_messages(
                channel_id=str(channel_id),
                start_date=target_date.isoformat(),
                end_date=target_date.isoformat()
            )
            
            if not messages:
                await send_message(f"No messages found for {date_str}")
                return

            # Convert messages to our format
            formatted_messages = [
                {
                    'user': msg['author']['username'],
                    'content': msg['content'],
                    'timestamp': datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                }
                for msg in messages
            ]
            
            logger.info(f"Found {len(formatted_messages)} messages to summarize for date {date_str}")
            
            # Generate summary using LLM
            summary_csv = self.analyze_messages(formatted_messages)
            
            if summary_csv is None:
                await send_message(f"No messages found for {date_str}")
                return
            
            # Save to file
            filename = f"discord_summary_{date_str}.csv"
            with open(filename, "w") as f:
                f.write(summary_csv)
            
            # Post the summary
            await send_message(f"Topic Summary for {date_str}:\n```\n{summary_csv}\n```")
            
        except ValueError:
            await send_message("Invalid date format. Please use YYYY-MM-DD (e.g., 2024-03-14)")
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            await send_message(f"Error generating summary: {e}")

def run_agent(guild_id: str, channel_id: str):
    """
    Run the message analyzer bot that listens for messages and can generate summaries.
    Args:
        guild_id (str): The Discord GUILD_ID (server) to connect to.
        channel_id (str): The Discord channel ID to monitor (e.g., '1378827407733035162').
    """
    bot = MessageAnalyzerBot()
    bot.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    Fire(run_agent)