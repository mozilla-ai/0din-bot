# Discord Bot: ODIN Threatfeed Checker

A minimalist Discord bot that:
- Responds to `@Bot /check <UUID>` by querying the ODIN Threatfeed API and reporting scan status.

## Features
- When mentioned with `/check <UUID>`, calls the ODIN Threatfeed API and reports if the item has been scanned or not.

Note: you can check whether the bot is active by writing "hello" in any channel the bot is in. It will respond "world!".

## Requirements
- **Hardware:** Any system capable of running Python 3.11+
- **Software:**
  - Python 3.11 or higher ([Download Python](https://www.python.org/downloads/))
  - [uv](https://github.com/astral-sh/uv) (for dependency management and running)
  - A Discord account and a Discord server where you have permission to add bots
  - A Discord Bot Token ([Create one here](https://discord.com/developers/applications))
  - An ODIN API Key (for /check command)

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

4. **Set your environment variables:**
   - The `/check <UUID>` command requires a valid ODIN API key.

   ```sh
   export DISCORD_TOKEN=your-bot-token-here
   export ODIN_API_KEY=your-odin-api-key-here # Note this is spelled ODIN, not 0DIN, as the original project
   ```

5. **Run the bot:**
   ```sh
   uv run python bot.py
   ```
