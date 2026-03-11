"""
agent.py – ADK entry point for `adk web` and `adk run`.

The `adk web` command looks for a variable named `root_agent` in this module.
We expose the research_agent as the primary interactive agent.
"""

from google.adk.agents import LlmAgent
from src.agents import _make_research_agent, _make_writer_agent, _make_editor_agent

# `adk web` discovers `root_agent` automatically
root_agent = _make_research_agent()
