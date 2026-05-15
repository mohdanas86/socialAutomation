import json
import asyncio
import google.generativeai as genai
from huggingface_hub import InferenceClient
from typing import List, Dict
from app.utils.logger import get_logger
from app.utils.config import settings
from app.models.schemas import GeneratePostRequest

logger = get_logger(__name__)

class LLMService:
    HF_MODELS = (
        "Qwen/Qwen2.5-7B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "meta-llama/Llama-3.1-8B-Instruct",
    )

    @staticmethod
    def _build_prompt(request: GeneratePostRequest) -> str:
        return f"""
You are an expert LinkedIn copywriter. I need you to write {request.postCount} distinct, high-quality LinkedIn posts.

Topic: {request.topic}
Niche: {request.niche}
Target Audience: {request.targetAudience}
Tones: {', '.join(request.tones)}
Content Goal: {request.contentGoal}
Post Style: {request.postStyle}
Keywords: {', '.join(request.keywords)}
Custom Instructions: {request.customInstructions}

AI Options:
- Include Hook: {request.aiOptions.includeHook}
- Include Call To Action (CTA): {request.aiOptions.includeCTA}
- Include Hashtags: {request.aiOptions.includeHashtags}
- Include Emojis: {request.aiOptions.includeEmojis}
- Human-like, authentic writing: {request.aiOptions.humanLike}
- Concise Writing: {request.aiOptions.conciseWriting}

Constraints:
- Minimum Characters per post: {request.constraints.minChars}
- Maximum Characters per post: {request.constraints.maxChars}

Return the response ONLY as a valid JSON array of objects. Each object should have exactly one key called "content" containing the exact text of the post.
Do not include markdown code blocks like ```json. Just return the raw JSON array.

Example:
[
  {{"content": "First post content here..."}},
  {{"content": "Second post content here..."}}
]
"""

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Normalize LLM output into raw JSON text."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    @staticmethod
    async def _generate_with_huggingface(prompt: str) -> str:
        """Generate with HF InferenceClient using chat completions + model retries."""
        if not settings.hf_api_key:
            raise ValueError("HF_API_KEY is not configured")

        client = InferenceClient(api_key=settings.hf_api_key)
        models = [settings.hf_model_1, settings.hf_model_2, settings.hf_model_3]
        model_candidates = [m for m in models if m] or list(LLMService.HF_MODELS)

        errors: List[str] = []
        for model_name in model_candidates:
            try:
                logger.info(f"Generating posts with Hugging Face model: {model_name}")
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty content returned from Hugging Face")
                return content.strip()
            except Exception as e:
                error_msg = f"{model_name}: {e}"
                errors.append(error_msg)
                logger.warning(f"Hugging Face generation failed for {model_name}: {e}")

        raise ValueError("All Hugging Face models failed. " + " | ".join(errors))

    @staticmethod
    def _generate_with_gemini(prompt: str) -> str:
        """Generate content using Gemini."""
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key is not configured")
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)
        return response.text.strip()

    @staticmethod
    async def generate_posts(prompt: str) -> List[Dict]:
        """Reusable service to generate posts from prompt text."""
        response_text = ""
        try:
            if settings.llm_provider.lower() == "huggingface":
                response_text = await LLMService._generate_with_huggingface(prompt)
            else:
                response_text = LLMService._generate_with_gemini(prompt)

            response_text = LLMService._strip_markdown_fences(response_text)
            posts = json.loads(response_text)
            if not isinstance(posts, list):
                raise ValueError("LLM did not return a JSON array")
            return posts
        except json.JSONDecodeError:
            logger.exception("Failed to parse LLM output as JSON")
            raise ValueError("Failed to parse generated posts into valid JSON array")
        except Exception as e:
            logger.exception(f"Error generating posts from LLM: {e}")
            raise ValueError(f"Failed to generate posts: {e}")

    @staticmethod
    async def generate_posts_from_request(request: GeneratePostRequest) -> List[Dict]:
        prompt = LLMService._build_prompt(request)
        return await LLMService.generate_posts(prompt)
