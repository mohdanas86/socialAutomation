import json
import google.generativeai as genai
from typing import List, Dict
from app.utils.logger import get_logger
from app.utils.config import settings
from app.models.schemas import GeneratePostRequest

logger = get_logger(__name__)

class LLMService:
    @staticmethod
    async def generate_posts(request: GeneratePostRequest) -> List[Dict]:
        try:
            if not settings.gemini_api_key:
                raise ValueError("Gemini API key is not configured")
                
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = f"""
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
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown if the model included it despite instructions
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            posts = json.loads(response_text)
            
            if not isinstance(posts, list):
                raise ValueError("LLM did not return a JSON array")
                
            return posts
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response_text}")
            raise ValueError("Failed to parse generated posts into structured format.")
        except Exception as e:
            logger.error(f"Error generating posts from LLM: {str(e)}")
            raise ValueError(f"Failed to generate posts: {str(e)}")
