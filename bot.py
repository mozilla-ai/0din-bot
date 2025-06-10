import os
import discord

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
    if message.content.lower() == 'hello':
        await message.channel.send('world!')

client.run(os.environ['DISCORD_TOKEN'])
