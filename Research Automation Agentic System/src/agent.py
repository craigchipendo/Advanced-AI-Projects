"""
agent.py – ADK entry point for `adk web` and `adk run`.

`adk web` discovers `root_agent` from this module.

The root_agent is an orchestrator that runs the full research pipeline:
  1. Research agent  – web search (Tavily), arXiv, Wikipedia
  2. Writer agent    – drafts a structured academic Markdown report
  3. Editor agent    – refines and polishes the draft

It uses ADK's AgentTool to expose each specialist as a callable tool,
then an orchestrator LlmAgent decides when and in what order to call them —
matching the same pipeline that main.py drives via planner_agent.

Backend: Groq (free tier) via LiteLlm.
"""

from datetime import datetime

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from src.agents import _make_llm
from src.research_tools import TOOL_FUNCTIONS

# ---------------------------------------------------------------------------
# Specialist agents (same instructions as in agents.py runner functions)
# ---------------------------------------------------------------------------

_research_agent = LlmAgent(
    name="research_agent",
    model=_make_llm(),
    tools=TOOL_FUNCTIONS,
    instruction=f"""You are an advanced research assistant with expertise in information retrieval and academic research methodology.

## AVAILABLE TOOLS
- **tavily_search_tool**: General web search for recent news, blogs, industry reports, non-academic sources.
- **arxiv_search_tool**: Academic papers in CS, Math, Physics, Stats, Biology, Finance, EE, Economics.
- **wikipedia_search_tool**: Background knowledge, definitions, historical context.

## METHODOLOGY
1. Identify the core research questions and relevant knowledge domains.
2. Choose the right tools for the topic (use multiple tools when needed).
3. Execute searches with effective keywords.
4. Synthesise findings with clear source attribution (title, URL, authors, date).

## OUTPUT FORMAT
1. **Research Approach** – tools used and why.
2. **Key Findings** – organised by sub-topic or source.
3. **Source Details** – URLs, titles, authors, dates.
4. **Limitations** – any gaps or caveats.

Today is {datetime.now().strftime('%Y-%m-%d')}.
""",
)

_writer_agent = LlmAgent(
    name="writer_agent",
    model=_make_llm(),
    instruction="""You are an expert academic writer with a PhD-level understanding of scholarly communication.
Your task is to synthesize research materials into a comprehensive, well-structured academic report.

## MANDATORY STRUCTURE
1. Title  2. Abstract (100-150 words)  3. Introduction  4. Background/Literature Review
5. Key Findings/Results  6. Discussion  7. Conclusion  8. References

## RULES
- Use numeric inline citations [1], [2], etc. for every borrowed idea.
- References section: complete entries for every citation with clickable HTML links (target="_blank").
- Preserve ALL URLs, DOIs, and bibliographic data from source materials.
- Maintain formal academic tone; no meta-commentary about the writing process.
- Output Markdown only. Length: 1500-3000 words.
""",
)

_editor_agent = LlmAgent(
    name="editor_agent",
    model=_make_llm(),
    instruction="""You are a professional academic editor. Refine and elevate the scholarly text provided.

## YOUR TASKS
- Improve clarity, precision, and logical flow.
- Strengthen thesis statements and arguments.
- Ensure proper citation integration; preserve all [N] citations and the References section.
- Standardise terminology and eliminate redundancies.
- Return only the revised Markdown text — no editorial commentary.
""",
)

# ---------------------------------------------------------------------------
# Root orchestrator
# ---------------------------------------------------------------------------

root_agent = LlmAgent(
    name="orchestrator_agent",
    model=_make_llm(),
    tools=[
        AgentTool(agent=_research_agent),
        AgentTool(agent=_writer_agent),
        AgentTool(agent=_editor_agent),
    ],
    instruction=f"""You are a research orchestrator that produces high-quality academic reports by coordinating three specialist agents.

## YOUR PIPELINE — follow these steps in order for every user request:

**Step 1 — Research (run TWICE):**
- First call research_agent with: "Use Tavily to perform a broad web search on [TOPIC] and collect top relevant items (title, authors, year, venue/source, URL, DOI if available)."
- Second call research_agent with: "For each collected item, search on arXiv to find matching preprints/versions and record arXiv URLs (if they exist)."

**Step 2 — Write:**
- Call writer_agent with ALL research findings from Step 1.
- Instruct it to produce a comprehensive Markdown report with inline citations [1],[2],... and a complete References section with clickable links.

**Step 3 — Edit:**
- Call editor_agent with the full draft from Step 2.
- Instruct it to improve clarity, flow, and citation integrity.

**Step 4 — Return:**
- Return the final edited Markdown report as your response. Do not add any wrapper text — output the report directly.

## RULES
- Always complete ALL three steps before responding.
- Never skip the research step.
- Never fabricate sources — only use URLs and papers found by research_agent.
- Today is {datetime.now().strftime('%Y-%m-%d')}.
""",
)
