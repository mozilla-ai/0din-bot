# agent.py

import os
from dotenv import load_dotenv
from loguru import logger
import discord
from discord import app_commands
from discord.ext import commands
from openai import OpenAI
from datetime import datetime, timedelta
import json
import asyncio

# Configure logger
logger.add("bot.log", rotation="1 day", retention="7 days", level="DEBUG")

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class MessageAnalyzerBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing MessageAnalyzerBot...")
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        # Store pending summary requests
        self.pending_requests = {}

    async def setup_hook(self):
        logger.info("Setting up bot hooks...")
        # Register slash commands
        self.tree.add_command(app_commands.Command(
            name="check",
            description="Check the status of the bot",
            callback=self.check_command
        ))
        await self.tree.sync()
        logger.info("Slash commands registered")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user}')
        await self.tree.sync()
        logger.info("Resynced global commands.")

    async def check_command(self, interaction: discord.Interaction):
        """Handle the /check command."""
        logger.debug(f"Received /check command from {interaction.user}")
        await interaction.response.send_message("Bot is operational!")

    async def get_channel_history(self, channel, date=None, limit=1000):
        """Get message history from a channel for a specific date."""
        messages = []
        async for message in channel.history(limit=limit):
            if date:
                # If date is specified, only include messages from that date
                if message.created_at.date() == date:
                    messages.append({
                        'author': str(message.author),
                        'content': message.content,
                        'timestamp': message.created_at.isoformat()
                    })
            else:
                # If no date specified, include all messages
                messages.append({
                    'author': str(message.author),
                    'content': message.content,
                    'timestamp': message.created_at.isoformat()
                })
        return messages

    async def analyze_messages(self, messages, query, user_id):
        """Use OpenAI to analyze messages and respond to the query."""
        try:
            # Prepare the conversation for the LLM
            conversation = [
                {"role": "system", "content": """You are a helpful assistant that analyzes Discord messages.
                Your primary function is to understand what action items arise from channel activity.
                
                When a user asks for a summary and only in that case:
                1. If they don't specify a date, ask them which date they want to summarize
                2. If they specify a date, provide a summary of messages from that date. The date can be in any format (e.g., "June 11th", "11th June", "June 11", "11/6", etc.). Always interpret the date correctly and use it to filter messages.
                3. If they don't specify a year, assume the current year,
                4. Use the Discord tool to access message history, read the messages and provide a summary of the main topics and discussions.
                
                Your response should be:
                - A request for a date if none is specified. If you did not understand the date, repeat it between quotes so the user can correct it.
                - A clear summary of the main topics and discussions if a date is provided. The summary should have the format shown below.
                - A message indicating no messages were found if the date has no activity
                
                The correct format for the summary should be similar to a csv file with columns, including the header:
                user, topic, number of messages

                For example:
                '''
                user, topic, number of messages
                Alex#123, payment, 1
                Stefan#223, submission, 2
                Irina#231, general questions, 1
                '''
                Keep your responses concise and focused on the summary request. Do NOT hallucinate messages or any content.
                
                IMPORTANT: You have access to the actual messages through the messages parameter. Use these messages to create your summary. Do not make up or hallucinate any content."""},
                {"role": "user", "content": f"Here are the messages from the channel:\n{json.dumps(messages, indent=2)}\n\n"
                 f"Query: {query}\n\nPlease analyze these messages and respond appropriately."}
            ]

            # Get response from OpenAI using the new API
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4.1",
                messages=conversation,
                temperature=0.1,
                max_tokens=5000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in analyze_messages: {e}")
            logger.exception("Full traceback:")
            return "I encountered an error while analyzing the messages."

    async def on_message(self, message):
        # Don't respond to our own messages
        if message.author == self.user:
            return

        # Check if the message is directed at the bot
        is_directed = (
            message.reference and 
            message.reference.resolved and 
            message.reference.resolved.author == self.user
        ) or any(mention.id == self.user.id for mention in message.mentions)

        if not is_directed:
            await message.channel.send("Nah")
            return

        logger.debug(f"Received directed message from {message.author}: {message.content}")

        try:
            # Get message history
            messages = await self.get_channel_history(message.channel)
            
            # Analyze messages and get response
            response = await self.analyze_messages(messages, message.content, message.author.id)
            
            # Check if the response is asking for a date
            if "which date" in response.lower() or "what date" in response.lower():
                # Store the pending request
                self.pending_requests[message.author.id] = True
            
            # Send response
            await message.channel.send(response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception("Full traceback:")
            await message.channel.send("I encountered an error while processing your request.")

def run_agent(guild_id: str, channel_id: str):
    """
    Run the message analyzer bot that monitors a Discord channel.
    Args:
        guild_id (str): The Discord GUILD_ID (server) to connect to.
        channel_id (str): The Discord channel ID to monitor.
    """
    logger.info(f"Starting bot for guild {guild_id}, channel {channel_id}")
    bot = MessageAnalyzerBot()
    bot.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    from fire import Fire
    Fire(run_agent)