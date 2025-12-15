# Netflix AI Recommender & Executive Analytics Platform

## 1. Project Overview

This project is an end‑to‑end data platform that simulates a Netflix‑style streaming company using a large, production‑like synthetic dataset. It spans operational OLTP databases, NoSQL systems, a Hive‑based big‑data warehouse, and a new AI‑driven business application for both end users and executives.[file:5] The goal is to demonstrate how modern data engineering, generative AI, and BI can work together to power personalized recommendations, operational monitoring, and strategic decision‑making in a single cohesive stack.[file:3][file:5]

The existing ecosystem is modeled as a normalized MySQL OLTP schema for users, subscriptions, roles, titles, episodes, viewing activity, and content reviews, ensuring data integrity for core workflows such as registration, authentication, catalog management, and billing.[image:1][file:5] For large‑scale analytics, Apache Hive on Amazon EMR reads synthetic watch‑event and review data from S3 into a Parquet star schema, enabling high‑volume, read‑intensive queries on engagement, ratings, and regional trends without impacting transactional systems.[file:5]

On top of this foundation, the **Netflix AI Recommender & Executive Analytics System** introduces a novel AI‑powered application: end users get semantic‑search recommendations and dynamically generated posters, while executives access interactive dashboards and behavioral telemetry not present in the baseline platform.[file:3] The application integrates MySQL (auth and warehouse), MongoDB (clickstream logs), and ChromaDB (vector search) via a FastAPI backend and Gradio front end, providing a realistic demonstration of how a streaming company could evolve its data architecture and product capabilities.[file:3][file:5]

---

## 2. Existing Data Systems

### 2.1 OLTP RDBMS Design

For daily operations, the project uses a normalized MySQL database (e.g., `netflix_oltp`) to support mission‑critical transactions.[image:1][file:5]

- **User Management:**  
  `Users`, `Roles`, `UserRoles`, `Subscriptions`, and `SubscriptionPlans` manage identities, access control, and pricing tiers.[image:1]
- **Content Catalog:**  
  `Titles` and `Episodes` store metadata such as type, genre, MPAA rating, release year, runtime, and air date.[image:1]
- **Engagement & Feedback:**  
  `ViewingActivity` captures per‑session start time, duration, device type, and the linked title/episode, while `ContentReviews` records structured ratings and free‑form comments.[image:1][file:5]

The schema is designed in Third Normal Form (3NF) to minimize redundancy and safely support frequent updates to catalog and subscription plans without corrupting historical viewing or billing records.[image:1][file:5]

### 2.2 NoSQL & Big‑Data Warehouse (Hive + S3)

To support scalable analytics, a Hive‑based NoSQL data warehouse is deployed on Amazon EMR.[file:5]

- **Raw Data Layer (S3):**  
  Synthetic CSVs for titles, episodes, watch events, and reviews are stored in S3 under dedicated prefixes, forming a schema‑on‑read staging layer.[file:5]
- **Hive External & Star Schema Tables:**  
  Hive external tables ingest these files, and ETL transforms them into Parquet star schemas with dimensions (`dimtitles`, `dimepisodes`) and large facts (`factwatchevents`, `factcontentreviews`) partitioned by event date or review year for efficient scanning and partition pruning.[file:5]
- **Workloads:**  
  The warehouse supports queries such as top‑watched titles, country‑level average viewing duration, movie vs. TV show rating comparisons, and Daily Active Users (DAU), all executed over more than a million synthetic watch‑event rows.[file:5]

In addition, a MongoDB database (`secure_app_logs`) is used as a NoSQL store for semi‑structured clickstream and audit logs, capturing each login, button click, and navigation path in an immutable, append‑only fashion.[file:3]

### 2.3 Implementation Challenges

Key implementation challenges and solutions include:[file:5]

- **S3 Path & Table Location Management:**  
  Directly mapping tables to arbitrary paths proved fragile, so consistent S3 prefixes (for titles, episodes, watch events, reviews) were introduced for predictable ingestion.[file:5]
- **Dynamic Partition Limits in Hive:**  
  Default limits on dynamic partitions and created files caused ETL failures when loading many distinct dates; tuning settings such as `hive.exec.max.dynamic.partitions` resolved this.[file:5]
- **Date Parsing & Data Variety:**  
  Source files used heterogeneous date formats (natural‑language dates, timestamps, and ISO strings). Standardization via `UNIX_TIMESTAMP` and `TO_DATE` ensured reliable date keys in the warehouse.[file:5]
- **Performance at Scale:**  
  Converting fact tables to Parquet and leveraging partition pruning significantly reduced query times and resource usage, making the warehouse suitable for interactive dashboards.[file:5]

---

## 3. New Business Application

### 3.1 Concept & Differentiation

The **Netflix AI Recommender & Executive Analytics System** is a new business application that goes beyond the company’s baseline streaming and batch reporting capabilities.[file:3]

- **For Users:**  
  An AI‑powered “Ask Netflix” interface lets subscribers describe what they want to watch in natural language (e.g., “a funny time‑travel movie”), returning semantically relevant titles with AI‑generated posters when artwork is missing or needs enhancement.[file:3]
- **For Executives:**  
  A dedicated analytics portal provides interactive views of catalog performance, engagement, and audience behavior, including hidden gems (high rating, low views), vintage content consumption, demographic review patterns, and geographic genre preferences.[file:3][file:5]

This dual‑facing design differs from existing offerings by tightly coupling generative AI, semantic search, and BI dashboards in one integrated product.

