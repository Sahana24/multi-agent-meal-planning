import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

class GroqConfig:
    BASE_URL = "https://api.groq.com/openai/v1"
    MODEL_NAME = "llama-3.3-70b-versatile"

    def __init__(self):
        self.api_key = self._validate_env()
        self.model_client = self._create_client()

    def _validate_env(self):
        """Validate required environment variables"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("""
            Missing GROQ_API_KEY in environment variables.
            Create a .env file with:
            GROQ_API_KEY=your_actual_key_here
            """)
        return api_key

    def _create_client(self):
        """Create Groq client using .env configuration"""
        return OpenAIChatCompletionClient(
            model=self.MODEL_NAME,
            base_url=self.BASE_URL,
            api_key=self.api_key,
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "family": "llama",
            },
        )

    @property
    def llm_config(self):
        return {
            "config_list": [{
                "model": self.MODEL_NAME,
                "api_key": self.api_key,
                "base_url": self.BASE_URL,
                "price": [0, 0]
            }],
            "temperature": 0.7,
            "timeout": 120,
            "max_retries": 3 
        }

groq_config = GroqConfig()
