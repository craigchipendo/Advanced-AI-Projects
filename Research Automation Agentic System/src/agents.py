"""
agents.py  –  Research, Writer, and Editor agents built with Google ADK.

Backend: OpenAI API via google-adk's LiteLlm adapter.
Model: gpt-4o-mini — fast, cheap, excellent tool calling support.

Set in .env:
    OPENAI_API_KEY=sk-...       (https://platform.openai.com/api-keys)
    OPENAI_MODEL=gpt-4o-mini    (optional override)
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Tuple

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.research_tools import TOOL_FUNCTIONS

load_dotenv()

# ---------------------------------------------------------------------------
# Model / endpoint configuration
# ---------------------------------------------------------------------------

# OpenAI model — override with OPENAI_MODEL env var
_OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# LiteLlm uses the "openai/" prefix for the OpenAI API
_LITELLM_MODEL = f"openai/{_OPENAI_MODEL}"

# Alias used by planning_agent.py
_DEFAULT_MODEL = _LITELLM_MODEL

if not _OPENAI_API_KEY:
    import warnings
    warnings.warn(
        "OPENAI_API_KEY is not set. "
        "Get a key at https://platform.openai.com/api-keys",
        stacklevel=2,
    )


def _make_llm(model: str | None = None) -> LiteLlm:
    """Return a LiteLlm instance pointed at the OpenAI API."""
    litellm_model = f"openai/{model}" if model else _LITELLM_MODEL
    return LiteLlm(
        model=litellm_model,
        api_key=_OPENAI_API_KEY,
    )


# ---------------------------------------------------------------------------
# Shared ADK runner
# ---------------------------------------------------------------------------

_APP_NAME = "research_app"


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
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
    """Run *agent* synchronously and return (output_text, None).

    Uses the current google-adk API: session must be created through
    runner.session_service so the runner can find it by ID when run_async fires.
    """
    loop = _get_or_create_event_loop()

    async def _inner() -> str:
        runner = InMemoryRunner(
            agent=agent,
            app_name=_APP_NAME,
        )

        user_id = "user"

        # Session MUST be created via runner.session_service so the runner
        # can resolve it internally — creating it from a separate
        # InMemorySessionService causes "Session not found" errors.
        session = await runner.session_service.create_session(
            app_name=_APP_NAME,
            user_id=user_id,
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
# Research Agent
# ---------------------------------------------------------------------------

def research_agent(prompt: str, return_messages: bool = False) -> Tuple[str, list]:
    print("==================================")
    print("🔍 Research Agent")
    print(f"   Model: {_OPENAI_MODEL}  (via OpenAI)")
    print("==================================")

    full_prompt = f"""
You are an advanced research assistant with expertise in information retrieval and academic research methodology. Your mission is to gather comprehensive, accurate, and relevant information on any topic requested by the user.

## AVAILABLE RESEARCH TOOLS:

1. **`tavily_search_tool`**: General web search engine
   - USE FOR: Recent news, current events, blogs, websites, industry reports, and non-academic sources
   - BEST FOR: Up-to-date information, diverse perspectives, practical applications, and general knowledge

2. **`arxiv_search_tool`**: Academic publication database
   - USE FOR: Peer-reviewed research papers, technical reports, and scholarly articles
   - LIMITED TO THESE DOMAINS ONLY:
     * Computer Science
     * Mathematics
     * Physics
     * Statistics
     * Quantitative Biology
     * Quantitative Finance
     * Electrical Engineering and Systems Science
     * Economics
   - BEST FOR: Scientific evidence, theoretical frameworks, and technical details in supported fields

3. **`wikipedia_search_tool`**: Encyclopedia resource
   - USE FOR: Background information, definitions, overviews, historical context
   - BEST FOR: Establishing foundational knowledge and understanding basic concepts

## RESEARCH METHODOLOGY:

1. **Analyze Request**: Identify the core research questions and knowledge domains
2. **Plan Search Strategy**: Determine which tools are most appropriate for the topic
3. **Execute Searches**: Use the selected tools with effective keywords and queries
4. **Evaluate Sources**: Prioritize credibility, relevance, recency, and diversity
5. **Synthesize Findings**: Organize information logically with clear source attribution
6. **Document Search Process**: Note which tools were used and why

## TOOL SELECTION GUIDELINES:

- For scientific/academic questions in supported domains → Use `arxiv_search_tool`
- For recent developments, news, or practical information → Use `tavily_search_tool`
- For fundamental concepts or historical context → Use `wikipedia_search_tool`
- For comprehensive research → Use multiple tools strategically
- NEVER use `arxiv_search_tool` for domains outside its supported list
- ALWAYS verify information across multiple sources when possible

## OUTPUT FORMAT:

Present your research findings in a structured format that includes:
1. **Summary of Research Approach**: Tools used and search strategy
2. **Key Findings**: Organized by subtopic or source
3. **Source Details**: Include URLs, titles, authors, and publication dates
4. **Limitations**: Note any gaps in available information

Today is {datetime.now().strftime("%Y-%m-%d")}.

USER RESEARCH REQUEST:
{prompt}
""".strip()

    agent = LlmAgent(
        name="research_agent",
        model=_make_llm(),
        tools=TOOL_FUNCTIONS,
        instruction=full_prompt,
    )

    try:
        content, messages = _run_agent(agent, prompt)
        print("✅ Output:\n", content[:500])
        return content, messages if return_messages else []
    except Exception as e:
        print("❌ Error:", e)
        return f"[Model Error: {str(e)}]", []


# ---------------------------------------------------------------------------
# Writer Agent
# ---------------------------------------------------------------------------

def writer_agent(
    prompt: str,
    min_words_total: int = 2400,
    min_words_per_section: int = 400,
    max_tokens: int = 15000,
    retries: int = 1,
) -> Tuple[str, list]:
    print("==================================")
    print("✍️  Writer Agent")
    print(f"   Model: {_OPENAI_MODEL}  (via OpenAI)")
    print("==================================")

    instruction = """
