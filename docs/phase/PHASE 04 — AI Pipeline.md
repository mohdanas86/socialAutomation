# PHASE 04 — AI Pipeline (Analyzer, Angle Engine, Generator, Humanizer)

## Phase Goal
Build the complete multi-model AI pipeline that transforms raw project data into recruiter-ready LinkedIn posts. This is the core differentiator. The pipeline must be model-agnostic (HuggingFace / Gemini / GPT), prompt-versioned, and modular (each step independently testable).

---

## Features Implemented
- Abstract `BaseAIClient` + concrete implementations (HuggingFace, Gemini)
- `AIClientFactory` — swap models via env variable
- `ProjectAnalyzer` — understands technical depth, value, audience relevance
- `AngleEngine` — selects best content angle from 6 types
- `HookGenerator` — creates attention-grabbing opening line
- `PostGenerator` — generates full LinkedIn post body + CTA + hashtags
- `HumanizerLayer` — removes AI-pattern phrases, adds authenticity
- Full pipeline orchestrator: `ContentGenerationPipeline`
- Token guard: README truncation before sending to LLM
- Analysis result caching in `projects.analysis_cache`
- Prompt versioning (`PROMPT_VERSION = "v1.2"`)

---

## Technical Architecture

```
app/
├── ai/
│   ├── __init__.py
│   ├── client/
│   │   ├── __init__.py
│   │   ├── base.py              ← BaseAIClient ABC
│   │   ├── huggingface.py       ← HuggingFace Inference API
│   │   ├── gemini.py            ← Google Gemini API
│   │   └── factory.py           ← get_ai_client() factory
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── analyzer.py          ← ProjectAnalyzer
│   │   ├── angle_engine.py      ← AngleEngine
│   │   ├── hook_generator.py    ← HookGenerator
│   │   ├── post_generator.py    ← PostGenerator
│   │   ├── humanizer.py         ← HumanizerLayer
│   │   └── orchestrator.py      ← ContentGenerationPipeline
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── version.py           ← PROMPT_VERSION constant
│   │   ├── analyzer_prompts.py
│   │   ├── angle_prompts.py
│   │   ├── hook_prompts.py
│   │   ├── post_prompts.py
│   │   └── humanizer_prompts.py
│   └── constants.py             ← Banned phrases, angle definitions
```

---

## AI Client Abstraction

### Base Client (`app/ai/client/base.py`)
```python
from abc import ABC, abstractmethod
from typing import Optional

class BaseAIClient(ABC):
    """Abstract base for all AI provider clients."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text from a prompt. Returns raw string output."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the AI provider is reachable."""
        pass
```

### Gemini Client (`app/ai/client/gemini.py`)
```python
import httpx
from typing import Optional
from app.ai.client.base import BaseAIClient
from app.core.config import settings
from app.utils.logger import logger

class GeminiClient(BaseAIClient):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        url = f"{self.BASE_URL}/models/gemini-1.5-flash:generateContent"
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                params={"key": settings.GEMINI_API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def health_check(self) -> bool:
        try:
            await self.generate("Say hello in one word.", max_tokens=10)
            return True
        except Exception:
            return False
```

### HuggingFace Client (`app/ai/client/huggingface.py`)
```python
import httpx
from typing import Optional
from app.ai.client.base import BaseAIClient
from app.core.config import settings

class HuggingFaceClient(BaseAIClient):
    MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"
    BASE_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.BASE_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
            )
            response.raise_for_status()
            return response.json()[0]["generated_text"]

    async def health_check(self) -> bool:
        try:
            await self.generate("Hello", max_tokens=5)
            return True
        except Exception:
            return False
```

### Factory (`app/ai/client/factory.py`)
```python
from app.ai.client.base import BaseAIClient
from app.ai.client.gemini import GeminiClient
from app.ai.client.huggingface import HuggingFaceClient
from app.core.config import settings

_client_cache: BaseAIClient = None

def get_ai_client() -> BaseAIClient:
    global _client_cache
    if _client_cache is None:
        provider = settings.LLM_PROVIDER.lower()
        if provider == "gemini":
            _client_cache = GeminiClient()
        elif provider == "huggingface":
            _client_cache = HuggingFaceClient()
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    return _client_cache
```

---

## Prompt Version
```python
# app/ai/prompts/version.py
PROMPT_VERSION = "v1.2"
```

---

