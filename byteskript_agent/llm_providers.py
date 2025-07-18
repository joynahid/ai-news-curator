from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""

    api_key: str
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None


@dataclass
class Prompt:
    user_message: str
    system_message: Optional[str] = field(default=None)


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
    def generate(self, prompt: Prompt) -> str:
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

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._initialize_client()

    def _initialize_client(self):
        from google import genai

        self._client = genai.Client(api_key=self.config.api_key)

    def generate(self, prompt: Prompt) -> str:
        response = self._client.models.generate_content(
            model=self.config.model,
            contents=prompt.user_message,
            config={
                "system_instruction": prompt.system_message,
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
