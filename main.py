import autogen
from datetime import datetime
import json

import autogen.tools
from byteskript_agent.agents import (
    search_query_agent,
    internet_search_result_analyzer,
    formatter_agent,
    llm_config,
)


def is_termination_msg(message):
    """Check if a message indicates termination."""
    content = message.get("content", "")
    if content is None:
        return False

    if content.rstrip().endswith("TERMINATE"):
        return True

    # Handle cases where the message content might be a code block with JSON
    if "```json" in content:
        # Extract content within the json code block
        start = content.find("```json") + len("```json")
        end = content.rfind("```")
        if end > start:
            content = content[start:end].strip()
    # sometimes the LLM just returns raw JSON
    elif content.strip().startswith("[") and content.strip().endswith("]"):
        content = content.strip()

    try:
        # Attempt to parse the content as JSON
        data = json.loads(content)
        # Check if it's a list (JSON array) of objects
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Check if the first item has the expected keys
            if all(
                k in data[0]
                for k in ["title", "caption", "source", "url", "thumbnail_url"]
            ):
                return True
    except (json.JSONDecodeError, IndexError):
        # Not valid JSON or empty list
        pass

    return False


# Create a UserProxyAgent
user_proxy = autogen.UserProxyAgent(
    name="User_Proxy",
    system_message="""User Proxy Agent. It will coordinate the agents and verify if the result is satisfactory. If the result is not satisfactory, it will ask the agents to try again. Otherwise, terminate the conversation.
    You will receive the final output from the agents and you will verify if the result is satisfactory. If the result is not satisfactory, you will ask the agents to try again. Otherwise, terminate the conversation.
    """,
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=is_termination_msg,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
)

# Create a group chat
groupchat = autogen.GroupChat(
    agents=[
        user_proxy,
        search_query_agent,
        internet_search_result_analyzer,
        formatter_agent,
    ],
    messages=[],
    max_round=15,
)

group_chat_llm_config = llm_config.copy()
group_chat_llm_config["functions"] = []

# Create a group chat manager
manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=group_chat_llm_config,
)


def run():
    """
    Run the autogen crew to generate tech news reports.
    """
    current_date = datetime.now().strftime("%d-%m-%Y")
    initial_prompt = f"""
    Generate a report on the latest technology news in Bangladesh and globally for today, {current_date}.
    The final output should be a JSON array of ByteSkript-ready post objects. The final output should have title, caption, summary, source, url, thumbnail_url and it will be a JSON array, max 20 entries.
    """

    user_proxy.initiate_chat(
        manager,
        message=initial_prompt,
    )


if __name__ == "__main__":
    run()