## AI Constants
```python
# app/ai/constants.py

CONTENT_ANGLES = [
    "achievement",          # "I built X and it achieved Y"
    "storytelling",         # Narrative arc: struggle → solution → result
    "learning_journey",     # What I learned building this
    "technical_breakdown",  # How it works technically
    "problem_solution",     # Problem → Why it's hard → How I solved it
    "internship_focused"    # Targeted at getting internship/job
]

BANNED_AI_PHRASES = [
    "delve",
    "excited to announce",
    "in today's fast-paced world",
    "unlocking potential",
    "game-changer",
    "revolutionize",
    "leverage",
    "synergy",
    "paradigm shift",
    "excited to share",
    "thrilled to announce",
    "it gives me great pleasure",
    "as an AI language model",
    "I don't have personal experiences",
    "I cannot",
]

TONE_OPTIONS = ["professional", "casual", "storytelling", "technical", "inspiring"]

TARGET_AUDIENCES = [
    "recruiters",
    "students",
    "developers",
    "startup_founders",
    "ml_engineers"
]
```

---

## Pipeline Components

### Project Analyzer (`app/ai/pipeline/analyzer.py`)
```python
from app.ai.client.factory import get_ai_client
from app.ai.prompts.analyzer_prompts import build_analyzer_prompt
from app.utils.logger import logger
import json

class ProjectAnalyzer:
    """
    Analyzes a project to extract value, impact, and technical depth.
    Results are cached to avoid redundant API calls.
    """

    async def analyze(self, project: dict) -> dict:
        # Return cached analysis if available and not stale
        if project.get("analysis_cache"):
            logger.info("Using cached project analysis", project_id=project["id"])
            return project["analysis_cache"]

        client = get_ai_client()
        prompt = build_analyzer_prompt(project)

        try:
            raw_output = await client.generate(
                prompt=prompt,
                max_tokens=512,
                temperature=0.3,  # low temp for factual analysis
                system_prompt="You are a technical recruiter analyzing student projects. Always respond with valid JSON only."
            )

            # Parse JSON response
            analysis = json.loads(raw_output.strip())
            logger.info("Project analysis complete", project_id=project.get("id"))
            return analysis

        except json.JSONDecodeError:
            logger.error("Failed to parse analyzer JSON output", raw=raw_output)
            # Fallback: extract key fields manually
            return self._fallback_analysis(project)

    def _fallback_analysis(self, project: dict) -> dict:
        return {
            "problem": project.get("problem_solved", ""),
            "value": f"Solves {project.get('problem_solved', '')}",
            "technical_depth": "medium",
            "audience_relevance": "recruiters, developers",
            "angles": ["problem_solution", "achievement"]
        }
```

**Analyzer Prompt (`app/ai/prompts/analyzer_prompts.py`):**
```python
def build_analyzer_prompt(project: dict) -> str:
    tech_stack = ", ".join(project.get("tech_stack", []))
    readme = project.get("readme_context", "")[:1000]  # further limit for analysis
    
    return f"""Analyze this student project and respond with ONLY a JSON object. No explanations.

Project Title: {project.get("title")}
Tech Stack: {tech_stack}
Problem Solved: {project.get("problem_solved")}
Results/Impact: {project.get("results_impact", "Not specified")}
README Excerpt: {readme}

Respond ONLY with this JSON structure:
{{
  "problem": "<core problem in one sentence>",
  "value": "<key value proposition>",
  "technical_depth": "low|medium|high",
  "audience_relevance": "<who would care about this>",
  "angles": ["<best angle 1>", "<best angle 2>"],
  "key_achievement": "<most impressive aspect>",
  "suggested_hook_theme": "<emotion or angle for opening hook>"
}}"""
```

### Angle Engine (`app/ai/pipeline/angle_engine.py`)
```python
from typing import List
from app.ai.constants import CONTENT_ANGLES

class AngleEngine:
    """
    Selects the best content angle based on project analysis.
    Pure logic — no AI call needed.
    """

    ANGLE_PRIORITY = {
        "achievement": ["results_impact", "key_achievement"],
        "problem_solution": ["problem_solved"],
        "storytelling": [],  # works for all projects
        "technical_breakdown": ["tech_stack"],
        "learning_journey": [],  # good default for students
        "internship_focused": [],  # always valid
    }

    def select_angle(self, analysis: dict, preferred_angle: str = None) -> str:
        if preferred_angle and preferred_angle in CONTENT_ANGLES:
            return preferred_angle

        # Use AI-suggested angle from analysis
        suggested = analysis.get("angles", [])
        if suggested and suggested[0] in CONTENT_ANGLES:
            return suggested[0]

        # Default fallback for students
        return "problem_solution"
```

