import asyncio
from io import BytesIO
import autogen
from datetime import datetime
import json
import os
import shutil

import autogen.tools
from PIL import Image
from byteskript_agent.agents import (
    create_agents_with_date,
    llm_config,
)
from byteskript_agent.img_gen.gen_img import ImageGenerator
from byteskript_agent.img_gen.json_processor import NewsDataProcessor
from byteskript_agent.telegram_sender import TelegramSender

from dotenv import load_dotenv

load_dotenv()


def save_data_with_metadata(data, filename="data.json"):
    """
    Save data to JSON file with metadata and backup.

    Args:
        data: The data to save (list of dictionaries)
        filename: The filename to save to
    """
    try:
        # Create metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "total_entries": len(data),
            "source": "ByteSkript Autogen System",
            "version": "1.0",
        }

        # Create the final data structure
        final_data = {"metadata": metadata, "posts": data}

        # Create backup of existing file if it exists
        if os.path.exists(filename):
            backup_filename = f"{filename}.backup"
            shutil.copy2(filename, backup_filename)
            print(f"Backup created: {backup_filename}")

        # Save the new data
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)

        print(f"Data saved successfully to {filename}")
        print(f"Total posts: {len(data)}")

        # Also save a timestamped version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_filename = f"data_{timestamp}.json"
        with open(timestamped_filename, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"Timestamped backup saved: {timestamped_filename}")

        return True

    except Exception as e:
        print(f"Error saving data: {e}")
        return False


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
                # Save data with improved mechanism
                success = save_data_with_metadata(data)
                if success:
                    print("✅ Data successfully saved and conversation terminated.")
                else:
                    print("❌ Failed to save data, but conversation will terminate.")
                return True

    except (json.JSONDecodeError, IndexError):
        # Not valid JSON or empty list
        pass

    return False


telegram_sender = TelegramSender(
    os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
)


def run_with_loop(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(func(*args, **kwargs))
    else:
        loop.run_until_complete(func(*args, **kwargs))


def on_one_generated(img: Image.Image, data):
    """
    On one generation complete, save the images and data.
    """
    summary = data["summary"]

    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    run_with_loop(
        telegram_sender.app.bot.send_photo,
        chat_id=telegram_sender.chat_id,
        photo=img_bytes,
    )

    run_with_loop(
        telegram_sender.app.bot.send_message,
        chat_id=telegram_sender.chat_id,
        text=summary,
        parse_mode="Markdown",
    )

    run_with_loop(
        telegram_sender.app.bot.send_message,
        chat_id=telegram_sender.chat_id,
        text=data["url"],
    )


def run():
    """
    Run the autogen crew to generate tech news reports.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Create agents with current date
    (
        search_query_agent,
        content_scraper_agent,
        credibility_checker_agent,
        formatter_agent,
    ) = create_agents_with_date(current_date)

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

    # user_id = "nahid_user"

    # def add_to_memory(message, sender, recipient, silent=False):
    #     memory.add(message, user_id=user_id)
    #     print(f"Added to memory, sender: {sender}, recipient: {recipient}: {message}")
    #     return message

    # user_proxy.register_hook("process_message_before_send", add_to_memory)

    # Create a group chat
    groupchat = autogen.GroupChat(
        agents=[
            user_proxy,
            search_query_agent,
            content_scraper_agent,
            credibility_checker_agent,
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

    initial_prompt = f"""
    Generate a ByteSkript-style tech news report featuring specific, high-quality updates from the past 24 hours only.

    **TODAY'S DATE:** {current_date} — Only include news from today or yesterday.

    **PRIORITIZED CATEGORIES:**
    - AI/ML: Gemini 2.5, ChatGPT updates, Claude, coding agents, LLM features
    - Programming: New Python/JS/TS/Rust releases, GitHub projects, frameworks
    - DevOps & Infra: Docker, Kubernetes, CI/CD innovations, monitoring tools
    - Cloud: AWS, GCP, Azure services, regional cloud news
    - Web Tech: React, Next.js, WebAssembly, browser upgrades
    - Mobile: Flutter, Android/iOS SDK updates, mobile trends
    - Data: DB innovations (Postgres, SQLite, DuckDB), analytics, ML infra
    - Security: Vulnerabilities, breaches, new tools, GitHub advisories
    - Web3: Blockchain, DeFi protocols, token launches, SEC actions
    - Startups: New tech products, funding news, BD startup scene
    - Open Source: GitHub trending tools, new releases, developer trends
    - Social: Twitter/X, Threads, TikTok platform changes or drama

    **RULES:**
    - News must be < 24 hours old (since {current_date})
    - Headlines must include specific keywords (e.g., “Claude 3.5 launched by Anthropic” not just “AI Tool Released”)
    - Avoid tutorials, think pieces, “best of” lists, and overly broad topics
    - Ensure all articles are sourced from reputable outlets or GitHub
    - Include a mix of global + Bangladeshi news if available

    **OUTPUT FORMAT (JSON Array):**
    Each object must contain: title, caption, summary, source, url, thumbnail_url, publish_date.
    Ensure summary is concise and hook-style (e.g., ~2 lines max).
    """

    user_proxy.initiate_chat(
        manager,
        message=initial_prompt,
        verbose=False,  # Reduce verbose output
    )

    processor = NewsDataProcessor(ImageGenerator(), on_one_generated)

    with open("data_20250717_032727.json", "r") as f:
        data = json.load(f)
        data = json.loads(data)
    images = processor.process_data(data)
    print(f"Generated {len(images)} images")


if __name__ == "__main__":
    run()
