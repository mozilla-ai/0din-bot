"""
Command-line interface for launching the message analyzer bot.
"""
import sys
import click
from loguru import logger

@click.group()
def cli():
    """ODIN Discord Bot CLI."""
    pass

@cli.command()
@click.option('--guild-id', required=True, help='Discord GUILD_ID (server) to connect to')
@click.option('--channel-id', required=True, help='Discord channel ID to analyze')
def agent(guild_id: str, channel_id: str):
    """Run the message analyzer bot that summarizes Discord messages."""
    logger.info(f"Starting message analyzer bot for guild {guild_id}, channel {channel_id}...")
    # Lazy load agent functionality only when needed
    from odinbot.agent import run_agent
    run_agent(guild_id=guild_id, channel_id=channel_id)

def main():
    """Entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 