### Hook Generator (`app/ai/pipeline/hook_generator.py`)
```python
from app.ai.client.factory import get_ai_client
from app.ai.prompts.hook_prompts import build_hook_prompt

class HookGenerator:
    """Generates the opening hook line for the LinkedIn post."""

    async def generate(self, project: dict, analysis: dict, angle: str) -> str:
        client = get_ai_client()
        prompt = build_hook_prompt(project, analysis, angle)
        hook = await client.generate(
            prompt=prompt,
            max_tokens=100,
            temperature=0.8,  # higher temp for creative hooks
            system_prompt="You write viral LinkedIn opening hooks for student developers. One line only. No hashtags. No emojis."
        )
        return hook.strip().strip('"')
```

**Hook Prompt (`app/ai/prompts/hook_prompts.py`):**
```python
def build_hook_prompt(project: dict, analysis: dict, angle: str) -> str:
    return f"""Write ONE powerful opening hook for a LinkedIn post about this student project.

Project: {project.get("title")}
Problem: {analysis.get("problem")}
Key Achievement: {analysis.get("key_achievement")}
Content Angle: {angle}
Hook Theme: {analysis.get("suggested_hook_theme")}

Rules:
- Maximum 15 words
- Must stop the scroll
- No "I'm excited to share" or "Thrilled to announce"
- No hashtags or emojis
- Make it relatable to {analysis.get("audience_relevance")}

Write ONLY the hook line:"""
```

### Post Generator (`app/ai/pipeline/post_generator.py`)
```python
from app.ai.client.factory import get_ai_client
from app.ai.prompts.post_prompts import build_post_prompt

class PostGenerator:
    """Generates the full LinkedIn post body."""

    async def generate(
        self,
        project: dict,
        analysis: dict,
        angle: str,
        hook: str,
        tone: str = "professional",
        target_audience: str = "recruiters"
    ) -> str:
        client = get_ai_client()
        prompt = build_post_prompt(project, analysis, angle, hook, tone, target_audience)
        post = await client.generate(
            prompt=prompt,
            max_tokens=800,
            temperature=0.7,
            system_prompt="""You are an expert LinkedIn ghostwriter for student developers.
Write posts that sound like a real student wrote them — not AI-generated marketing copy.
Keep paragraphs short (2-3 lines). Use line breaks between sections."""
        )
        return post.strip()
```

**Post Prompt (`app/ai/prompts/post_prompts.py`):**
```python
def build_post_prompt(project, analysis, angle, hook, tone, audience) -> str:
    tech = ", ".join(project.get("tech_stack", []))
    return f"""Write a complete LinkedIn post for this student project.

HOOK (already written, use this as the opening): {hook}

Project Details:
- Title: {project.get("title")}
- Tech Stack: {tech}
- Problem: {analysis.get("problem")}
- Value: {analysis.get("value")}
- Key Achievement: {analysis.get("key_achievement")}
- Results: {project.get("results_impact", "Not specified")}

Content Angle: {angle}
Tone: {tone}
Target Audience: {audience}

Post Structure:
1. Hook (already written above — use it exactly)
2. Context (2-3 lines: what problem and why it matters)
3. Solution (2-3 lines: what you built and how)
4. Results (1-2 lines: impact, metrics if available)
5. Learning (1-2 lines: what you learned)
6. CTA (1 line: invite connection/feedback)
7. Hashtags (4-5 relevant hashtags)

Write the FULL post now:"""
```

### Humanizer Layer (`app/ai/pipeline/humanizer.py`)
```python
import re
from app.ai.constants import BANNED_AI_PHRASES
from app.ai.client.factory import get_ai_client

class HumanizerLayer:
    """
    Two-step humanization:
    1. Rule-based: remove banned AI phrases
    2. AI-based: rewrite to sound more authentic
    """

    def remove_banned_phrases(self, text: str) -> str:
        cleaned = text
        for phrase in BANNED_AI_PHRASES:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
        # Clean up double spaces or awkward gaps
        cleaned = re.sub(r'  +', ' ', cleaned)
        return cleaned.strip()

    async def humanize(self, post: str) -> str:
        # Step 1: Rule-based cleaning
        cleaned = self.remove_banned_phrases(post)

        # Step 2: AI refinement for authenticity
        client = get_ai_client()
        prompt = f"""Rewrite this LinkedIn post to sound like a real student wrote it.

Original post:
{cleaned}

Rules:
- Keep all facts, numbers, and tech stack mentions exactly as-is
- Remove any remaining AI clichés
- Make it conversational but professional
- Keep the same structure and length
- First person ("I built", "I learned")
- Sound human — not a press release
- Keep all hashtags at the end

Rewritten post:"""

        humanized = await client.generate(
            prompt=prompt,
            max_tokens=900,
            temperature=0.6,
            system_prompt="You are a LinkedIn writing coach who helps students sound authentic, not robotic."
        )
        return humanized.strip()
```

