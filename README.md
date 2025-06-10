# Hello-World Discord Bot

A minimalist Discord bot that replies with `world!` whenever a user says `hello` in any channel the bot can read.

## Features
- Responds to the message `hello` (case-insensitive) with `world!` on any channel on your server it can read.

## Requirements
- **Hardware:** Any system capable of running Python 3.11+
- **Software:**
  - Python 3.8 or higher ([Download Python](https://www.python.org/downloads/))
  - [uv](https://github.com/astral-sh/uv) (for dependency management and running)
  - A Discord account and a Discord server where you have permission to add bots
  - A Discord Bot Token ([Create one here](https://discord.com/developers/applications))

## Setup

1. **Clone this repository and enter the directory:**
   ```sh
   git clone <your-repo-url>
   cd <your-repo-directory>
   ```

2. **Install dependencies using uv:**
   ```sh
   uv pip install -r requirements.txt
   ```

3. **Create a Discord bot and get your token:**
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application, add a bot, and copy the bot token
   - Invite the bot to your server using the OAuth2 URL generator (scopes: `bot`, permissions: `Send Messages`, `Read Messages`)

4. **Set your bot token as an environment variable:**
   ```sh
   export DISCORD_TOKEN=your-bot-token-here
   ```

5. **Run the bot:**
   ```sh
   uv run python bot.py
   ```
