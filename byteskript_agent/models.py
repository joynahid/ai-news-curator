from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import List, Optional, Dict, Any
import os


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""

    api_key: str
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @abstractmethod
    def _initialize_client(self):
        """Initialize the LLM client"""
        pass

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        pass

    @property
    def client(self):
        """Lazy initialization of client"""
        if self._client is None:
            self._initialize_client()
        return self._client


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def _initialize_client(self):
        from openai import OpenAI

        self._client = OpenAI(api_key=self.config.api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            **(self.config.additional_params or {}),
        )
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def _initialize_client(self):
        import anthropic

        self._client = anthropic.Anthropic(api_key=self.config.api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens or 4000,
            temperature=self.config.temperature,
            messages=[{"role": "user", "content": prompt}],
            **(self.config.additional_params or {}),
        )
        return response.content[0].text


class GoogleProvider(LLMProvider):
    """Google Gemini provider"""

    def _initialize_client(self):
        import google.generativeai as genai

        genai.configure(api_key=self.config.api_key)
        self._client = genai.GenerativeModel(self.config.model)

    def generate(self, prompt: str) -> str:
        response = self.client.generate_content(
            prompt,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
                **(self.config.additional_params or {}),
            },
        )
        return response.text


class CohereProvider(LLMProvider):
    """Cohere provider"""

    def _initialize_client(self):
        import cohere

        self._client = cohere.Client(api_key=self.config.api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.generate(
            model=self.config.model,
            prompt=prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            **(self.config.additional_params or {}),
        )
        return response.generations[0].text


# Factory function for easy provider creation
def create_llm_provider(provider_type: str, **kwargs) -> LLMProvider:
    """Factory function to create LLM providers"""
    config = LLMConfig(**kwargs)

    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "cohere": CohereProvider,
    }

    if provider_type not in providers:
        raise ValueError(f"Unknown provider type: {provider_type}")

    return providers[provider_type](config)


@dataclass
class Article:
    """Represents a single news article"""

    title: str
    content: str
    url: str
    source: str
    publish_date: Optional[str] = None
    author: Optional[str] = None
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "publish_date": self.publish_date,
            "author": self.author,
            "summary": self.summary,
        }


@dataclass
class FormattedPost:
    """Represents a formatted social media post"""

    title: str
    summary: str
    caption: str
    source: str
    url: str
    thumbnail_url: str = "placeholder"
    publish_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "caption": self.caption,
            "source": self.source,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "publish_date": self.publish_date,
        }


@dataclass
class PipelineResult:
    """Result of the tech news pipeline"""

    articles: List[Article] = field(default_factory=list)
    formatted_posts: List[FormattedPost] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def add_article(self, article: Article):
        self.articles.append(article)

    def add_formatted_post(self, post: FormattedPost):
        self.formatted_posts.append(post)

    def add_error(self, error: str):
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_articles": len(self.articles),
                "total_posts": len(self.formatted_posts),
                "errors": self.errors,
                **self.metadata,
            },
            "articles": [article.to_dict() for article in self.articles],
            "posts": [post.to_dict() for post in self.formatted_posts],
        }

    def save_to_file(self, filename: str):
        """Save result to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