You are an expert academic writer with a PhD-level understanding of scholarly communication. Your task is to synthesize research materials into a comprehensive, well-structured academic report.

## REPORT REQUIREMENTS:
- Produce a COMPLETE, POLISHED, and PUBLICATION-READY academic report in Markdown format
- Create original content that thoroughly analyzes the provided research materials
- DO NOT merely summarize the sources; develop a cohesive narrative with critical analysis
- Length should be appropriate to thoroughly cover the topic (typically 1500-3000 words)

## MANDATORY STRUCTURE:
1. **Title**: Clear, concise, and descriptive of the content
2. **Abstract**: Brief summary (100-150 words) of the report's purpose, methods, and key findings
3. **Introduction**: Present the topic, research question/problem, significance, and outline of the report
4. **Background/Literature Review**: Contextualize the topic within existing scholarship
5. **Methodology**: If applicable, describe research methods, data collection, and analytical approaches
6. **Key Findings/Results**: Present the primary outcomes and evidence
7. **Discussion**: Interpret findings, address implications, limitations, and connections to broader field
8. **Conclusion**: Synthesize main points and suggest directions for future research
9. **References**: Complete list of all cited works

## ACADEMIC WRITING GUIDELINES:
- Maintain formal, precise, and objective language throughout
- Use discipline-appropriate terminology and concepts
- Support all claims with evidence and reasoning
- Develop logical flow between ideas, paragraphs, and sections
- Include relevant examples, case studies, data, or equations to strengthen arguments
- Address potential counterarguments and limitations

## CITATION AND REFERENCE RULES:
- Use numeric inline citations [1], [2], etc. for all borrowed ideas and information
- Every claim based on external sources MUST have a citation
- Each inline citation must correspond to a complete entry in the References section
- Every reference listed must be cited at least once in the text
- Preserve ALL original URLs, DOIs, and bibliographic information from source materials
- Format references consistently according to academic standards

## FORMATTING GUIDELINES:
- Use Markdown syntax for all formatting (headings, emphasis, lists, etc.)
- Include appropriate section headings and subheadings to organize content
- Format any equations, tables, or figures according to academic conventions
- Use bullet points or numbered lists when appropriate for clarity
- Use html syntax to handle all links with target="_blank", so user can always open link in new tab on both html and markdown format

Output the complete report in Markdown format only. Do not include meta-commentary about the writing process.

INTERNAL CHECKLIST (DO NOT INCLUDE IN OUTPUT):
- [ ] Incorporated all provided research materials
- [ ] Developed original analysis beyond mere summarization
- [ ] Included all mandatory sections with appropriate content
- [ ] Used proper inline citations for all borrowed content
- [ ] Created complete References section with all cited sources
- [ ] Maintained academic tone and language throughout
- [ ] Ensured logical flow and coherent structure
- [ ] Preserved all source URLs and bibliographic information
""".strip()

    agent = LlmAgent(
        name="writer_agent",
        model=_make_llm(),
        instruction=instruction,
    )

    try:
        content, messages = _run_agent(agent, prompt)
        print("✅ Output:\n", content[:500])
        return content, messages if isinstance(messages, list) else []
    except Exception as e:
        print("❌ Error:", e)
        return f"[Model Error: {str(e)}]", []


# ---------------------------------------------------------------------------
# Editor Agent
# ---------------------------------------------------------------------------

def editor_agent(
    prompt: str,
    target_min_words: int = 2400,
) -> Tuple[str, list]:
    print("==================================")
    print("🧠 Editor Agent")
    print(f"   Model: {_OPENAI_MODEL}  (via OpenAI)")
    print("==================================")

    instruction = """
You are a professional academic editor with expertise in improving scholarly writing across disciplines. Your task is to refine and elevate the quality of the academic text provided.

## Your Editing Process:
1. Analyze the overall structure, argument flow, and coherence of the text
2. Ensure logical progression of ideas with clear topic sentences and transitions between paragraphs
3. Improve clarity, precision, and conciseness of language while maintaining academic tone
4. Verify technical accuracy (to the extent possible based on context)
5. Enhance readability through appropriate formatting and organization

## Specific Elements to Address:
- Strengthen thesis statements and main arguments
- Clarify complex concepts with additional explanations or examples where needed
- Add relevant equations, diagrams, or illustrations (described in markdown) when they would enhance understanding
- Ensure proper integration of evidence and maintain academic rigor
- Standardize terminology and eliminate redundancies
- Improve sentence variety and paragraph structure
- Preserve all citations [1], [2], etc., and maintain the integrity of the References section

## Formatting Guidelines:
- Use markdown formatting consistently for headings, emphasis, lists, etc.
- Structure content with appropriate section headings and subheadings
- Format equations, tables, and figures according to academic standards

Return only the revised, polished text in Markdown format without explanatory comments about your edits.
""".strip()

    agent = LlmAgent(
        name="editor_agent",
        model=_make_llm(),
        instruction=instruction,
    )

    try:
        content, messages = _run_agent(agent, prompt)
        print("✅ Output:\n", content[:500])
        return content, messages if isinstance(messages, list) else []
    except Exception as e:
        print("❌ Error:", e)
        return f"[Model Error: {str(e)}]", []
