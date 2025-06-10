"""
A Discord bot that responds to 'hello' and handles '@Bot /check <UUID>' commands by querying the ODIN Threatfeed API.
"""
import os
import discord
import requests
from loguru import logger
from typing import Optional
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Register the command tree for a specific guild for instant update
        GUILD_ID = os.environ.get("GUILD_ID")
        if not GUILD_ID:
            raise RuntimeError("GUILD_ID environment variable not set.")
        guild = discord.Object(id=int(GUILD_ID))
        await self.tree.sync(guild=guild)

client = MyClient()

# === Discord User-Facing Messages ===
API_KEY_NOT_CONFIGURED_MSG = "API key not configured."
API_REQUEST_FAILED_MSG = "API request failed: {error}"
API_RETURNED_STATUS_MSG = "API returned status code {status_code}: {text}"
NO_UUID_MSG = "Please provide a UUID after /check, e.g. '@agent /check myUUID'"
SCANNED_MSG = "It has been scanned"
NOT_SCANNED_MSG = "It hasn't been checked, hang tight."
USAGE_INSTRUCTIONS_MSG = "If you want me to check your submission, @ me and write '/check UUID'"
HELLO_RESPONSE = "world!"
API_BASE_URL = "https://0din.ai/api/v1/threatfeed/"
IS_UUID_VALID_MSG = "Did you provide a valid UUID?"

def get_api_key() -> Optional[str]:
    return os.environ.get("ODIN_API_KEY")

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

@client.event
async def on_ready() -> None:
    logger.info(f'Logged in as {client.user}')
    for guild in client.guilds:
        logger.info(f'Connected to guild: {guild.name} (id: {guild.id})')
        for channel in guild.text_channels:
            logger.info(f'  Text channel: {channel.name} (id: {channel.id})')

@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return

    logger.info(f'Received message: "{message.content}" from {message.author} in #{message.channel}')

    # Respond to "hello"
    if message.content.lower() == 'hello':
        await message.channel.send(HELLO_RESPONSE)
        logger.info(f'Responded with "world!" to {message.author}')
        return

    # Respond to any other message that mentions the bot
    if client.user in message.mentions:
        await message.channel.send(USAGE_INSTRUCTIONS_MSG)
        logger.info(f'Responded with usage instructions to {message.author}')

@client.tree.command(
    name="check",
    description="Check a UUID in the threat feed",
    guild=discord.Object(id=1378827399948406906)
)
@app_commands.describe(uuid="The UUID to check")
async def check(interaction: discord.Interaction, uuid: str):
    api_url = f"{API_BASE_URL}{uuid}"
    api_key = get_api_key()
    if not api_key:
        logger.error("ODIN_API_KEY not set in environment.")
        await interaction.response.send_message(API_KEY_NOT_CONFIGURED_MSG, ephemeral=True)
        return

    headers = {
        "accept": "application/json",
        "Authorization": api_key
    }

    try:
        response = requests.get(api_url, headers=headers)
        logger.info(f'API request to {api_url} returned status {response.status_code}')
    except Exception as e:
        logger.error(f"API request failed: {e}")
        await interaction.response.send_message(API_REQUEST_FAILED_MSG.format(error=e), ephemeral=True)
        return

    if response.status_code != 200:
        logger.error(f"API returned status code {response.status_code}: {response.text}")
        await interaction.response.send_message(f"{API_RETURNED_STATUS_MSG.format(status_code=response.status_code, text=response.text)}\n{IS_UUID_VALID_MSG}", ephemeral=False)
        return

    try:
        data = response.json()
    except Exception as e:
        logger.error(f'Error parsing JSON response: {e}')
        await interaction.response.send_message(response.text, ephemeral=True)
        return

    result = parse_scan_result(data)
    await interaction.response.send_message(result)

def main() -> None:
    client.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    main()
