import os
import discord
import requests

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    for guild in client.guilds:
        print(f'Connected to guild: {guild.name} (id: {guild.id})')
        for channel in guild.text_channels:
            print(f'  Text channel: {channel.name} (id: {channel.id})')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Respond to "hello"
    if message.content.lower() == 'hello':
        await message.channel.send('world!')
        return

    # Respond to "@Bot /check myUUID"
    if client.user in message.mentions and "/check" in message.content:
        # Extract the UUID from the message
        parts = message.content.split()
        try:
            check_index = parts.index("/check")
            uuid = parts[check_index + 1]
        except (ValueError, IndexError):
            await message.channel.send("Please provide a UUID after /check, e.g. '@agent /check myUUID'")
            return

        api_url = f"https://0din.ai/api/v1/threatfeed/{uuid}"
        api_key = os.environ.get("ODIN_API_KEY")
        if not api_key:
            await message.channel.send("API key not configured.")
            return

        headers = {
            "accept": "application/json",
            "Authorization": api_key
        }

        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check for ScannerModule in metadata
                    scanned = None
                    for item in data.get("metadata", []):
                        if item.get("type") == "ScannerModule":
                            scanned = item.get("result")
                            break
                    if scanned == 1:
                        result = "It has been scanned"
                    elif scanned == 0 or scanned is None:
                        result = "It hasn't been checked, hang tight."
                    else:
                        import json
                        result = f"```json\n{json.dumps(data, indent=2)}\n```"
                except Exception:
                    result = response.text
            else:
                result = f"API returned status code {response.status_code}: {response.text}"
        except Exception as e:
            result = f"API request failed: {e}"

        await message.channel.send(result)

client.run(os.environ['DISCORD_TOKEN'])
