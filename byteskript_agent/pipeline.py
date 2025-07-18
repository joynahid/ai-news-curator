from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
import json
import os
import shutil
from io import BytesIO

from byteskript_agent.llm_providers import (
    GoogleProvider,
    LLMConfig,
    LLMProvider,
    Prompt,
)
from byteskript_agent.models import Article, FormattedPost, PipelineResult
from byteskript_agent.tools.playwright_tool import visit_urls_and_extract_content
from byteskript_agent.tools.serper_tools import SerperQuery, search_scraper_multiple, search_serper_multiple
from byteskript_agent.telegram_sender import TelegramSender
from byteskript_agent.img_gen.gen_img import ImageGenerator
from byteskript_agent.img_gen.json_processor import NewsDataProcessor
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from dotenv import load_dotenv

load_dotenv()


def parse_json_response(response: str) -> List[str]:
    """Parse a JSON response into a list of strings"""
    response = response.replace("```json", "").replace("```", "").strip()
    return json.loads(response)


@dataclass
class PipelineConfig:
    """Configuration for the tech news pipeline"""

    current_date: str
    max_articles: int = 15
    max_queries: int = 12
    save_backup: bool = True
    output_filename: str = "data.json"


class PipelineStep(ABC):
    """Abstract base class for pipeline steps"""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    @abstractmethod
    def execute(self, data: Any, config: PipelineConfig) -> Any:
        """Execute the pipeline step"""
        pass


class QueryGenerationStep(PipelineStep):
    """Step 1: Generate search queries"""

    def execute(self, focus: str, config: PipelineConfig) -> List[str]:
        system_prompt = """
        You are an expert SEO assistant. 
        Your job is to craft concise, high-coverage search queries for breaking tech news.
        """

        user_prompt = f"""
        Task: Produce **{config.max_queries}** diverse Google search objects in JSON.

        Context
        -------
        • Window: last 24 hours before {config.current_date}  
        • Focus topic: “{focus}”

        Rules
        -----
        • Each object must contain "q" (query string) and "gl" (country code).
        • Vary keywords, synonyms, and locales (e.g., bd, us, ca, in).  
        • Target tech-news sources (blogs, portals, company posts).  
        • No duplicate or near-duplicate queries.
        • Source type can be "news" or "search"
        • Must use google dorks to find the latest news
        • The articles must be from the last 24 hours
        • Make sure the query is not too broad or too narrow and have strict time range

        Output
        ------
        Return a pure JSON array only. Example schema:

        [
        {{"q": "latest AI chip launch Bangladesh", "gl": "bd", "source_type": "news"}},
        {{"q": "24h cloud computing breakthroughs", "gl": "us", "source_type": "search"}}
        ]

        No extra keys, comments, or prose.
        """

        response = self.llm.generate(
            Prompt(user_message=user_prompt, system_message=system_prompt)
        )
        return parse_json_response(response)


class FindBestURLsStep(PipelineStep):
    """Step 2: Find the best URLs"""

    def execute(
        self, results: List[Dict[str, Any]], config: PipelineConfig
    ) -> List[str]:
        system_prompt = """
        You are a meticulous researcher who filters search results for recency and credibility from raw JSON.
        Return ONLY a JSON array of URLs.
        """

        user_prompt = f"""

        You are given a list of search results in json format inside <search_results> tag.
        Select 10-15 URLs that best match the criteria listed below.

        Input results:
        <search_results>
        {json.dumps(results, indent=2)}
        </search_results>

        Selection criteria:
        ✔ Published in the last 24 hours, current date: {config.current_date}
        ✔ Reputable tech sources (major outlets, official blogs, well-known analysts)  
        ✔ Specific, descriptive titles (avoid generic listicles)
        ✔ Avoid generic titles like "top", "best", "trending", "popular", "list", "ranking", "comparison", "guide", "tutorial"

        Reject if:
        ✖ Older than 24 hours  
        ✖ Low-quality or non-tech listings  
        ✖ Duplicate coverage of the same story, choose the best one

        Output:
        Return a JSON array *only*, e.g.:

        [
        "https://example.com/2025/07/17/new-quantum-gpu-announced",
        "https://another-site.com/apple-open-sourcing-vision-os-kernel"
        ]

        No commentary, markdown, or keys besides the raw strings. Only Array of URLs.
        """
        print(user_prompt)
        response = self.llm.generate(
            Prompt(user_message=user_prompt, system_message=system_prompt)
        )
        return parse_json_response(response)


