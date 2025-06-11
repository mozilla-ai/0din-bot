# agent.py

import os
from dotenv import load_dotenv
from any_agent import AgentConfig, AnyAgent
from any_agent.config import MCPStdio
from pydantic import BaseModel, Field
from fire import Fire
from any_agent.tools import visit_webpage
from tools.summarize_text_with_llm import summarize_text_with_llm

load_dotenv()

# ========= Structured Output definition =========
class SummaryRow(BaseModel):
    user_handle: str = Field(..., description="The Discord handle of the user.")
    main_topic_of_concern: str = Field(..., description="The main topic this user posted about.")
    num_messages: int = Field(..., description="The number of messages from this user with essentially the same main topic on June 11th 2025.")

class StructuredOutput(BaseModel):
    summary_csv: str = Field(
        ..., description="CSV, where each row is: user_handle,main_topic_of_concern_the_user_posted_about,number_of_messages_with_the_same_topic"
    )
    file_path: str = Field(..., description="The relative path to the saved CSV summary file.")
    message_id: str = Field(..., description="The Discord message ID of the summary post.")

# ========= System Instructions =========
INSTRUCTIONS = '''
You are an assistant tasked with analyzing all messages posted on June 11th, 2025 on a specific Discord channel. Follow this exact workflow:
1. Retrieve all messages from the Discord channel with CHANNEL_ID {channel_id} (of server GUILD_ID provided by the user) that were posted on June 11th, 2025 (00:00 to 23:59 UTC inclusive). Fetch the message content, posting user handle, and timestamp for each message.
2. Identify what topic each user was primarily concerned with for their posts on that day by grouping their messages by topic (use main subject of concern or thread per user; if a user posted about multiple topics, each main topic counts as a row).
3. For each (user_handle, topic) pair, count the number of messages where the topic is the same.
4. Create a summary CSV in this schema: user_handle,main_topic_of_concern_the_user_posted_about,number_of_messages_with_the_same_topic (one row per main topic of each user).
5. Post the complete summary CSV as a single message to the same Discord channel (ID {channel_id}), prepending the message with 'Daily Topic Summary, June 11th 2025:'.
6. Save the summary CSV file locally as 'discord_june11_2025_topic_summary.csv' in the working directory, and confirm the relative path in your final output.
7. Return a JSON object containing: the summary_csv (as a string), the local file path, and the Discord message ID of your posted summary message. Make sure all work is reproducible.
'''

# ========= Tools ===========
TOOLS = [
    MCPStdio(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "DISCORD_TOKEN",
            "mcp/mcp-discord",
        ],
        env={"DISCORD_TOKEN": os.getenv("DISCORD_TOKEN")},
        tools=[
            # Main tools per https://raw.githubusercontent.com/pathintegral-institute/mcpm.sh/refs/heads/main/mcp-registry/servers/mcp-discord.json
            "discord_read_messages",
            "discord_send"
        ],
    ),
    # LLM text summarization, used for topic extraction
    summarize_text_with_llm,
]

agent = AnyAgent.create(
    "openai",
    AgentConfig(
        model_id="gpt-4.1",
        instructions=INSTRUCTIONS,
        tools=TOOLS,
        agent_args={"output_type": StructuredOutput},
    ),
)

def run_agent(guild_id: str, channel_id: str):
    """
    Fetches and summarizes all Discord messages in a specified channel for June 11, 2025.
    Output is a CSV summary posted back to the channel and also saved as a local file.
    Args:
        guild_id (str): The Discord GUILD_ID (server) to connect to.
        channel_id (str): The Discord channel ID to process (e.g., '1378827407733035162').
    """
    input_prompt = (
        f"Please check and summarize all messages posted on June 11th 2025 in Discord channel ID {channel_id}. "
        f"The Discord GUILD_ID to use is {guild_id}. Output a CSV where each line is: user_handle, main_topic_of_concern_the_user_posted_about, "
        "number_of_messages_with_the_same_topic. Then post that summary to the same channel and save the summary CSV as a file in the local working directory."
    )
    agent_trace = agent.run(prompt=input_prompt)
    with open("generated_workflows/latest/agent_eval_trace.json", "w", encoding="utf-8") as f:
        f.write(agent_trace.model_dump_json(indent=2))
    return agent_trace.final_output

if __name__ == "__main__":
    Fire(run_agent)