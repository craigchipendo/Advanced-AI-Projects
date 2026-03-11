"""
planning_agent.py  –  Planner and Executor built with Google ADK.
"""

from __future__ import annotations

import ast
import json
import re
from typing import List, Tuple

from google.adk.agents import LlmAgent
from src.agents import _run_agent, _DEFAULT_MODEL
from src.agents import research_agent, writer_agent, editor_agent


# ---------------------------------------------------------------------------
# Planner
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


def _coerce_to_list(raw: str) -> List[str]:
    """Try JSON → ast.literal_eval → empty list."""
    # Strip code fences
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw.strip())
    raw = re.sub(r"\n?```$", "", raw).strip()
    for parser in (json.loads, ast.literal_eval):
        try:
            obj = parser(raw)
            if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
                return obj[:7]
        except Exception:
            pass
    return []


def _enforce_contract(steps: List[str]) -> List[str]:
    if not steps:
        return [
            _REQUIRED_FIRST,
            _REQUIRED_SECOND,
            "Research agent: Synthesise and rank findings by relevance, recency, and authority; deduplicate.",
            "Writer agent: Draft a structured outline based on the ranked evidence.",
            "Editor agent: Review for coherence, coverage, and citation completeness.",
            _REQUIRED_FINAL,
        ]
    steps = [s for s in steps if isinstance(s, str)]
    if not steps or steps[0] != _REQUIRED_FIRST:
        steps = [_REQUIRED_FIRST] + steps
    if len(steps) < 2 or steps[1] != _REQUIRED_SECOND:
        steps = (
            [steps[0], _REQUIRED_SECOND]
            + [s for s in steps[1:] if "arXiv" not in s or "For each collected item" in s]
        )
    if _REQUIRED_FINAL not in steps:
        steps.append(_REQUIRED_FINAL)
    return steps[:7]


def planner_agent(topic: str) -> List[str]:
    """Use a Gemini LlmAgent to produce a step-by-step research plan.

    Returns a list of up to 7 step strings.
    """
    planner = LlmAgent(
        name="planner_agent",
        model=_DEFAULT_MODEL,
        instruction="""You are a planning agent that organises a multi-agent research workflow.

Available agents:
- Research agent: web search (Tavily), arXiv, Wikipedia.
- Writer agent: drafts Markdown reports from research findings.
- Editor agent: reviews and improves drafts.

Rules:
- Return ONLY a valid Python list of strings – no markdown, no explanations.
- Maximum 7 steps; each step is atomic and assigned to one agent.
- Do NOT include steps like "install packages" or "create CSV".
- The FIRST step MUST be exactly:
  "Research agent: Use Tavily to perform a broad web search and collect top relevant items (title, authors, year, venue/source, URL, DOI if available)."
- The SECOND step MUST be exactly:
  "Research agent: For each collected item, search on arXiv to find matching preprints/versions and record arXiv URLs (if they exist)."
- The FINAL step MUST instruct the Writer agent to produce a comprehensive Markdown report with inline citations and a References section with clickable links.
""",
    )

    prompt = f'Produce a research plan (Python list of strings) for the topic: "{topic}"'
    raw, _ = _run_agent(planner, prompt)
    steps = _coerce_to_list(raw)
    return _enforce_contract(steps)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def executor_agent_step(
    step_title: str, history: list, prompt: str
) -> Tuple[str, str, str]:
    """Execute one step of the plan.

    Returns:
        (step_title, agent_name, output_text)
    """
    # Build enriched context from history
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
        return step_title, "research_agent", content
    elif "draft" in step_lower or "write" in step_lower or "writer" in step_lower:
        content, _ = writer_agent(prompt=enriched_task)
        return step_title, "writer_agent", content
    elif any(kw in step_lower for kw in ("revise", "edit", "feedback", "editor")):
        content, _ = editor_agent(prompt=enriched_task)
        return step_title, "editor_agent", content
    else:
        raise ValueError(f"Cannot determine agent for step: {step_title!r}")
