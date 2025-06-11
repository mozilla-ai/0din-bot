"""
Command-line interface for launching either the UUID checker bot or the message analyzer bot.
"""
import os
import sys
from typing import Optional
import click
from loguru import logger

from .bot import main as run_uuid_bot

@click.group()
def cli():
    """ODIN Discord Bot - Choose which bot to run."""
    pass

@cli.command()
def bot():
    """Run the UUID checker bot that verifies UUIDs against the ODIN Threatfeed API."""
    logger.info("Starting UUID checker bot...")
    run_uuid_bot()

@cli.command()
@click.option('--guild-id', required=True, help='Discord GUILD_ID (server) to connect to')
@click.option('--channel-id', required=True, help='Discord channel ID to analyze')
def agent(guild_id: str, channel_id: str):
    """Run the message analyzer bot that summarizes Discord messages."""
    logger.info(f"Starting message analyzer bot for guild {guild_id}, channel {channel_id}...")
    # Lazy load agent functionality only when needed
    from .agent import run_agent
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