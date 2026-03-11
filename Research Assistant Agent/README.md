# Research Agent Project

## Overview
This repository contains a containerized research assistant built with Python and the Google Agent Development Kit (ADK). The system orchestrates large language model (LLM) agents to automate literature review, evidence synthesis, and technical writing for data science and machine learning workflows.

---

## Architecture

```mermaid
graph TD
    %% Layer 1: Client
    subgraph Layer_1 [① Client Layer]
        UI[Browser UI: Jinja2/JS]
        Static[Static Assets: Logos/CSS]
    end
    %% Layer 2: API
    subgraph Layer_2 [② API & Server Layer]
        FastAPI[FastAPI App: main.py]
        TaskStore[(In-memory Task Store)]
        DB[(Database: SQLite/Postgres)]
        BG_Thread[Background Thread: run_agent_workflow]
    end
    %% Layer 3: Orchestration
    subgraph Layer_3 [③ Orchestration Layer]
        Planner[Planner Agent: Gemini 2.0 Flash]
        Router[Executor Router: Keyword Routing]
    end
    %% Layer 4: Agents
    subgraph Layer_4 [④ Specialist Agents - Google ADK]
        Researcher[Research Agent]
        Writer[Writer Agent]
        Editor[Editor Agent]
        ADK_Runtime[ADK InMemoryRunner]
    end
    %% Layer 5: Tools
    subgraph Layer_5 [⑤ Research Tools]
        Tavily[Tavily Search API]
        arXiv[arXiv Atom API/PDF Scraper]
        Wiki[Wikipedia API]
        HTTP_Client[Shared HTTP Session w/ Retries]
    end
    %% Layer 6: Infra
    subgraph Layer_6 [⑥ Infrastructure & Config]
        Gemini[Gemini API / Vertex AI]
        Docker[Docker: Python 3.11-slim]
        Env[Environment: .env / Secrets]
    end
    %% Relationships
    UI -->|POST /generate_report| FastAPI
    UI -->|GET /task_progress| TaskStore
    FastAPI --> BG_Thread
    FastAPI --> DB
    BG_Thread --> Planner
    Planner -->|Returns JSON Plan| Router
    Router -->|Routes Step| Researcher
    Router -->|Routes Step| Writer
    Router -->|Routes Step| Editor
    Researcher --> Tavily
    Researcher --> arXiv
    Researcher --> Wiki
    Tavily & arXiv & Wiki --> HTTP_Client
    Researcher & Writer & Editor --> ADK_Runtime
    ADK_Runtime --> Gemini
    Gemini -.-> Env
    BG_Thread -.->|Updates Status| TaskStore
    BG_Thread -.->|Saves Final Report| DB
    %% Styling
    style Layer_1 fill:#0a192f,stroke:#3b82f6,color:#fff
    style Layer_2 fill:#0a192f,stroke:#10b981,color:#fff
    style Layer_3 fill:#0a192f,stroke:#f59e0b,color:#fff
    style Layer_4 fill:#0a192f,stroke:#8b5cf6,color:#fff
    style Layer_5 fill:#0a192f,stroke:#ec4899,color:#fff
    style Layer_6 fill:#0a192f,stroke:#94a3b8,color:#fff
```
---

## Repository Structure

```text
.
├─ .adk/              # Local configuration and metadata for Google ADK
├─ docker/            # Container orchestration and startup scripts
├─ src/               # Application source code (agents, tools, orchestration)
├─ .env               # Environment variables (API keys, model configuration)
├─ Dockerfile         # Container image definition
├─ main.py            # Application entry point (API or CLI runner)
├─ README.md          # Project documentation
└─ requirements       # Python dependency specification
```

`.adk/`
The `.adk` directory stores configuration and cache data used by the Google Agent Development Kit. It typically includes project metadata, tool registration, and local state required to manage multi‑agent LLM workflows.

`docker/`
The `docker` folder contains scripts and configuration for building and running the application in a containerized environment. This includes entrypoint logic for launching the API server and any supporting services required by the research agents.

`src/`
The `src` directory holds the core application logic, including:
* Agent definitions for research, drafting, and editing tasks.
* Planning and execution modules that coordinate multi‑step research pipelines.
* Tool integrations for web search and scholarly retrieval (for example, Tavily, arXiv, and Wikipedia adapters).
These components work together to support reproducible literature reviews, structured report generation, and automated refinement of technical writing in data science and machine learning contexts.

`.env`
The `.env` file defines environment variables such as LLM provider keys, search API keys, and model configuration. Typical variables include:
* LLM API keys (for example, Gemini).
* Web research API keys (for example, Tavily).
* Optional configuration flags for model selection and runtime behavior.
Using `.env` allows you to keep credentials out of source control while enabling flexible experimentation with different models and tools.

`Dockerfile`
The `Dockerfile` specifies how to build a reproducible container image for the project. It installs Python, project dependencies, and the application code, then configures the runtime command used to launch the research service.

`main.py`
`main.py` is the primary entry point for the application. It typically wires together:
* The planning agent that decomposes a research question into sequential tasks.
* The executor that routes each task to the appropriate LLM agent (research, writer, editor).
* The serving interface (for example, a FastAPI app or CLI) used to trigger end‑to‑end research runs.

`README.md`
This file provides documentation for developers and practitioners working with the research agent. It explains the project structure, the purpose of each core component, and how the system supports automated literature review and technical report generation for data science and machine learning use cases.

`requirements`
The `requirements` file lists the Python packages required to run the project. Typical dependencies include:
* A web framework and ASGI server (for example, FastAPI, Uvicorn).
* Google ADK and compatible LLM client libraries.
* HTTP and data‑processing libraries for integrating external research tools.
Installing these dependencies ensures that the research agents, planning logic, and orchestration components run consistently across environments.

---