---

## Pipeline Orchestrator

```python
# app/ai/pipeline/orchestrator.py
from datetime import datetime
from app.ai.pipeline.analyzer import ProjectAnalyzer
from app.ai.pipeline.angle_engine import AngleEngine
from app.ai.pipeline.hook_generator import HookGenerator
from app.ai.pipeline.post_generator import PostGenerator
from app.ai.pipeline.humanizer import HumanizerLayer
from app.ai.prompts.version import PROMPT_VERSION
from app.repositories.project_repository import ProjectRepository
from app.utils.logger import logger
import time

class ContentGenerationPipeline:
    """
    Full pipeline: Project → Analysis → Angle → Hook → Post → Humanize
    """

    def __init__(self):
        self.analyzer = ProjectAnalyzer()
        self.angle_engine = AngleEngine()
        self.hook_gen = HookGenerator()
        self.post_gen = PostGenerator()
        self.humanizer = HumanizerLayer()
        self.project_repo = ProjectRepository()

    async def run(
        self,
        project: dict,
        tone: str = "professional",
        target_audience: str = "recruiters",
        preferred_angle: str = None
    ) -> dict:
        start_time = time.time()
        
        logger.info("Pipeline starting", project_id=project.get("id"), tone=tone)

        # Step 1: Analyze project
        analysis = await self.analyzer.analyze(project)

        # Cache analysis in DB if not already cached
        if not project.get("analysis_cache"):
            await self.project_repo.update_analysis_cache(project["id"], analysis)

        # Step 2: Select angle
        angle = self.angle_engine.select_angle(analysis, preferred_angle)
        logger.info("Angle selected", angle=angle)

        # Step 3: Generate hook
        hook = await self.hook_gen.generate(project, analysis, angle)
        logger.info("Hook generated", hook=hook[:50])

        # Step 4: Generate full post
        raw_post = await self.post_gen.generate(
            project, analysis, angle, hook, tone, target_audience
        )

        # Step 5: Humanize
        final_post = await self.humanizer.humanize(raw_post)

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info("Pipeline complete", duration_ms=duration_ms)

        return {
            "content": final_post,
            "angle": angle,
            "hook": hook,
            "analysis": analysis,
            "prompt_version": PROMPT_VERSION,
            "duration_ms": duration_ms
        }
```

---

## API Endpoints
None directly — the pipeline is called by the generation service in Phase 05. This phase is pure AI infrastructure.

---

## Backend Tasks
1. Create entire `app/ai/` directory structure
2. Implement `BaseAIClient` + `GeminiClient` + `HuggingFaceClient`
3. Implement `AIClientFactory`
4. Write all 5 prompt builder functions
5. Implement `ProjectAnalyzer`, `AngleEngine`, `HookGenerator`, `PostGenerator`, `HumanizerLayer`
6. Implement `ContentGenerationPipeline` orchestrator
7. Write unit tests for each pipeline stage with mocked AI client
8. Write integration test for full pipeline flow

---

## Frontend Tasks
None in this phase. Pipeline is backend-only.

---

## AI Workflow Tasks

### Full Pipeline Execution Flow:
```
project_data
    ↓ 
ProjectAnalyzer.analyze()
    → extracts: problem, value, depth, angles
    → caches result in MongoDB
    ↓
AngleEngine.select_angle()
    → pure logic: best angle for this project + user preference
    ↓
HookGenerator.generate()
    → AI call: 1-line hook (temp=0.8 for creativity)
    ↓
PostGenerator.generate()
    → AI call: full post body (temp=0.7)
    ↓
HumanizerLayer.humanize()
    → Rule-based banned phrase removal
    → AI call: authenticity rewrite (temp=0.6)
    ↓
{content, angle, hook, analysis, prompt_version, duration_ms}
```

Total AI calls per generation: **4** (analyze, hook, post, humanize)

---

## Scheduler / Background Tasks
None in this phase.

---

## Security Considerations
- API keys must only be in `.env` — never hardcoded
- README must be truncated before sending to LLM — prevents token explosion and cost abuse
- Analyzer prompt instructs "JSON only" to prevent prompt injection via project data
- User-supplied content (project title, problem) passed as data, not as instruction — prevents prompt injection

---

## Environment Variables

```env
# Add to backend .env
LLM_PROVIDER=gemini         # or huggingface
GEMINI_API_KEY=AIzaSy...
HUGGINGFACE_API_KEY=hf_...
```

---

