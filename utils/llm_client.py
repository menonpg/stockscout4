"""
StockScout v4 — LLM Client

Unified interface for multiple LLM providers.
"""

import os
from typing import Optional
import anthropic
import openai


class LLMClient:
    """
    Unified LLM client supporting multiple providers:
    - Anthropic (Claude)
    - OpenAI (GPT)
    - Ollama (local)
    """
    
    def __init__(self, config):
        self.config = config
        self.provider = config.LLM_PROVIDER
        
        # Initialize clients based on provider
        if self.provider == "anthropic":
            self.client = anthropic.AsyncAnthropic(
                api_key=config.ANTHROPIC_API_KEY
            )
        elif self.provider == "openai":
            self.client = openai.AsyncOpenAI(
                api_key=config.OPENAI_API_KEY
            )
        elif self.provider == "ollama":
            # Ollama uses OpenAI-compatible API
            self.client = openai.AsyncOpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.3,
        model: Optional[str] = None,
        max_tokens: int = 4096
    ) -> str:
        """
        Generate completion from LLM.
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature (0-1)
            model: Model name (uses config default if not specified)
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text
        """
        model = model or self.config.QUICK_THINK_MODEL
        
        if self.provider == "anthropic":
            return await self._complete_anthropic(prompt, temperature, model, max_tokens)
        else:
            return await self._complete_openai(prompt, temperature, model, max_tokens)
    
    async def _complete_anthropic(
        self,
        prompt: str,
        temperature: float,
        model: str,
        max_tokens: int
    ) -> str:
        """Anthropic/Claude completion."""
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    async def _complete_openai(
        self,
        prompt: str,
        temperature: float,
        model: str,
        max_tokens: int
    ) -> str:
        """OpenAI/Ollama completion."""
        response = await self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
