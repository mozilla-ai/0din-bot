"""
A Discord bot that responds to 'hello' and handles '@Bot /check <UUID>' commands by querying the ODIN Threatfeed API.
"""
import os
import discord
from loguru import logger
from discord import app_commands
from odinbot.tools.odin import (
    check_submission,
    SCANNED_MSG,
    NOT_SCANNED_MSG
)

# === Discord User-Facing Messages ===
NO_UUID_MSG: str = "Please provide a UUID after /check, e.g. '@agent /check myUUID'"
USAGE_INSTRUCTIONS_MSG: str = "If you want me to check your submission, @ me and write '/check UUID'"
HELLO_RESPONSE: str = "world!"
IS_UUID_VALID_MSG: str = "Did you provide a valid UUID?"

intents = discord.Intents.default()
intents.message_content = True

def parse_scan_result(data: dict) -> str:
    """Extracts and formats the scan result from the API response."""
    for item in data.get("metadata", []):
        if item.get("type") == "ScannerModule":
            scanned = item.get("result")
            if scanned == 1:
                return SCANNED_MSG
            elif scanned == 0 or scanned is None:
                return NOT_SCANNED_MSG
    # If no ScannerModule or unexpected result, show full JSON
    import json
    return f"```json\n{json.dumps(data, indent=2)}\n```"

class MyClient(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        guild_id = os.environ.get("GUILD_ID")
        if not guild_id:
            raise RuntimeError("GUILD_ID environment variable not set.")
        guild = discord.Object(id=int(guild_id))
        await self.tree.sync(guild=guild)

client = MyClient()

@client.event
async def on_ready() -> None:
    logger.info(f'Logged in as {client.user}')
    await client.tree.sync()
    logger.info("Resynced global commands.")
    for guild in client.guilds:
        logger.info(f'Connected to guild: {guild.name} (id: {guild.id})')
        for channel in guild.text_channels:
            logger.info(f'  Text channel: {channel.name} (id: {channel.id})')

@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return
    logger.info(f'Received message: "{message.content}" from {message.author} in #{message.channel}')
    if message.content.lower() == 'hello':
        await message.channel.send(HELLO_RESPONSE)
        logger.info(f'Responded with "world!" to {message.author}')
        return

    # Respond to any other message that mentions the bot
    if client.user in message.mentions:
        await message.channel.send(USAGE_INSTRUCTIONS_MSG)
        logger.info(f'Responded with usage instructions to {message.author}')

@client.tree.command(
    name="checkk",
    description="Checkk a UUID in the threat feed",
    guild=discord.Object(id=1378827399948406906)
)
@app_commands.describe(uuid="The UUID to check")
async def check(interaction: discord.Interaction, uuid: str) -> None:
    result = await check_submission(uuid)
    await interaction.response.send_message(result)

def main() -> None:
    client.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    main()
