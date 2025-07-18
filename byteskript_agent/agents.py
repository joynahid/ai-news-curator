import json
import os
from typing import Optional
import autogen
from autogen import register_function
from datetime import datetime

from byteskript_agent.tools.playwright_tool import visit_urls_and_extract_content
from byteskript_agent.tools.serper_tools import search_serper, search_serper_multiple
from byteskript_agent.prompts import (
    SEARCH_QUERY_GENERATOR_PROMPT,
    CONTENT_EXTRACTOR_PROMPT,
    QUALITY_FILTER_PROMPT,
    FORMATTER_PROMPT,
)

# Define the LLM configuration
config_list = [
    {
        "api_type": "openai",
        "model": "gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY"),
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.0,
}



def save_data_with_metadata(data: str, filename: str = "data.json") -> Optional[str]:
    """
    Save data to JSON file with metadata and backup.

    Args:
        data: The data to save (list of dictionaries)
        filename: The filename to save to
    """
    try:
        # Create a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_filename = f"data_{timestamp}.json"

        # Save the data to the file
        with open(timestamped_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Data saved successfully to {timestamped_filename}")

        return timestamped_filename

    except Exception as e:
        print(f"Error saving data: {e}")
        return None


def create_agents_with_date(current_date: str):
    """Create agents with the current date injected into their system messages."""

    # Create new agent instances with current date in system messages
    search_query_agent_with_date = autogen.AssistantAgent(
        name="Search_Query_Generator",
        system_message=SEARCH_QUERY_GENERATOR_PROMPT.format(current_date=current_date),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    content_extractor_agent_with_date = autogen.AssistantAgent(
        name="Content_Extractor",
        system_message=CONTENT_EXTRACTOR_PROMPT.format(current_date=current_date),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    quality_filter_agent_with_date = autogen.AssistantAgent(
        name="Quality_Filter",
        system_message=QUALITY_FILTER_PROMPT.format(current_date=current_date),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    formatter_agent_with_date = autogen.AssistantAgent(
        name="Formatter",
        system_message=FORMATTER_PROMPT.format(current_date=current_date),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Register functions for the new agents
    register_function(
        search_serper_multiple,
        caller=search_query_agent_with_date,
        executor=search_query_agent_with_date,
        description="Search the internet using Serper API",
    )

    register_function(
        visit_urls_and_extract_content,
        caller=content_extractor_agent_with_date,
        executor=content_extractor_agent_with_date,
        description="Visit URLs and extract content",
    )

    register_function(
        search_serper_multiple,
        caller=content_extractor_agent_with_date,
        executor=content_extractor_agent_with_date,
        description="Search the internet using Serper API",
    )

    register_function(
        save_data_with_metadata,
        caller=formatter_agent_with_date,
        executor=formatter_agent_with_date,
        description="Save data json to a file",
    )

    return (
        search_query_agent_with_date,
        content_extractor_agent_with_date,
        quality_filter_agent_with_date,
        formatter_agent_with_date,
    )
