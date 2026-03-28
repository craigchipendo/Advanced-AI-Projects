"""
planning_agent.py  –  Planner and Executor built with Google ADK + Groq.

Uses the same Groq/LiteLlm backend as agents.py.
"""

from __future__ import annotations

import ast
import json
import re
from typing import List, Tuple

from google.adk.agents import LlmAgent
from src.agents import _run_agent, _make_llm
from src.agents import research_agent, writer_agent, editor_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_json_block(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip("` \n")


def _coerce_to_list(s: str) -> List[str]:
    """JSON → ast.literal_eval → code-fence strip → empty list."""
    try:
        obj = json.loads(s)
        if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
            return obj[:7]
    except json.JSONDecodeError:
        pass
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
            return obj[:7]
    except Exception:
        pass
    if s.startswith("```") and s.endswith("```"):
        inner = s.strip("`")
        try:
            obj = ast.literal_eval(inner)
            if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
                return obj[:7]
        except Exception:
            pass
    return []


# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

_REQUIRED_FIRST = (
    "Research agent: Use Tavily to perform a broad web search and collect top relevant "
    "items (title, authors, year, venue/source, URL, DOI if available)."
)
_REQUIRED_SECOND = (
    "Research agent: For each collected item, search on arXiv to find matching "
    "preprints/versions and record arXiv URLs (if they exist)."
)
_REQUIRED_FINAL = (
    "Writer agent: Generate the final comprehensive Markdown report with inline "
    "citations and a complete References section with clickable links."
)


def _ensure_contract(steps_list: List[str]) -> List[str]:
    if not steps_list:
        return [
            _REQUIRED_FIRST,
            _REQUIRED_SECOND,
            "Research agent: Synthesize and rank findings by relevance, recency, and authority; deduplicate by title/DOI.",
            "Writer agent: Draft a structured outline based on the ranked evidence.",
            "Editor agent: Review for coherence, coverage, and citation completeness; request fixes.",
            _REQUIRED_FINAL,
        ]

    steps_list = [s for s in steps_list if isinstance(s, str)]

    if not steps_list or steps_list[0] != _REQUIRED_FIRST:
        steps_list = [_REQUIRED_FIRST] + steps_list

    if len(steps_list) < 2 or steps_list[1] != _REQUIRED_SECOND:
        steps_list = (
            [steps_list[0], _REQUIRED_SECOND]
            + [s for s in steps_list[1:] if "arXiv" not in s or "For each collected item" in s]
        )

    if _REQUIRED_FINAL not in steps_list:
        steps_list.append(_REQUIRED_FINAL)

    return steps_list[:7]


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def planner_agent(topic: str) -> List[str]:
    """Use a Groq LlmAgent to produce a step-by-step research plan."""
    planner = LlmAgent(
        name="planner_agent",
        model=_make_llm(),
        instruction="""You are a planning agent responsible for organizing a research workflow using multiple intelligent agents.

🧠 Available agents:
- Research agent: MUST begin with a broad **web search using Tavily** to identify only **relevant** and **authoritative** items (e.g., high-impact venues, seminal works, surveys, or recent comprehensive sources). The output of this step MUST capture for each candidate: title, authors, year, venue/source, URL, and (if available) DOI.
- Research agent: AFTER the Tavily step, perform a **targeted arXiv search** ONLY for the candidates discovered in the web step (match by title/author/DOI). If an arXiv preprint/version exists, record its arXiv URL and version info. Do NOT run a generic arXiv search detached from the Tavily results.
- Writer agent: drafts based on research findings.
- Editor agent: reviews, reflects on, and improves drafts.

🎯 Produce a clear step-by-step research plan **as a valid Python list of strings** (no markdown, no explanations).
Each step must be atomic, actionable, and assigned to one of the agents.
Maximum of 7 steps.

🚫 DO NOT include steps like "create CSV", "set up repo", "install packages".
✅ Focus on meaningful research tasks (search, extract, rank, draft, revise).
✅ The FIRST step MUST be exactly:
"Research agent: Use Tavily to perform a broad web search and collect top relevant items (title, authors, year, venue/source, URL, DOI if available)."
✅ The SECOND step MUST be exactly:
"Research agent: For each collected item, search on arXiv to find matching preprints/versions and record arXiv URLs (if they exist)."

🔚 The FINAL step MUST instruct the writer agent to generate a comprehensive Markdown report that:
- Uses all findings and outputs from previous steps
- Includes inline citations (e.g., [1], (Wikipedia/arXiv))
- Includes a References section with clickable links for all citations
- Preserves earlier sources
- Is detailed and self-contained
""",
    )

    prompt = f'Produce a research plan (Python list of strings) for the topic: "{topic}"'
    raw, _ = _run_agent(planner, prompt)
    raw = clean_json_block(raw)
    steps = _coerce_to_list(raw)
    return _ensure_contract(steps)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def executor_agent_step(
    step_title: str, history: list, prompt: str
) -> Tuple[str, str, str]:
    """Execute one step of the plan. Returns (step_title, agent_name, output_text)."""
    context = f"📘 User Prompt:\n{prompt}\n\n📜 History so far:\n"
    for i, (desc, agent, output) in enumerate(history):
        if "draft" in desc.lower() or agent == "writer_agent":
            context += f"\n✍️ Draft (Step {i + 1}):\n{output.strip()}\n"
        elif "feedback" in desc.lower() or agent == "editor_agent":
            context += f"\n🧠 Feedback (Step {i + 1}):\n{output.strip()}\n"
        elif "research" in desc.lower() or agent == "research_agent":
            context += f"\n🔍 Research (Step {i + 1}):\n{output.strip()}\n"
        else:
            context += f"\n🧩 Other (Step {i + 1}) by {agent}:\n{output.strip()}\n"

    enriched_task = f"{context}\n\n🧩 Your next task:\n{step_title}"

    step_lower = step_title.lower()
    if "research" in step_lower:
        content, _ = research_agent(prompt=enriched_task)
        print("🔍 Research Agent Output:", content[:300])
        return step_title, "research_agent", content
    elif "draft" in step_lower or "write" in step_lower or "writer" in step_lower:
        content, _ = writer_agent(prompt=enriched_task)
        return step_title, "writer_agent", content
    elif any(kw in step_lower for kw in ("revise", "edit", "feedback", "editor")):
        content, _ = editor_agent(prompt=enriched_task)
        return step_title, "editor_agent", content
    else:
        raise ValueError(f"Unknown step type: {step_title!r}")
