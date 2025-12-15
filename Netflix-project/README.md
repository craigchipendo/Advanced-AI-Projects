# Netflix AI Recommender & Executive Analytics Platform

## 1. Project Overview

This project is an end‑to‑end data platform that simulates a Netflix‑style streaming company using a large, production‑like synthetic dataset. It spans operational OLTP databases, NoSQL systems, a Hive‑based big‑data warehouse, and a new AI‑driven business application for both end users and executives. The goal is to demonstrate how modern data engineering, generative AI, and BI can work together to power personalized recommendations, operational monitoring, and strategic decision‑making in a single cohesive stack.

The existing ecosystem is modeled as a normalized MySQL OLTP schema for users, subscriptions, roles, titles, episodes, viewing activity, and content reviews, ensuring data integrity for core workflows such as registration, authentication, catalog management, and billing. For large‑scale analytics, Apache Hive on Amazon EMR reads synthetic watch‑event and review data from S3 into a Parquet star schema, enabling high‑volume, read‑intensive queries on engagement, ratings, and regional trends without impacting transactional systems.

On top of this foundation, the **Netflix AI Recommender & Executive Analytics System** introduces a novel AI‑powered application: end users get semantic‑search recommendations and dynamically generated posters, while executives access interactive dashboards and behavioral telemetry not present in the baseline platform. The application integrates MySQL (auth and warehouse), MongoDB (clickstream logs), and ChromaDB (vector search) via a FastAPI backend and Gradio front end, providing a realistic demonstration of how a streaming company could evolve its data architecture and product capabilities.

---

## 2. Existing Data Systems

### 2.1 OLTP RDBMS Design

For daily operations, the project uses a normalized MySQL database (e.g., `netflix_oltp`) to support mission‑critical transactions.

- **User Management:**  
  `Users`, `Roles`, `UserRoles`, `Subscriptions`, and `SubscriptionPlans` manage identities, access control, and pricing tiers.
- **Content Catalog:**  
  `Titles` and `Episodes` store metadata such as type, genre, MPAA rating, release year, runtime, and air date.
- **Engagement & Feedback:**  
  `ViewingActivity` captures per‑session start time, duration, device type, and the linked title/episode, while `ContentReviews` records structured ratings and free‑form comments.

The schema is designed in Third Normal Form (3NF) to minimize redundancy and safely support frequent updates to catalog and subscription plans without corrupting historical viewing or billing records.
![OLTP ER Diagram for existing system] (OLTP ER Diagram.png)


### 2.2 NoSQL & Big‑Data Warehouse (Hive + S3)

To support scalable analytics, a Hive‑based NoSQL data warehouse is deployed on Amazon EMR.

- **Raw Data Layer (S3):**  
  Synthetic CSVs for titles, episodes, watch events, and reviews are stored in S3 under dedicated prefixes, forming a schema‑on‑read staging layer.
- **Hive External & Star Schema Tables:**  
  Hive external tables ingest these files, and ETL transforms them into Parquet star schemas with dimensions (`dimtitles`, `dimepisodes`) and large facts (`factwatchevents`, `factcontentreviews`) partitioned by event date or review year for efficient scanning and partition pruning.
- **Workloads:**  
  The warehouse supports queries such as top‑watched titles, country‑level average viewing duration, movie vs. TV show rating comparisons, and Daily Active Users (DAU), all executed over more than a million synthetic watch‑event rows.

In addition, a MongoDB database (`secure_app_logs`) is used as a NoSQL store for semi‑structured clickstream and audit logs, capturing each login, button click, and navigation path in an immutable, append‑only fashion.

### 2.3 Implementation Challenges

Key implementation challenges and solutions include:

- **S3 Path & Table Location Management:**  
  Directly mapping tables to arbitrary paths proved fragile, so consistent S3 prefixes (for titles, episodes, watch events, reviews) were introduced for predictable ingestion.
- **Dynamic Partition Limits in Hive:**  
  Default limits on dynamic partitions and created files caused ETL failures when loading many distinct dates; tuning settings such as `hive.exec.max.dynamic.partitions` resolved this.
- **Date Parsing & Data Variety:**  
  Source files used heterogeneous date formats (natural‑language dates, timestamps, and ISO strings). Standardization via `UNIX_TIMESTAMP` and `TO_DATE` ensured reliable date keys in the warehouse.
- **Performance at Scale:**  
  Converting fact tables to Parquet and leveraging partition pruning significantly reduced query times and resource usage, making the warehouse suitable for interactive dashboards.