class ContentFilteringStep(PipelineStep):
    """Step 3: Filter content for quality"""

    def execute(
        self, articles: List[Dict[str, Any]], config: PipelineConfig
    ) -> List[str]:
        system_prompt = """
        You are a meticulous tech-news curator.  
        Return ONLY the JSON array requested—no prose.
        """

        user_prompt = f"""
        Task: From the list below inside <articles> tag, keep **high-quality tech articles** published ≤ 24 h before {config.current_date}.  
        Aim for VARIETY: product/feature launches, funding or M&A, security incidents, research breakthroughs, policy or legal moves, earnings/market data, notable interviews—anything substantive and news-worthy.

        Acceptance Criteria:
        • Published within 24 h of {config.current_date}  
        • Covers a concrete, *newsworthy* development (see categories above)  
        • Source is reputable (major outlet, official blog, well-known analyst, founder post)  
        • Title is specific and descriptive (not click-bait)

        Rejection Criteria:
        • Listicles, roundups, generic “how-to” / tutorial / guide content  
        • Titles containing: top, best, trending, popular, list, ranking, comparison, guide, tutorial  
        • Overly vague titles like “AI Breakthrough” or “New AI Tool”  
        • Older than 24 h  
        • Duplicate or near-duplicate stories

        Input:
        <articles>
        {json.dumps(articles, indent=2)}
        </articles>

        Output:
        A pure JSON array of the **original titles** that pass, e.g.:

        [
        "OpenAI Introduces GPT-5 With 2 Trillion Parameters",
        "Singapore's InFlight Secures $25 M to Build Quantum-Safe VPNs",
        "Microsoft Discloses July 2025 Patch Tuesday Fixing 132 Vulnerabilities"
        ]

        No markdown, labels, or extra keys.
        """

        response = self.llm.generate(
            Prompt(
                user_message=user_prompt.strip(), system_message=system_prompt.strip()
            )
        )

        titles = parse_json_response(response)
        return titles


class PostFormattingStep(PipelineStep):
    """Step 4: Format articles into social media posts"""

    def execute(
        self, articles: List[Dict[str, Any]], config: PipelineConfig
    ) -> List[Dict[str, Any]]:
        system_prompt = """
        You are a tech-savvy social-media copywriter for Bangladeshi readers.
        Turn news articles into viral, meme-friendly posts.
        Return ONLY the JSON array requested—no prose.
        """

        user_prompt = f"""
        Task:
        For each article below inside <articles> tag, output one JSON object with these keys:

        {{
        "title": "",         # Meme style, Title Case, No Emojis, Or Special Characters, max 25 words, Hooky and catchy
        "summary": "",       # max 150 words, crisp value delivery
        "bangla_title": "",  # max 25 words, bangla title
        "bangla_summary": "", # max 150 words, crisp value delivery in bangla
        "caption": "",       # Meme vibe + emojis
        "source": "",        # e.g. TechCrunch, The Verge, etc.
        "url": "",           # original link
        "thumbnail_url": "", # leave "placeholder"
        "publish_date": ""   # e.g. 17 July 2025
        }}

        Guidelines:
        - **Bangladesh angle—only if relevant**:  
          - If the story clearly affects Bangladesh (local launch, pricing, jobs, regulations, partnerships), weave that angle into the title or summary.  
          - Otherwise, skip the BD mention and keep it global.  
        - Title must name a specific company, product, or tech and hook the reader.
        - Use Gen-Z language & emotional punch, but stay factual.  
        - Summary: no fluff—explain “why it matters.”  
        - Caption: fun, punchy, emoji-rich; local slang or 🇧🇩 emoji welcome *only* when the BD angle exists.  
        - Keep markdown, hashtags, @handles *out* of title & summary.
        - Source should not be a URL, it should be a name of the source like TechCrunch, The Verge, etc.

        Input:  
        <articles>
        {json.dumps(articles, indent=2)}
        </articles>

        Output:
        Return a pure **JSON array** of the objects (no wrapper text).

        Example:
        [
        {{
            "title": "Apple Drops Vision Pro 2—Your Wallet Just Cried",
            "summary": "Apple's second-gen headset doubles battery life and slashes weight by 30 %. Devs get a new spatial SDK today. Here's why that's huge ▶️",
            "caption": "Vision Pro 2—who's buying? 🙋‍♀️",
            "source": "The Verge", # e.g. TechCrunch, The Verge, etc.
            "url": "https://…",
            "thumbnail_url": "placeholder",
            "publish_date": "17 July 2025"
        }}
        ]

        No extra keys, comments, or prose.
        """

        response = self.llm.generate(
            Prompt(
                user_message=user_prompt.strip(), system_message=system_prompt.strip()
            )
        )

        posts = parse_json_response(response)
        return posts


class TechNewsPipeline:
    """Main pipeline orchestrator"""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.query_generation_step = QueryGenerationStep(llm_provider)
        self.find_best_urls_step = FindBestURLsStep(llm_provider)
        self.content_filtering_step = ContentFilteringStep(llm_provider)
        self.post_formatting_step = PostFormattingStep(llm_provider)


async def log(message: str):
    await telegram_app.bot.send_message(
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        text=message,
        parse_mode="Markdown",
    )

