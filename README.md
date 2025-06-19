# Discord Bot: ODIN Threatfeed & Channel Summarizer

A Discord bot that:
- Checks the scan status of a UUID in the ODIN Threatfeed API.
- Fetches and summarizes the full ODIN threat feed.
- Summarizes channel conversations by user and topic for a given date.
- Responds to health checks and logs all activity.

## Features

- **/check <UUID>**: Query the ODIN Threatfeed API and report if the item has been scanned.
- **/health**: Check if the bot is operational.
- **Threat Feed Access**: The agent can fetch and summarize the full ODIN threat feed when requested.
- **Message Summarization**: When mentioned with a request for a summary (optionally specifying a date or user), the bot summarizes the main topics discussed by each user in the channel for that date.
- **Logging**: All agent traces and errors are logged to `logs/`.
- **Local Summaries**: Summaries are saved to `logs/discord_daily_summary_<date>.txt`.

## Requirements

- **Hardware:** Any system capable of running Python 3.11+
- **Software:**
  - Python 3.11 or higher
  - [uv](https://github.com/astral-sh/uv) (for dependency management and running)
  - A Discord account and a Discord server where you have permission to add bots
  - A Discord Bot Token ([Create one here](https://discord.com/developers/applications))
  - An ODIN API Key (for `/check` command and threat feed access)

## Installation

### For Use
To install the bot for regular use (runtime dependencies only):
```sh
uv pip install -e .
```

### For Development and Testing
To install the bot with all development and test dependencies:
```sh
uv pip install -e '.[test]'
```
This will install all runtime and test dependencies (pytest, pytest-asyncio, pytest-mock, etc.).

## Setup

1. **Clone this repository and enter the directory:**
   ```sh
   git clone git@github.com:ividal/0din-bot.git
   cd 0din-bot
   ```

2. **Install the package** (see Installation section above).

3. **Create a Discord bot and get your token:**
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application, add a bot, and copy the bot token
   - Invite the bot to your server using the OAuth2 URL generator (scopes: `bot`, permissions: `Send Messages`, `Read Messages`)

4. **Set your environment variables:**
   - The `/check <UUID>` command and threat feed access require a valid ODIN API key.
   - You must also set your Discord server's Guild ID and the channel ID you want the bot to monitor.

   ```sh
   export DISCORD_TOKEN=your-bot-token-here
   export ODIN_API_KEY=your-odin-api-key-here
   export GUILD_ID=your-discord-guild-id-here
   export CHANNEL_ID=your-discord-channel-id-here
   ```

5. **Run the bot:**
   ```sh
   uv run odinbot agent --guild-id $GUILD_ID --channel-id $CHANNEL_ID
   ```
   - Make sure you have set the `DISCORD_TOKEN`, `ODIN_API_KEY`, `GUILD_ID`, and `CHANNEL_ID` environment variables as described above.
   - The bot will start and monitor the specified channel in your server.

## Usage

- **Check a UUID:**  
  In any channel the bot is in, use the slash command:
  ```
  /check <UUID>
  ```
  The bot will reply with the scan status from the ODIN Threatfeed.

- **Health Check:**  
  ```
  /health
  ```
  The bot will reply if it is operational.

- **Access Threat Feed:**  
  Mention the bot and ask about the threat feed, e.g.:
  ```
  @Bot show me the threat feed
  @Bot what's in the threat feed today
  ```
  The bot will fetch and summarize the current ODIN threat feed.

- **Summarize Channel Messages:**  
  Mention the bot and request a summary, e.g.:
  ```
  @Bot summarize today's messages
  @Bot summarize messages from 2024-03-20
  @Bot summarize messages from user Alice on 2024-03-20
  ```
  The bot will reply with a summary of topics by user for the specified date and save the summary to a log file.

## Testing

- Tests are located in `tests/`.
- To install test dependencies, use:
  ```sh
  uv pip install -e '.[test]'
  ```
- To run the tests:
  ```sh
  uv run pytest tests/
  ```

## Notes

- All logs and summaries are saved in the `logs/` directory.
- The bot will only respond to direct mentions or slash commands.
- For development and debugging, all agent traces are saved as JSON in `logs/`.