---

## 3. New Business Application

### 3.1 Concept & Differentiation

The **Netflix AI Recommender & Executive Analytics System** is a new business application that goes beyond the company’s baseline streaming and batch reporting capabilities.

- **For Users:**  
  An AI‑powered “Ask Netflix” interface lets subscribers describe what they want to watch in natural language (e.g., “a funny time‑travel movie”), returning semantically relevant titles with AI‑generated posters when artwork is missing or needs enhancement.
- **For Executives:**  
  A dedicated analytics portal provides interactive views of catalog performance, engagement, and audience behavior, including hidden gems (high rating, low views), vintage content consumption, demographic review patterns, and geographic genre preferences.

This dual‑facing design differs from existing offerings by tightly coupling generative AI, semantic search, and BI dashboards in one integrated product.

### 3.2 Dataset & Database Design

To enable this, the application integrates three main data stores, populated primarily from synthetic data extracted and transformed from the OLTP model and Hive warehouse:

1. **MySQL (Authentication & Analytics):**  
   - `secure_app_db` manages `users/admins` tables with SHA‑256‑hashed credentials and role assignments. 
   - `dw_netflix_analytics` hosts a star‑schema warehouse (`FactUserContentMetrics`, `DimUser`, `DimTitle`, `DimDate`) used directly by the executive dashboard.[file:3]

2. **MongoDB (`secure_app_logs`):**  
   - Stores semi‑structured logs of every click, login attempt, and navigation event, forming a rich behavioral dataset for UX analysis, anomaly detection, and future model training.

3. **ChromaDB (Vector Store):**  
   - Indexes title embeddings generated with HuggingFace’s `all-MiniLM-L6-v2` model, enabling semantic similarity search over plot descriptions and genres so that natural‑language queries map to the most relevant titles with low latency.

This multi‑store design contrasts sharply with the legacy environment, which relied almost entirely on relational schemas and did not provide a unified vector index or robust clickstream logging for online AI experiences.

### 3.3 Front‑End & Service Architecture

The user experience is delivered through a FastAPI + Gradio stack:

- **Backend:**  
  FastAPI orchestrates requests, handles authentication, and mediates interactions with MySQL, MongoDB, and ChromaDB, while Uvicorn serves the ASGI application.
- **Frontend:**  
  Gradio Blocks and custom HTML/CSS provide multi‑page flows for user login, admin login, AI search, and analytics dashboards, all mounted on distinct routes (e.g., `/`, `/login/user/`, `/portal/admin/`, `/ai/`, `/analytics/`).
- **Security & Configuration:**  
  Passwords are hashed using SHA‑256, databases are auto‑created when possible, and configuration for MySQL credentials, HuggingFace tokens, and Ngrok tokens is centralized in `netflix_app.py`.

### 3.5 🛠️ Tech Stack  

- Frontend: Gradio (Blocks, HTML/CSS styling)  

- Backend: FastAPI, Uvicorn  

- Databases: * MySQL (Auth & Analytics)  

- MongoDB (Logs)  

- ChromaDB (Vector Embeddings)  

- AI/ML: LangChain, HuggingFace Inference Client, Stable Diffusion  

- Tunneling: PyNgrok (for public URL generation)  

### 3.6 ⚙️ Prerequisites & Installation  

**1. System Requirements**  

- Python 3.8+  

- MySQL Server (Running locally on port 3306)  

- MongoDB Server (Running locally on port 27017)  

**2. Install Python Dependencies**  

Create a requirements.txt file or run the following command:  

`pip install gradio pandas matplotlib seaborn plotly pymysql sqlalchemy cryptography pymongo huggingface_hub langchain langchain_community chromadb fastapi uvicorn pyngrok`  

**3. Database Setup**  

The application expects two MySQL databases and one MongoDB instance.  

**A. Authentication DB (Auto-Created)**  

The script explicitly checks for and creates secure_app_db and the users/admins tables on startup. No manual work is needed here other than ensuring your MySQL credentials are correct.  

**B. Analytics DB (Manual Setup Required)**  

The Admin Dashboard expects a database named dw_netflix_analytics.  

You must import your Netflix data warehouse schema (tables: FactUserContentMetrics, DimTitle, DimUser, DimDate) into your local MySQL server for the charts to populate.  

**4. Configuration**  

Open netflix_app.py and update the following configuration blocks to match your local environment:  

---