### 3.2 Dataset & Database Design

To enable this, the application integrates three main data stores, populated primarily from synthetic data extracted and transformed from the OLTP model and Hive warehouse:[image:1][file:5]

1. **MySQL (Authentication & Analytics):**  
   - `secure_app_db` manages `users/admins` tables with SHA‑256‑hashed credentials and role assignments.[file:3]  
   - `dw_netflix_analytics` hosts a star‑schema warehouse (`FactUserContentMetrics`, `DimUser`, `DimTitle`, `DimDate`) used directly by the executive dashboard.[file:3]

2. **MongoDB (`secure_app_logs`):**  
   - Stores semi‑structured logs of every click, login attempt, and navigation event, forming a rich behavioral dataset for UX analysis, anomaly detection, and future model training.[file:3]

3. **ChromaDB (Vector Store):**  
   - Indexes title embeddings generated with HuggingFace’s `all-MiniLM-L6-v2` model, enabling semantic similarity search over plot descriptions and genres so that natural‑language queries map to the most relevant titles with low latency.[file:3]

This multi‑store design contrasts sharply with the legacy environment, which relied almost entirely on relational schemas and did not provide a unified vector index or robust clickstream logging for online AI experiences.[file:3][file:5]

### 3.3 Front‑End & Service Architecture

The user experience is delivered through a FastAPI + Gradio stack:[file:3]

- **Backend:**  
  FastAPI orchestrates requests, handles authentication, and mediates interactions with MySQL, MongoDB, and ChromaDB, while Uvicorn serves the ASGI application.[file:3]
- **Frontend:**  
  Gradio Blocks and custom HTML/CSS provide multi‑page flows for user login, admin login, AI search, and analytics dashboards, all mounted on distinct routes (e.g., `/`, `/login/user/`, `/portal/admin/`, `/ai/`, `/analytics/`).[file:3]
- **Security & Configuration:**  
  Passwords are hashed using SHA‑256, databases are auto‑created when possible, and configuration for MySQL credentials, HuggingFace tokens, and Ngrok tokens is centralized in `netflix_app.py`.[file:3]

---

## 4. Original README (Preserved)

> **Note:** The following section is the original application README, preserved verbatim and augmented by the sections above for full project context.[file:4]

Netflix AI Recommender & Executive Analytics System  

📋 Overview  

This application is a robust, full-stack prototype that simulates a Netflix-like environment. It combines Generative AI for user engagement (movie recommendations and dynamic poster generation) with Business Intelligence for administration (SQL-based analytics dashboards).  

The system features role-based authentication (User vs. Admin), a multi-page navigation architecture using FastAPI and Gradio, and dual-database logging.  

🌟 Key Features  

1. 🔐 Role-Based Authentication  

User & Admin Portals: Distinct login flows for general users and system administrators.  

Secure Storage: Passwords are hashed using SHA-256 before storage in MySQL.  

Registration: New users can sign up, with data stored in a structured Relational Database.  

2. 🤖 AI-Powered Recommender (User Feature)  

Semantic Search: Uses ChromaDB and HuggingFace Embeddings (all-MiniLM-L6-v2) to allow natural language queries (e.g., "A scary movie about space aliens").  

Generative UI: If a movie poster is missing or for visual flair, the app uses Stable Diffusion XL (via HuggingFace Inference API) to generate a cinematic poster on the fly based on the movie's description.  

3. 📊 Executive Analytics Dashboard (Admin Feature)  

Data Warehouse Integration: Connects to a dw_netflix_analytics SQL database.  

Visualizations: Interactive charts using Plotly and Seaborn:  

Hidden Gems: Scatter plot correlating low view counts with high ratings.  

Vintage Analysis: Content consumption by release decade.  

Audience Demographics: Review contributions by age group.  

Geographic Trends: Top genres per country.  

4. 📝 Universal Logging  

MongoDB Integration: Every click, login attempt, and page navigation is logged to a NoSQL database (secure_app_logs) for audit trails.  

🛠️ Tech Stack  

Frontend: Gradio (Blocks, HTML/CSS styling)  

Backend: FastAPI, Uvicorn  

Databases: * MySQL (Auth & Analytics)  

MongoDB (Logs)  

ChromaDB (Vector Embeddings)  

AI/ML: LangChain, HuggingFace Inference Client, Stable Diffusion  

Tunneling: PyNgrok (for public URL generation)  

⚙️ Prerequisites & Installation  

1. System Requirements  

Python 3.8+  

MySQL Server (Running locally on port 3306)  

MongoDB Server (Running locally on port 27017)  

2. Install Python Dependencies  

Create a requirements.txt file or run the following command:  

`pip install gradio pandas matplotlib seaborn plotly pymysql sqlalchemy cryptography pymongo huggingface_hub langchain langchain_community chromadb fastapi uvicorn pyngrok`  

3. Database Setup  

The application expects two MySQL databases and one MongoDB instance.  

A. Authentication DB (Auto-Created)  

The script explicitly checks for and creates secure_app_db and the users/admins tables on startup. No manual work is needed here other than ensuring your MySQL credentials are correct.  

B. Analytics DB (Manual Setup Required)  

The Admin Dashboard expects a database named dw_netflix_analytics.  

You must import your Netflix data warehouse schema (tables: FactUserContentMetrics, DimTitle, DimUser, DimDate) into your local MySQL server for the charts to populate.  

4. Configuration  

Open netflix_app.py and update the following configuration blocks to match your local environment:  

MySQL Credentials (Line 36 & 252):  

