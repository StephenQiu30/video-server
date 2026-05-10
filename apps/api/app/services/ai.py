import json
import logging
from typing import Optional

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_api_base_url
        self.model = settings.llm_model_name

    async def summarize_transcript(self, transcript: str) -> Optional[str]:
        if not self.api_key:
            logger.warning("AI API key not configured, skipping summary")
            return None

        prompt = (
            "你是一个专业的视频内容分析专家。请根据以下转录文本，"
            "生成高质量的 Markdown 摘要。要求包含内容概述、"
            "3-5 个核心观点以及重要的结论。保持简洁且具有深度。请使用中文回答。\n\n"
            f"转录文本：\n{transcript[:10000]}" # Limit context for now
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error during AI summarization: {str(e)}")
            return None

    async def generate_mindmap(self, transcript: str) -> Optional[str]:
        if not self.api_key:
            return None

        prompt = (
            "请根据以下视频转录文本，生成一个结构化的思维导图，格式为 Mermaid.js。 "
            "使用 `mindmap` 语法。重点展示核心话题和子话题。请使用中文描述节点内容。\n\n"
            f"转录文本：\n{transcript[:10000]}"
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                # Clean up mermaid code block if present
                if "```mermaid" in content:
                    content = content.split("```mermaid")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                return content
        except Exception as e:
            logger.error(f"Error generating mindmap: {str(e)}")
            return None
