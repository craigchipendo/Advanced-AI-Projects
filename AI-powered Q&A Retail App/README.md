# AI-Powered Retail Q&A App (Vertex AI + Cloud SQL)

This repository contains a Jupyter notebook that implements an **AI-powered** question-answering application for a fictional retail company using Google Cloud Vertex AI, LangChain, and PostgreSQL on Cloud SQL. The app lets business users ask natural-language questions about retail data and receive grounded answers backed by a vector-enabled SQL database.

## Project Overview

- Uses Vertex AI embeddings and generative models to answer questions over retail transactions and product data stored in PostgreSQL.  
- Leverages the `pgvector` extension so that text fields can be converted into vectors and searched via semantic similarity. 
- Orchestrates the end-to-end flow (embed → retrieve → generate) with LangChain and `langchain_google_vertexai`.

## Architecture

- **Data layer**:  
  - Cloud SQL for PostgreSQL instance (e.g., `retail-ins`) hosting a `retail` database and tables with vector columns backed by `pgvector`. 
  - Sample retail data loaded into tables for products, transactions, and related entities (as defined in the notebook cells).

- **Model layer**:  
  - Vertex AI `TextEmbeddingModel` (via LangChain `VertexAIEmbeddings`) to embed documents and user queries.
  - Vertex AI `GenerativeModel` to produce final natural-language answers grounded in retrieved rows.

- **Orchestration**:  
  - LangChain chains that embed the user query, perform similarity search in PostgreSQL, and pass retrieved context to the LLM for answer synthesis.  
  - Notebook-based UI using `display` and `Markdown` for readable prompts, intermediate outputs, and final answers.

## Prerequisites

You need the following before running `AI-powered-app.ipynb`:

- A Google Cloud project with:
  - Vertex AI API enabled.  
  - Cloud SQL Admin and SQL APIs enabled.
- A Cloud SQL for PostgreSQL instance (e.g., `retail-ins`) with:
  - A database named `retail`.  
  - A user (e.g., `retail-admin`) and password with permission to create extensions and tables.
- `pgvector` extension installed/enabled on the PostgreSQL instance.
- Local or environment-based authentication:
  - For local: `gcloud auth application-default login`.  
  - For managed environments: a service account with appropriate Vertex AI and Cloud SQL permissions.

### Python Environment

The notebook installs and pins key dependencies inside itself, including:

- `cloud-sql-python-connector[asyncpg]==1.2.3`  
- `asyncpg==0.27.0`  
- `pgvector==0.1.8`  
- `numpy==1.26.4` and `pandas`  
- `langchain`, `langchain_google_vertexai`, `langchain-community`  
- `transformers`, `bottleneck`, `numexpr`, `validators` and related support libraries.

The first cells handle package installation and may restart the kernel automatically after installation.

## Configuration

Key configuration values are defined near the top of the notebook:

```python
project_id = "*****-gcp-02-c72a978ae543"
database_password = "*********"
region = "us-central1"
instance_name = "retail-ins"
database_name = "retail"
database_user = "retail-admin"

vertexai.init(project=project_id, location=region)

