import autogen
from autogen import register_function
from datetime import datetime

from byteskript_agent.tools.playwright_tool import visit_urls_and_extract_content
from byteskript_agent.tools.serper_tools import search_serper, search_serper_multiple

# Define the LLM configuration
config_list = autogen.config_list_from_dotenv(
    dotenv_file_path=".env",
    model_api_key_map={"gpt-4o-mini": "OPENAI_API_KEY"},
    filter_dict={"model": ["gpt-4o-mini"]},
)

llm_config = {
    "config_list": config_list,
    "temperature": 0.1,
}

# Agent definitions

search_query_agent = autogen.AssistantAgent(
    name="SEO_Research_Specialist",
    system_message="""You are an SEO Research Specialist for Tech & Startup News.
Your goal is to generate optimized and varied search queries to find current tech and startup news from international and Bangladeshi sources.
You're an expert at crafting Google and SERP search queries that uncover newsworthy and trending content. You understand how to structure prompts with keywords, time filters, and source targeting to capture diverse perspectives across media landscapes.
After generating the queries, you should call the `search_internet_multiple` tool to execute the search.
""",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

register_function(
    search_serper_multiple,
    caller=search_query_agent,
    executor=search_query_agent,
    description="Visit URLs and extract content",
)


internet_search_result_analyzer = autogen.AssistantAgent(
    name="Internet_Search_Result_Analyzer",
    system_message="""You are an Internet Search Result Analyzer for Byteskript.
Your goal is to analyze the search results and extract the most relevant and interesting information. Make sure the news is upto date and relevant to the current date.
You're an expert at analyzing search results and extracting the most relevant and interesting information. You only provide the urls of the articles that are relevant to the current date.
From the search results, you should identify the most promising URLs and call the `visit_urls_and_extract_content` tool to scrape them.
""",
    llm_config=llm_config,
    human_input_mode="NEVER",
)

register_function(
    visit_urls_and_extract_content,
    caller=internet_search_result_analyzer,
    executor=internet_search_result_analyzer,
    description="Visit URLs and extract content",
)

formatter_agent = autogen.AssistantAgent(
    name="ByteSkript_Post_Generator",
    system_message="""You are a ByteSkript Post Generator.
Your goal is to format summarized news into JSON-formatted ByteSkript social posts with title, summary (max 150 words, give maximum value to he readers), caption, source, url, publish_date and thumbnail_url.
You will receive summaries and you need to format them into JSON objects.
You write short, witty, and engaging and slightly satirical or meme like ByteSkript-style tech news posts. Tone is like Obaydul Kader (former Bangladesh MP). Your output is a JSON object with 5 keys: title, summary (max 150 words, give maximum value to he readers), caption, source, url, thumbnail_url, publish_data. You always match the brand tone—bold, slightly sarcastic, and Gen Z-friendly.
This is the final step. After generating the JSON, Type TERMINATE to end the conversation.
""",
    llm_config=llm_config,
    human_input_mode="NEVER",
)