## Third-Party Services Required
| Service | Purpose | Signup |
|---------|---------|--------|
| Google Gemini API | Primary LLM (recommended) | aistudio.google.com (free tier) |
| HuggingFace Inference | Fallback LLM | huggingface.co/settings/tokens |

---

## Implementation Steps (Exact Order)

1. Create `app/ai/` directory structure
2. Implement `app/ai/client/base.py`
3. Implement `app/ai/client/gemini.py` (start with Gemini — free and fast)
4. Implement `app/ai/client/factory.py`
5. Add Gemini API key to `.env`
6. Test Gemini client in isolation: `python -c "import asyncio; from app.ai.client.gemini import GeminiClient; print(asyncio.run(GeminiClient().generate('Hello')))"`
7. Write `app/ai/constants.py`
8. Write `app/ai/prompts/version.py` and all prompt files
9. Implement `ProjectAnalyzer` → test JSON output parsing
10. Implement `AngleEngine` → test angle selection logic (no AI needed)
11. Implement `HookGenerator` → test with a real project
12. Implement `PostGenerator` → test full post output
13. Implement `HumanizerLayer` → verify banned phrases removed
14. Implement `ContentGenerationPipeline.run()` 
15. Write integration test with real project data
16. Commit: `git commit -m "Phase 04: AI pipeline — analyzer, angle engine, generator, humanizer"`

---

## Testing Strategy

```python
# tests/ai/test_pipeline.py
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_angle_engine_uses_preferred():
    engine = AngleEngine()
    result = engine.select_angle({}, preferred_angle="achievement")
    assert result == "achievement"

@pytest.mark.asyncio
async def test_humanizer_removes_banned_phrases():
    h = HumanizerLayer()
    text = "I'm excited to announce this game-changer that will revolutionize things."
    # Mock the AI call
    with patch.object(h, 'humanize', new_callable=AsyncMock) as mock_h:
        cleaned = h.remove_banned_phrases(text)
    assert "excited to announce" not in cleaned
    assert "game-changer" not in cleaned
    assert "revolutionize" not in cleaned

@pytest.mark.asyncio
async def test_pipeline_full_flow():
    with patch("app.ai.pipeline.orchestrator.get_ai_client") as mock_factory:
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=[
            '{"problem": "test", "value": "test", "technical_depth": "high", "audience_relevance": "devs", "angles": ["achievement"], "key_achievement": "built it", "suggested_hook_theme": "challenge"}',
            "I built something that changed everything",
            "Full post content here...",
            "Humanized post content here..."
        ])
        mock_factory.return_value = mock_client
        
        pipeline = ContentGenerationPipeline()
        result = await pipeline.run(
            project={"id": "test", "title": "AgriLenses", "tech_stack": ["Python"], "problem_solved": "Crop diseases"},
            tone="professional"
        )
        assert "content" in result
        assert "angle" in result
        assert result["prompt_version"] == "v1.2"
```

---

## Edge Cases
- LLM returns malformed JSON in analyzer → `_fallback_analysis()` used
- LLM times out → raise `AppException("AI_TIMEOUT", "Generation took too long. Please try a shorter description.")`
- `analysis_cache` exists in DB → use it, skip API call
- Banned phrase appears mid-word (e.g. "leveraged") → regex uses word boundary to avoid false positives
- HuggingFace model loading (cold start) → 503 for first call → implement retry with `httpx`

---

## Deliverables / Checklist

- [ ] `BaseAIClient` abstract class
- [ ] `GeminiClient` working with real API key
- [ ] `HuggingFaceClient` implemented (even if not tested with real key)
- [ ] `AIClientFactory` switches correctly via `LLM_PROVIDER` env var
- [ ] All 5 prompt builder functions written
- [ ] `ProjectAnalyzer` with JSON parsing + fallback
- [ ] `AngleEngine` with angle selection logic
- [ ] `HookGenerator` producing 1-line hooks
- [ ] `PostGenerator` producing full posts
- [ ] `HumanizerLayer` rule-based + AI-based cleaning
- [ ] `ContentGenerationPipeline.run()` orchestrating all steps
- [ ] Analysis caching in `project_repository.update_analysis_cache`
- [ ] All pipeline stages independently testable
- [ ] Integration test with mocked AI passes
- [ ] `PROMPT_VERSION = "v1.2"` set

---

## Definition of Completion
`ContentGenerationPipeline.run(project_data)` produces a full, humanized LinkedIn post. Each stage is independently testable. Switching `LLM_PROVIDER=gemini` vs `LLM_PROVIDER=huggingface` changes the underlying client without touching pipeline logic. Analysis results are cached in MongoDB after first run.