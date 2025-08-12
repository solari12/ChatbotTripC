import requests
import logging
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, api_key: str = None, base_url: str = None):
        # Load from .env if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables. LLM responses will fail.")
        
        self.base_url = self.base_url.rstrip("/")
    
    def set_api_key(self, api_key: str):
        """Cập nhật API key"""
        self.api_key = api_key
    
    def get_api_key(self) -> str:
        """Lấy API key hiện tại"""
        return self.api_key
    
    def is_configured(self) -> bool:
        """Kiểm tra xem client đã được cấu hình chưa"""
        return bool(self.api_key and self.api_key != "your_openai_api_key_here")

    def generate_response(self, prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 512) -> Optional[str]:
        """
        Gửi prompt đến LLM API (OpenAI hoặc Qwen nếu đổi URL) và nhận về câu trả lời.
        """
        if not self.is_configured():
            logger.error("OpenAI API key not configured. Please set OPENAI_API_KEY in .env file")
            return None
            
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("OpenAI API key invalid or expired. Please check your OPENAI_API_KEY")
            elif e.response.status_code == 429:
                logger.error("OpenAI API rate limit exceeded. Please try again later")
            else:
                logger.error(f"OpenAI API HTTP error: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error("OpenAI API request timeout")
            return None
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return None
