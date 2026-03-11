"""
agents.py  –  Research, Writer, and Editor agents built with Google ADK.

Each agent is a google.adk.agents.LlmAgent configured with Gemini and, where
appropriate, the research tools defined in research_tools.py.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Tuple

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from src.research_tools import TOOL_FUNCTIONS

load_dotenv()

# ---------------------------------------------------------------------------
# Shared ADK infrastructure
# ---------------------------------------------------------------------------

_APP_NAME = "research_app"

# Default Gemini model – override with GEMINI_MODEL env var
_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """
    Safely get or create an asyncio event loop.

    FastAPI runs sync endpoints in a thread pool. Each worker thread
    may not have a running event loop, so we create one if needed.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _run_agent(agent: LlmAgent, prompt: str) -> Tuple[str, None]:
    """Run *agent* synchronously with *prompt* and return (output_text, None).

    Safe to call from FastAPI background threads: creates a fresh event loop
    when no running loop is available.
    """
    loop = _get_or_create_event_loop()

    async def _inner() -> str:
        # Fresh session service per call to avoid cross-request contamination.
        session_service = InMemorySessionService()
        runner = InMemoryRunner(
            agent=agent,
            app_name=_APP_NAME,
            session_service=session_service,
        )
        user_id = "user"
        session = await runner.session_service.create_session(
            app_name=_APP_NAME, user_id=user_id
        )

        message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=prompt)],
        )

        collected: list[str] = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text:
                        collected.append(part.text)

        return "\n".join(collected) or "[No output produced]"

    return loop.run_until_complete(_inner()), None


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

def _make_research_agent() -> LlmAgent:
    return LlmAgent(
        name="research_agent",
        model=_DEFAULT_MODEL,
        tools=TOOL_FUNCTIONS,
        instruction=f"""You are an advanced research assistant with expertise in information retrieval and academic research.

## AVAILABLE TOOLS
- **tavily_search_tool**: General web search for recent news, blogs, industry reports, non-academic sources.
- **arxiv_search_tool**: Academic papers in CS, Math, Physics, Stats, Biology, Finance, EE, Economics.
- **wikipedia_search_tool**: Background knowledge, definitions, historical context.

## METHODOLOGY
1. Identify the core research questions and relevant knowledge domains.
2. Choose the right tools for the topic (use multiple tools when needed).
3. Execute searches with effective keywords.
4. Synthesize findings with clear source attribution (title, URL, authors, date).

## OUTPUT FORMAT
1. **Research Approach** – tools used and why.
2. **Key Findings** – organised by sub-topic or source.
3. **Source Details** – URLs, titles, authors, dates.
4. **Limitations** – any gaps or caveats.

Today is {datetime.now().strftime('%Y-%m-%d')}.
""",
    )


def _make_writer_agent() -> LlmAgent:
    return LlmAgent(
        name="writer_agent",
        model=_DEFAULT_MODEL,
        instruction="""You are an expert academic writer. Synthesise research materials into a comprehensive, well-structured Markdown report.

## MANDATORY STRUCTURE
1. Title  2. Abstract (100-150 words)  3. Introduction  4. Background / Literature Review
5. Key Findings / Results  6. Discussion  7. Conclusion  8. References

## RULES
- Inline citations: [1], [2], ...  Every claim needs a citation.
- References section: complete entries for every citation, with clickable HTML links (target="_blank").
- Preserve ALL URLs, DOIs, and bibliographic data from source materials.
- Maintain formal academic tone; no meta-commentary about the writing process.
- Output Markdown only.
""",
    )


def _make_editor_agent() -> LlmAgent:
    return LlmAgent(
        name="editor_agent",
        model=_DEFAULT_MODEL,
        instruction="""You are a professional academic editor. Refine and elevate the scholarly text provided.

## YOUR TASKS
- Improve clarity, precision, and logical flow.
- Strengthen thesis statements and arguments.
- Ensure proper citation integration; preserve all [N] citations and the References section.
- Standardise terminology and eliminate redundancies.
- Return only the revised Markdown text – no editorial commentary.
""",
    )


# ---------------------------------------------------------------------------
# Public agent runner functions
# ---------------------------------------------------------------------------

def research_agent(prompt: str) -> Tuple[str, None]:
    """Run the Research Agent and return (output_text, None)."""
    print("==================================")
    print("🔍 Research Agent")
    print("==================================")
    agent = _make_research_agent()
    content, msgs = _run_agent(agent, prompt)
    print("✅ Output:\n", content[:500])
    return content, msgs


def writer_agent(prompt: str) -> Tuple[str, None]:
    """Run the Writer Agent and return (output_text, None)."""
    print("==================================")
    print("✍️  Writer Agent")
    print("==================================")
    agent = _make_writer_agent()
    content, msgs = _run_agent(agent, prompt)
    print("✅ Output:\n", content[:500])
    return content, msgs


def editor_agent(prompt: str) -> Tuple[str, None]:
    """Run the Editor Agent and return (output_text, None)."""
    print("==================================")
    print("🧠 Editor Agent")
    print("==================================")
    agent = _make_editor_agent()
    content, msgs = _run_agent(agent, prompt)
    print("✅ Output:\n", content[:500])
    return content, msgs