async def run_pipeline(
    pipeline: TechNewsPipeline, telegram_app: Application, focus: str
):
    queries = pipeline.query_generation_step.execute(
        focus, PipelineConfig(current_date=datetime.now().strftime("%m-%d-%Y"))
    )

    await log(f"Searching {len(queries)} queries")

    results = await search_serper_multiple(
        [
            SerperQuery(q=query["q"], gl=query["gl"], source_type=query["source_type"])
            for query in queries
        ]
    )

    best_urls = pipeline.find_best_urls_step.execute(
        results, PipelineConfig(current_date=datetime.now().strftime("%m-%d-%Y"))
    )

    await log(f"Visiting {len(best_urls)} filtered urls")

    contents = await visit_urls_and_extract_content(best_urls)

    prompt_contexts = []

    for content in contents:
        if "error" in content:
            continue

        prompt_contexts.append(
            {
                "title": content["title"],
                "summary": content["summary"],
                "url": content["article_url"],
                "source": content["source_url"],
                "publish_date": content["publish_date"],
                "authors": content["authors"],
                "keywords": content["keywords"],
            }
        )

    await log(f"Filtering {len(prompt_contexts)} articles")

    filtered_data = pipeline.content_filtering_step.execute(
        prompt_contexts,
        PipelineConfig(current_date=datetime.now().strftime("%m-%d-%Y")),
    )

    summary_contexts = []

    await log(f"Filtered {len(filtered_data)} articles")

    for title in filtered_data:
        for content in contents:
            if "error" in content:
                continue

            if content["title"] == title:
                summary_contexts.append(
                    {
                        "title": content["title"],
                        "summary": content["summary"],
                        "url": content["article_url"],
                        "source": content["source_url"],
                        "publish_date": content["publish_date"],
                        "authors": content["authors"],
                        "keywords": content["keywords"],
                        "content": content["text"],
                    }
                )

    await log(f"Formatting {len(summary_contexts)} articles")

    formatted_data = pipeline.post_formatting_step.execute(
        summary_contexts,
        PipelineConfig(current_date=datetime.now().strftime("%m-%d-%Y")),
    )

    with open("formatted_data.json", "w") as f:
        json.dump(formatted_data, f, indent=2)

    return formatted_data


async def run_and_send(
    pipeline: TechNewsPipeline, telegram_app: Application, focus: str
):
    formatted_data = await run_pipeline(pipeline, telegram_app, focus)

    # Initialize image generator and processor
    image_generator = ImageGenerator()

    async def on_one_generated(img, data):
        """Callback function when an image is generated"""
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Send image and message to Telegram
        await telegram_app.bot.send_document(
            chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            document=img_bytes,
            filename=f"{data['title'].replace(' ', '_').lower()[:100]}.png",
            parse_mode="Markdown",
        )

        await telegram_app.bot.send_message(
            chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            text=data["summary"],
            parse_mode="Markdown",
        )

        if "bangla_summary" in data:
            await telegram_app.bot.send_message(
                chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                text=data["bangla_summary"],
                parse_mode="Markdown",
            )

        await telegram_app.bot.send_message(
            chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            text=data["url"],
            parse_mode="Markdown",
        )

    # Process formatted data to generate images and send to Telegram
    processor = NewsDataProcessor(image_generator, on_one_generated)
    await processor.process_data(formatted_data)

    await telegram_app.bot.send_message(
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        text="Pipeline completed",
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    llm_provider = GoogleProvider(
        config=LLMConfig(
            api_key=os.getenv("GEMINI_API_KEY"),
            model="gemini-2.5-flash",
            temperature=0.0,
        )
    )

    telegram_sender = TelegramSender(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    )

    telegram_app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    pipeline = TechNewsPipeline(llm_provider)

    async def start_pipeline(update, context: CallbackContext):
        await update.message.reply_text("Starting pipeline...")
        pipeline = TechNewsPipeline(llm_provider)
        msg = update.message.text
        msg = msg.replace("/start", "")
        msg = msg.strip()
        if msg == "":
            msg = (
                "Breaking tech news and analysis with a focus on AI, machine learning, software development, "
                "startups, fintech, cybersecurity, and digital transformation. Highlight developments in Bangladesh "
                "and South Asia, including local product launches, government policy, funding rounds, research breakthroughs, "
                "and major partnerships. Cover global tech trends that impact the region, such as cloud computing, "
                "semiconductors, edtech, and telecom. Target audience: Bangladeshi tech professionals, students, and entrepreneurs. "
                "Prioritize news from the last 24 hours, emphasizing regional relevance and innovation."
            )
        await run_and_send(pipeline, telegram_app, msg)

    async def hello_pipeline(update, context: CallbackContext):
        await update.message.reply_text("Hello. /start to start the pipeline")

    telegram_app.add_handler(
        CommandHandler(
            "start",
            start_pipeline,
        )
    )
    telegram_app.add_handler(
        CommandHandler(
            "hello",
            hello_pipeline,
        )
    )
    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT,
            hello_pipeline,
        )
    )
    telegram_app.run_polling()

