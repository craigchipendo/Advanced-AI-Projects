import pymysql
import pandas as pd
import re
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
import warnings

# This tells Python to ignore all warnings
warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "msba@2025&SQL",
    "database": "netflix_oltp",
    "autocommit": True,
    "cursorclass": pymysql.cursors.Cursor
}

VECTOR_DB_PATH = "./chroma_db_netflix_production" # Where the brain lives

def get_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print("✅ Connected to MySQL")
        return conn
    except pymysql.MySQLError as e:
        print(f"❌ Connection Failed: {e}")
        return None

def run_etl():
    print("🚀 Starting ETL Pipeline...")
    
    # 1. EXTRACT (Complex SQL Join)
    conn = get_connection()
    if not conn: return

    try:
        cursor = conn.cursor()
        print("   - Executing Multi-Table Join...")
        
        sql_query = """
        SELECT 
            t.TitleID,
            t.Title,
            t.Type,
            t.ReleaseYear,
            t.MpaaRating,
            t.Description,
            -- Metrics for popularity context
            COALESCE(AVG(r.Rating), 0) AS AvgUserRating,
            COUNT(DISTINCT v.ActivityID) AS TotalViews,
            COUNT(DISTINCT e.EpisodeID) AS EpisodeCount,
            -- Context: Top 5 User Comments
            SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT r.Comment SEPARATOR '; '), '; ', 5) AS TopReviews
        FROM Titles t
        LEFT JOIN ContentReviews r ON t.TitleID = r.TitleID
        LEFT JOIN ViewingActivity v ON t.TitleID = v.TitleID
        LEFT JOIN Episodes e ON t.TitleID = e.TitleID
        GROUP BY 
            t.TitleID, t.Title, t.Type, t.ReleaseYear, t.MpaaRating, t.Description
        """
        
        cursor.execute(sql_query)
        column_names = [desc[0].lower() for desc in cursor.description]
        df = pd.DataFrame(cursor.fetchall(), columns=column_names)
        print(f"   - Extracted {len(df)} records from MySQL.")
        
    except Exception as e:
        print(f"❌ ETL Failed: {e}")
        return
    finally:
        conn.close()

    # 2. TRANSFORM (Data Engineering)
    print("   - Transforming Data & Engineering Features...")
    
    # Cleaning
    df['description'] = df['description'].fillna('No description available.')
    df['title'] = df['title'].fillna('Unknown')
    df['topreviews'] = df['topreviews'].fillna('')
    df['mpaarating'] = df['mpaarating'].fillna('Unrated')
    df['releaseyear'] = df['releaseyear'].fillna(0).astype(int)
    df['avguserrating'] = df['avguserrating'].astype(float).round(1)
    df['totalviews'] = df['totalviews'].astype(int)
    
    # Logic: Create the "Rich Content" Text
    def create_rich_content(row):
        content = f"Title: {row['title']}. Type: {row['type']}. "
        content += f"Year: {row['releaseyear']}. Rating: {row['mpaarating']}. "
        content += f"Plot: {row['description']} "
        
        # Inject Popularity Context
        if row['totalviews'] > 100: content += "Status: Very Popular/Trending. "
        elif row['totalviews'] < 5: content += "Status: Hidden Gem/Niche. "
            
        # Inject Sentiment Context
        if row['topreviews']: content += f"Audience Opinions: {row['topreviews']}"
        
        return content

    documents = []
    for _, row in df.iterrows():
        doc = Document(
            page_content=create_rich_content(row),
            metadata={
                "title_id": row['titleid'],
                "title": row['title'],
                "year": int(row['releaseyear']),
                "type": row['type'],
                "rating": float(row['avguserrating']),
                "views": int(row['totalviews'])
            }
        )
        documents.append(doc)

    # 3. LOAD (Save to Chroma)
    print(f"   - Loading into Vector Database at '{VECTOR_DB_PATH}'...")
    
    # Using a free, high-quality local model
    embedding_fn = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # This creates (or overwrites) the DB on disk
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        collection_name="netflix_production",
        persist_directory=VECTOR_DB_PATH
    )
    
    print("✅ ETL Complete! Database is ready for the App.")

if __name__ == "__main__":
    run_etl()