import gradio as gr
import time
import warnings
import base64
import io
import pandas as pd
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import seaborn as sns
import concurrent.futures
import plotly.express as px
import plotly.graph_objects as go
import pymysql
import hashlib
import datetime
from pymongo import MongoClient
from huggingface_hub import InferenceClient
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from fastapi import FastAPI
import uvicorn

# --- GLOBAL SETUP & SAFETY ---
warnings.filterwarnings("ignore")

# ==========================================
# 1. LOGGING & AUTHENTICATION INFRASTRUCTURE
# ==========================================

# --- MySQL Config for User/Admin Auth ---
AUTH_SQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "msba@2025&SQL", 
    "port": 3306,
    "database": "secure_app_db" 
}

# --- MongoDB Config for Universal Logs ---
mongo_client = None
logs_collection = None

try:
    mongo_client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    mongo_client.server_info() 
    mongo_db = mongo_client["secure_app_logs"]
    logs_collection = mongo_db["activity_logs"]
    print("✅ [System] MongoDB Connected (Universal Logging Enabled).")
except Exception as e:
    print(f"❌ [System] MongoDB Connection Failed: {e}")

# --- UNIVERSAL LOGGER FUNCTION ---
def log_interaction(action, details="N/A", username="Session_User"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📝 [LOG] {timestamp} | {username} | {action} | {details}")
    
    if logs_collection is not None:
        try:
            entry = {
                "timestamp": timestamp,
                "username": username,
                "action": action,
                "details": str(details)
            }
            logs_collection.insert_one(entry)
        except Exception as e:
            print(f"⚠️ Log Write Error: {e}")
    return 

# --- SQL Helper Functions ---
def get_auth_conn():
    return pymysql.connect(
        host=AUTH_SQL_CONFIG["host"],
        user=AUTH_SQL_CONFIG["user"],
        password=AUTH_SQL_CONFIG["password"],
        port=AUTH_SQL_CONFIG["port"],
        cursorclass=pymysql.cursors.DictCursor
    )

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_auth_db():
    conn = pymysql.connect(
        host=AUTH_SQL_CONFIG["host"],
        user=AUTH_SQL_CONFIG["user"],
        password=AUTH_SQL_CONFIG["password"],
        port=AUTH_SQL_CONFIG["port"]
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {AUTH_SQL_CONFIG['database']}")
    conn.select_db(AUTH_SQL_CONFIG['database'])
    
    # 1. USERS TABLE
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        username VARCHAR(255) PRIMARY KEY, 
                        password_hash VARCHAR(255),
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        age INT,
                        country VARCHAR(100),
                        phone VARCHAR(50),
                        is_subscriber BOOLEAN
                      )''')
    
    # 2. ADMINS TABLE
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
                        username VARCHAR(255) PRIMARY KEY, 
                        password_hash VARCHAR(255)
                      )''')
    
    # 3. Create Default Admin
    default_admin_pass = hash_password("admin123")
    cursor.execute(f"INSERT IGNORE INTO admins (username, password_hash) VALUES ('admin', '{default_admin_pass}')")

    conn.commit()
    conn.close()
    print("✅ [System] MySQL Tables Initialized (Users & Admins).")

# --- Auth Logic ---
def register_user(username, password, f_name, l_name, age, country, phone, is_sub):
    log_interaction("CLICK_REGISTER", f"Attempting to register: {username}")
    if not (username and password):
        return "⚠️ Missing Username or Password.", gr.update()
    conn = None
    try:
        conn = get_auth_conn()
        conn.select_db(AUTH_SQL_CONFIG['database'])
        cursor = conn.cursor()
        sql = """INSERT INTO users (username, password_hash, first_name, last_name, age, country, phone, is_subscriber) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (username, hash_password(password), f_name, l_name, int(age) if age else 0, country, phone, is_sub))
        conn.commit()
        log_interaction("REGISTER_SUCCESS", f"User Created: {username}", username)
        return f"✅ Account created for {username}! Please Log In.", gr.Tabs(selected="login_tab")
    except pymysql.IntegrityError:
        return "❌ Username already exists.", gr.update()
    except Exception as e:
        return f"❌ Error: {str(e)}", gr.update()
    finally:
        if conn: conn.close()

def login_user(username, password):
    log_interaction("CLICK_USER_LOGIN", f"Attempt: {username}")
    conn = None
    try:
        conn = get_auth_conn()
        conn.select_db(AUTH_SQL_CONFIG['database'])
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
        data = cursor.fetchone()
        if data and data['password_hash'] == hash_password(password):
            log_interaction("LOGIN_SUCCESS", "User Role", username)
            return (f"Welcome User, {username}!", gr.update(visible=False), gr.update(visible=True)) 
        else:
            log_interaction("LOGIN_FAIL", "Invalid User Creds", username)
            return "❌ Invalid credentials.", gr.update(), gr.update()
    except Exception as e:
        return f"❌ Error: {str(e)}", gr.update(), gr.update()
    finally:
        if conn: conn.close()

def login_admin(username, password):
    log_interaction("CLICK_ADMIN_LOGIN", f"Attempt: {username}")
    conn = None
    try:
        conn = get_auth_conn()
        conn.select_db(AUTH_SQL_CONFIG['database'])
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admins WHERE username=%s", (username,))
        data = cursor.fetchone()
        if data and data['password_hash'] == hash_password(password):
            log_interaction("ADMIN_LOGIN_SUCCESS", "Admin Role", username)
            return (f"Welcome Admin, {username}!", gr.update(visible=False), gr.update(visible=True)) 
        else:
            log_interaction("ADMIN_LOGIN_FAIL", "Invalid Admin Creds", username)
            return "❌ Invalid Admin credentials.", gr.update(), gr.update()
    except Exception as e:
        return f"❌ Error: {str(e)}", gr.update(), gr.update()
    finally:
        if conn: conn.close()

# Init DB
try:
    init_auth_db()
except Exception as e:
    print(f"❌ DB Init Error: {e}")

# ==========================================
# 2. NAVIGATION CONFIG
# ==========================================
LANDING_URL = "/"
LOGIN_USER_URL = "/login/user/"
LOGIN_ADMIN_URL = "/login/admin/"
PORTAL_USER_URL = "/portal/user/"
PORTAL_ADMIN_URL = "/portal/admin/"
AI_URL = "/ai/"
ANALYTICS_URL = "/analytics/"

# ==========================================
# 3. AI APP LOGIC
# ==========================================
VECTOR_DB_PATH = "./chroma_db_netflix_production"
HF_TOKEN = "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"

print("⏳ [AI App] Loading AI Model and Database...")
try:
    embedding_fn = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    image_client = InferenceClient(model="stabilityai/stable-diffusion-xl-base-1.0", token=HF_TOKEN)
    vector_db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding_fn, collection_name="netflix_production")
    print("✅ [AI App] System Ready!")
    ai_system_ready = True
except Exception as e:
    print(f"❌ [AI App] Error loading database: {e}")
    ai_system_ready = False

def generate_poster_b64(doc_data):
    title, description, genre = doc_data
    try:
        prompt = (f"A cinematic movie poster for a {genre} movie named '{title}'. "
                  f"Key visuals: {description[:100]}... "
                  "High quality, 8k, photorealistic, dramatic lighting, movie title text NOT required.")
        image = image_client.text_to_image(prompt)
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return "https://assets.nflxext.com/ffe/siteui/vlv3/f841d4c7-10e1-40af-bcae-07a3f8dc141a/f6d7434e-d6de-4185-a6d4-c77a2d08737b/US-en-20220502-popsignuptwoweeks-perspective_alpha_website_medium.jpg"

def search_logic(user_query):
    if not user_query:
        return "<div style='text-align:center; color: #777;'>Please enter a search query above.</div>"

    # --- Filter Logic ---
    filters = []
    if "movie" in user_query.lower(): filters.append({"type": {"$eq": "Movie"}})
    elif "show" in user_query.lower(): filters.append({"type": {"$eq": "TV Show"}})
    if "popular" in user_query.lower(): filters.append({"views": {"$gte": 20}}) 
    if "good" in user_query.lower(): filters.append({"rating": {"$gte": 4.0}})
    if "new" in user_query.lower(): filters.append({"year": {"$gte": 2023}})

    final_filter = {"$and": filters} if len(filters) > 1 else (filters[0] if filters else None)

    # --- Semantic Search (Top 3) ---
    try:
        # Get 3 results
        results = vector_db.similarity_search(user_query, k=3, filter=final_filter)
    except Exception as e:
        return f"<div style='color:red;'>Search Error: {str(e)}</div>"

    if not results:
        return "<div style='text-align:center; color: #ddd;'>No matches found.</div>"

    # --- PARALLEL IMAGE GENERATION ---
    # We prepare the data for the 3 results
    tasks = []
    for doc in results:
        title = doc.metadata.get('title', 'Unknown')
        type_ = doc.metadata.get('type', 'Unknown')
        tasks.append((title, doc.page_content, type_))
    
    # Run all 3 generations at the same time
    image_urls = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        image_urls = list(executor.map(generate_poster_b64, tasks))

    # --- HTML CONSTRUCTION ---
    # We use a Flexbox Row container to display them side-by-side
    html_output = "<div class='results-container'>"
    
    for i, doc in enumerate(results):
        title = doc.metadata.get('title', 'Unknown').upper()
        year = doc.metadata.get('year', 'N/A')
        rating = doc.metadata.get('rating', 'N/A')
        views = doc.metadata.get('views', 0)
        type_ = doc.metadata.get('type', 'Unknown')
        
        poster_url = image_urls[i]
        rating_color = "#46d369" if float(rating) >= 4.0 else "#ffa500"
        metadata_line = f"{year} • {type_} • <span style='color:{rating_color}'>★ {rating}</span>"

        html_output += f"""
        <div class="movie-card">
            <div class="poster-wrapper">
                <img src='{poster_url}' class='generated-poster'>
                <div class="overlay-badge">#{i+1} MATCH</div>
            </div>
            <div class="card-content">
                <h3 class="movie-title">{title}</h3>
                <p class="metadata-line">{metadata_line}</p>
                <div class="reason-text">{doc.page_content[:200]}...</div> 
            </div>
        </div>
        """
    
    html_output += "</div>"
    return html_output

# ==========================================
# 4. ANALYTICS APP LOGIC (FULL BACKEND RESTORED)
# ==========================================
print("⏳ [Analytics App] Connecting to SQL...")

# --- CONFIGURATION & CONSTANTS ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "msba@2025&SQL",
    "db": "dw_netflix_analytics"
}

# Netflix Branding Colors
NETFLIX_RED = '#E50914'
BG_BLACK = '#141414'
TEXT_WHITE = '#FFFFFF'
# A dark gray for secondary elements
SECONDARY_GRAY = '#2F2F2F' 

# --- DATABASE CONNECTION ---
analytics_ready = False
engine = None

try:
    encoded_pass = quote_plus(DB_CONFIG["password"])
    CONN_STR = f"mysql+pymysql://{DB_CONFIG['user']}:{encoded_pass}@{DB_CONFIG['host']}/{DB_CONFIG['db']}"
    engine = create_engine(CONN_STR)
    
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    
    print("✅ [Analytics App] Connected to SQL!")
    analytics_ready = True
except Exception as e:
    print(f"⚠️ [Analytics App] Connection failed: {e}. Analytics tabs may be empty.")
    engine = None

# --- DATA FETCHING FUNCTIONS ---

def safe_read_sql(query):
    """Wrapper to safely execute SQL and return a DataFrame."""
    if not analytics_ready or engine is None:
        return pd.DataFrame()
    return pd.read_sql(query, engine)

def get_hidden_gems_data():
    query = """
    SELECT dt.Genre, 
           SUM(f.TotalWatchMins) as TotalWatchTime, 
           AVG(f.AvgRating) as AvgRating
    FROM FactUserContentMetrics f
    JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
    GROUP BY dt.Genre
    HAVING COUNT(*) > 5;
    """
    return safe_read_sql(query)

def get_age_reviews_data():
    query = """
    SELECT du.AgeGroup, COUNT(DISTINCT f.TitleKey) as TotalReviews
    FROM FactUserContentMetrics f
    JOIN DimUser du ON f.UserKey = du.UserKey
    WHERE f.ReviewCount > 0 
    GROUP BY du.AgeGroup;
    """
    return safe_read_sql(query)

def get_vintage_data():
    query = """
    SELECT dt.ReleaseYear, SUM(f.TotalWatchMins) as TotalWatch
    FROM FactUserContentMetrics f
    JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
    WHERE dt.ReleaseYear IS NOT NULL
    GROUP BY dt.ReleaseYear;
    """
    return safe_read_sql(query)

def get_mpaa_data():
    query = """
    SELECT dt.MpaaRating, SUM(f.TotalWatchMins) as TotalWatch
    FROM FactUserContentMetrics f
    JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
    WHERE dt.MpaaRating IS NOT NULL AND dt.MpaaRating != ''
    GROUP BY dt.MpaaRating;
    """
    return safe_read_sql(query)

def get_geo_genre_data():
    query = """
    SELECT du.CountryCode, dt.Genre, ROUND(AVG(f.AvgRating),2) AS AvgRating, COUNT(*) as InteractionCount
    FROM FactUserContentMetrics f
    JOIN DimUser du ON f.UserKey = du.UserKey
    JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
    GROUP BY du.CountryCode, dt.Genre
    HAVING COUNT(*) > 10;
    """
    return safe_read_sql(query)

def get_monthly_trend_data():
    query = """
    SELECT dd.Year, dd.Month, dt.Genre, SUM(f.TotalWatchMins) as MonthlyWatch
    FROM FactUserContentMetrics f
    JOIN DimDate dd ON f.DateKey = dd.DateKey
    JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
    GROUP BY dd.Year, dd.Month, dt.Genre
    ORDER BY dd.Year, dd.Month;
    """
    return safe_read_sql(query)

# --- HELPER: COMMON PLOT STYLING ---
def apply_netflix_theme(fig):
    """Applies consistent dark theme to Plotly figures."""
    fig.update_layout(
        paper_bgcolor=BG_BLACK,
        plot_bgcolor=BG_BLACK,
        font=dict(color=TEXT_WHITE, family="Arial"),
        xaxis=dict(gridcolor=SECONDARY_GRAY, zerolinecolor=SECONDARY_GRAY),
        yaxis=dict(gridcolor=SECONDARY_GRAY, zerolinecolor=SECONDARY_GRAY),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig

# --- VISUALIZATION FUNCTIONS (PLOTLY) ---

def plot_hidden_gems():
    """Figure 1: Hidden Gems Analysis (Scatter)"""
    df_gems = get_hidden_gems_data()
    if df_gems.empty: return None

    # Create Scatter Plot
    fig = px.scatter(
        df_gems, 
        x="TotalWatchTime", 
        y="AvgRating",
        size="TotalWatchTime", # Bubble size based on popularity
        hover_name="Genre",
        hover_data={"TotalWatchTime": ":,.0f", "AvgRating": ":.2f"},
        title="'Hidden Gems' Analysis (Rating vs. Popularity)",
        color_discrete_sequence=[NETFLIX_RED]
    )

    # Manual Annotations (Mimicking the loop in original code)
    # We add text labels for interesting points (High Rating or High Popularity)
    high_watch_threshold = df_gems['TotalWatchTime'].quantile(0.85)
    
    for i, row in df_gems.iterrows():
        if row['AvgRating'] > 3.5 or row['TotalWatchTime'] > high_watch_threshold:
            fig.add_annotation(
                x=row['TotalWatchTime'],
                y=row['AvgRating'],
                text=row['Genre'],
                showarrow=True,
                arrowhead=1,
                yshift=10,
                font=dict(color="white", size=10)
            )

    fig.update_xaxes(title="Total Watch Time (Popularity)")
    fig.update_yaxes(title="Average Rating (Quality)")
    
    return apply_netflix_theme(fig)

def plot_age_contribution():
    """Figure 2: Total Review Contribution by Age Group (Bar)"""
    df_total_reviews = get_age_reviews_data()
    if df_total_reviews.empty: return None

    # Dynamic Ordering
    defined_order = ['Under 18', '18-25', '26-35', '36-50', '50+', 'Unknown']
    existing_groups = df_total_reviews['AgeGroup'].unique()
    final_order = [x for x in defined_order if x in existing_groups]

    fig = px.bar(
        df_total_reviews,
        x='AgeGroup',
        y='TotalReviews',
        category_orders={'AgeGroup': final_order},
        text='TotalReviews',
        title="Community Voice across Age Groups",
        color_discrete_sequence=[NETFLIX_RED]
    )

    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_yaxes(title="Total Reviews Contributed")
    
    return apply_netflix_theme(fig)

def plot_content_vintage():
    """Figure 3: Content Vintage Analysis (Bar - Million Hours)"""
    df_vintage = get_vintage_data()
    if df_vintage.empty: return None

    # Bin Years into Decades
    def get_decade(year):
        if year < 1990: return 'Pre-1990'
        if 1990 <= year < 2000: return '1990s'
        if 2000 <= year < 2010: return '2000s'
        if 2010 <= year < 2020: return '2010s'
        if year >= 2020: return '2020s'
        return 'Unknown'

    df_vintage['Decade'] = df_vintage['ReleaseYear'].apply(get_decade)
    df_decade_agg = df_vintage.groupby('Decade', as_index=False)['TotalWatch'].sum()
    
    # Convert Units: Million Hours
    df_decade_agg['TotalWatchMilHours'] = df_decade_agg['TotalWatch'] / 60 / 1000000

    # Sort Chronologically
    decade_order = ['Pre-1990', '1990s', '2000s', '2010s', '2020s']
    final_order = [x for x in decade_order if x in df_decade_agg['Decade'].unique()]

    fig = px.bar(
        df_decade_agg,
        x='Decade',
        y='TotalWatchMilHours',
        category_orders={'Decade': final_order},
        text='TotalWatchMilHours',
        title="User Preference: Classic vs. Modern Content",
        color_discrete_sequence=[NETFLIX_RED]
    )

    fig.update_traces(texttemplate='%{text:.2f} M', textposition='outside')
    fig.update_yaxes(title="Total Watch Hours (Million)")

    return apply_netflix_theme(fig)

def plot_strategic_audience():
    """Figure 4: Strategic Audience Analysis (Bar)"""
    df_mpaa = get_mpaa_data()
    if df_mpaa.empty: return None

    # Define Logic to Group Ratings
    def classify_audience(rating):
        r = str(rating).upper().strip()
        if r in ['TV-MA', 'R', 'NC-17', 'UR']:
            return 'Adults (Mature)'
        if r in ['TV-14', 'PG-13']:
            return 'Teens (13+)'
        if r in ['TV-PG', 'PG', 'G', 'TV-G', 'TV-Y', 'TV-Y7', 'TV-Y7-FV']:
            return 'Kids & Family'
        return 'Other'

    df_mpaa['AudienceSegment'] = df_mpaa['MpaaRating'].apply(classify_audience)
    df_audience = df_mpaa.groupby('AudienceSegment', as_index=False)['TotalWatch'].sum()
    
    # Convert Units: Million Hours
    df_audience['StreamingMilHours'] = df_audience['TotalWatch'] / 60 / 1000000
    df_audience = df_audience.sort_values('StreamingMilHours', ascending=False)

    fig = px.bar(
        df_audience,
        x='AudienceSegment',
        y='StreamingMilHours',
        text='StreamingMilHours',
        title="Content Consumption by Segment",
        color_discrete_sequence=[NETFLIX_RED]
    )

    fig.update_traces(texttemplate='%{text:.2f} M', textposition='outside')
    fig.update_yaxes(title="Total Watch Hours (Million)")

    return apply_netflix_theme(fig)

def plot_geo_preferences():
    """Figure 5: Regional Genre Preferences (Faceted Bar Charts)"""
    df_geo = get_geo_genre_data()
    if df_geo.empty: return None

    # 1. Top 5 countries
    top_n_countries = df_geo.groupby('CountryCode')['InteractionCount'].sum().nlargest(5).index
    df_filtered = df_geo[df_geo['CountryCode'].isin(top_n_countries)].copy()

    # 2. Top 3 genres per country
    df_top3 = (
        df_filtered.sort_values(["CountryCode", "AvgRating"], ascending=[True, False])
               .groupby("CountryCode")
               .head(3)
    )

    num_countries = len(top_n_countries)
    
    # MODIFICATION 1: Set 'facecolor=BG_BLACK' here for the main figure background
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), sharey=True, facecolor=BG_BLACK) 
    axes = axes.flatten()

    if num_countries < len(axes):
        for i in range(num_countries, len(axes)):
            fig.delaxes(axes[i])

    for i, country in enumerate(top_n_countries):
        ax = axes[i]
        country_data = df_top3[df_top3['CountryCode'] == country].sort_values('AvgRating', ascending=False)
        
        # MODIFICATION 2: Set background for the individual plot area
        ax.set_facecolor(BG_BLACK)
        
        sns.barplot(x='Genre', y='AvgRating', data=country_data, 
                    ax=ax, palette=[NETFLIX_RED, '#F7A700', '#5D5D5D'], edgecolor=BG_BLACK) 
        
        ax.set_title(f"{country}", color=NETFLIX_RED, fontsize=14, weight='bold')
        ax.set_xlabel("") 
        ax.set_ylim(0, 5.0) 
        ax.set_ylabel("Avg Rating" if i % 3 == 0 else "", color=TEXT_WHITE)
        
        # MODIFICATION 3: Ensure ticks and borders are white so they show up on black
        ax.tick_params(axis='x', rotation=45, labelsize=12, colors=TEXT_WHITE)
        ax.tick_params(axis='y', colors=TEXT_WHITE)
        
        # Make the axis borders (spines) white
        for spine in ax.spines.values():
            spine.set_edgecolor(TEXT_WHITE)

        ax.grid(axis='y', linestyle='--', alpha=0.3, color='#444444')
        
        for container in ax.containers:
            ax.bar_label(container, fmt='%.2f', fontsize=8, color=TEXT_WHITE)

    # Added y=0.98 to push title up
    fig.suptitle("Top 3 Highest Rated Genres by Country", fontsize=18, weight='bold', color=NETFLIX_RED, y=0.98)
    
    # Adjusted layout rect to prevent title clipping
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig

def plot_monthly_trends():
    """Figure 6: Monthly Watch Trends (Line)"""
    df_genre_trend = get_monthly_trend_data()
    if df_genre_trend.empty: return None

    # Filter Top 5 Genres
    top_genres = df_genre_trend.groupby('Genre')['MonthlyWatch'].sum().nlargest(5).index.tolist()
    df_trend_filtered = df_genre_trend[df_genre_trend['Genre'].isin(top_genres)].copy()

    # Create Date Label
    df_trend_filtered['DateLabel'] = df_trend_filtered['Year'].astype(str) + '-' + df_trend_filtered['Month'].astype(str).str.zfill(2)
    df_trend_filtered = df_trend_filtered.sort_values(['Year', 'Month'])

    # Remove incomplete last month
    last_month_label = df_trend_filtered['DateLabel'].max()
    df_trend_final = df_trend_filtered[df_trend_filtered['DateLabel'] != last_month_label].copy()

    # Convert Units
    df_trend_final['MonthlyWatchMilHours'] = df_trend_final['MonthlyWatch'] / 60 / 1000000

    fig = px.line(
        df_trend_final,
        x='DateLabel',
        y='MonthlyWatchMilHours',
        color='Genre',
        markers=True,
        title="Monthly Watch Trends by Top 5 Genres",
        color_discrete_sequence=px.colors.qualitative.Bold # Distinct colors for lines
    )

    fig.update_yaxes(title="Total Watch Hours (Million)")
    fig.update_xaxes(title="Month", tickangle=45)
    
    # Move legend to top right to match previous style
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))

    return apply_netflix_theme(fig)

# ==========================================
# 5. UI BUILDERS (WITH CSS & NAV FIXES)
# ==========================================

custom_css = """
body { background-color: #141414; }
.gradio-container { background-color: #141414 !important; font-family: 'Helvetica Neue', Arial, sans-serif; }
h1 { color: #E50914 !important; font-weight: 900 !important; font-size: 2.5rem !important; text-align: center; }
.subtitle { color: #aaa; text-align: center; margin-bottom: 2rem; }
.login-box { max-width: 450px; margin: auto; padding: 20px; background: #000; border-radius: 10px; }
.launcher-btn { font-size: 1.5rem !important; padding: 30px !important; margin: 10px !important; height: 200px !important; }
.role-btn { font-size: 1.2rem !important; padding: 20px !important; height: 100px !important; }
.results-container { display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 30px; }
.movie-card { background-color: #2f2f2f; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); overflow: hidden; flex: 1 1 300px; max-width: 350px; display: flex; flex-direction: column; transition: transform 0.2s; }
.movie-card:hover { transform: translateY(-5px); background-color: #383838; }
.poster-wrapper { position: relative; width: 100%; height: 400px; background-color: #000; }
.generated-poster { width: 100%; height: 100%; object-fit: cover; }
.card-content { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; }
.movie-title { margin: 0 0 5px 0; color: #fff; font-size: 1.4rem; font-weight: 800; line-height: 1.2; }
.reason-text { color: #ccc; line-height: 1.4; font-size: 0.9rem; }
"""

def build_landing():
    with gr.Blocks(title="Welcome to Netflix") as landing:
        gr.HTML(f"<style>{custom_css}</style>")
        gr.HTML("<br><br><br><h1>NETFLIX <span style='color:#fff;'> SYSTEM</span></h1>")
        gr.HTML("<div class='subtitle'>Please select your role to proceed</div>")
        with gr.Row():
            btn_user = gr.Button("I am a USER", variant="secondary", elem_classes=["role-btn"], link=LOGIN_USER_URL)
            btn_admin = gr.Button("I am an ADMIN", variant="primary", elem_classes=["role-btn"], link=LOGIN_ADMIN_URL)
        btn_user.click(fn=lambda: log_interaction("ROLE_SELECT", "Selected User Role"))
        btn_admin.click(fn=lambda: log_interaction("ROLE_SELECT", "Selected Admin Role"))
    return landing

def build_user_login():
    with gr.Blocks(title="User Login") as login_app:
        gr.HTML(f"<style>{custom_css}</style>")
        gr.HTML("<br><h1>USER <span style='color:#fff;'>LOGIN</span></h1>")
        gr.Button("⬅ Back to Selection", link=LANDING_URL)
        with gr.Column(elem_classes="login-box"):
            with gr.Tabs() as tabs:
                with gr.Tab("Sign In"):
                    with gr.Column(visible=True) as login_inputs:
                        l_user = gr.Textbox(label="Username")
                        l_pass = gr.Textbox(label="Password", type="password")
                        l_btn = gr.Button("Sign In", variant="primary")
                        l_msg = gr.Textbox(label="Status", interactive=False, show_label=False)
                    with gr.Column(visible=False) as success_col:
                        gr.Markdown("### ✅ Login Successful")
                        gr.Button("ENTER PORTAL ➜", variant="primary", link=PORTAL_USER_URL)
                with gr.Tab("Register New ID"):
                    with gr.Row():
                        r_fname = gr.Textbox(label="First Name")
                        r_lname = gr.Textbox(label="Last Name")
                    with gr.Row():
                        r_age = gr.Number(label="Age", precision=0)
                        r_country = gr.Textbox(label="Country")
                    with gr.Row():
                        r_phone = gr.Textbox(label="Phone Number")
                        r_sub = gr.Checkbox(label="Subscribe to newsletter?")
                    with gr.Row():
                        r_user = gr.Textbox(label="Desired Username")
                        r_pass = gr.Textbox(label="Password", type="password")
                    r_btn = gr.Button("Create Account")
                    r_msg = gr.Textbox(label="Registration Status", interactive=False)
        l_btn.click(login_user, inputs=[l_user, l_pass], outputs=[l_msg, login_inputs, success_col])
        r_btn.click(register_user, inputs=[r_user, r_pass, r_fname, r_lname, r_age, r_country, r_phone, r_sub], outputs=[r_msg, tabs])
    return login_app

def build_admin_login():
    with gr.Blocks(title="Admin Login") as login_app:
        gr.HTML(f"<style>{custom_css}</style>")
        gr.HTML("<br><h1>ADMIN <span style='color:#fff;'>ACCESS</span></h1>")
        gr.Button("⬅ Back to Selection", link=LANDING_URL)
        with gr.Column(elem_classes="login-box"):
            with gr.Column(visible=True) as login_inputs:
                l_user = gr.Textbox(label="Admin Username (Default: admin)")
                l_pass = gr.Textbox(label="Admin Password (Default: admin123)", type="password")
                l_btn = gr.Button("Authenticate", variant="stop")
                l_msg = gr.Textbox(label="Status", interactive=False, show_label=False)
            with gr.Column(visible=False) as success_col:
                gr.Markdown("### ✅ Admin Privileges Granted")
                gr.Button("ENTER EXECUTIVE DASHBOARD ➜", variant="primary", link=PORTAL_ADMIN_URL)
        l_btn.click(login_admin, inputs=[l_user, l_pass], outputs=[l_msg, login_inputs, success_col])
    return login_app

def build_user_portal():
    with gr.Blocks(title="User Portal") as portal:
        gr.HTML(f"<style>{custom_css}</style>")
        gr.HTML("<br><br><h1>NETFLIX <span style='color:#fff;'>USER PORTAL</span></h1>")
        gr.HTML("<div class='subtitle'>Welcome Back.</div>")
        with gr.Row():
            b1 = gr.Button("🤖 LAUNCH AI RECOMMENDER", variant="primary", elem_classes=["launcher-btn"], link=AI_URL)
        gr.Button("⬅ Log Out", link=LANDING_URL)
        b1.click(fn=lambda: log_interaction("NAV_CLICK", "User launched AI App"))
    return portal

def build_admin_portal():
    with gr.Blocks(title="Admin Portal") as portal:
        gr.HTML(f"<style>{custom_css}</style>")
        gr.HTML("<br><br><h1>NETFLIX <span style='color:#fff;'>ADMIN PORTAL</span></h1>")
        gr.HTML("<div class='subtitle'>Full System Access Granted.</div>")
        
        with gr.Row():
            b1 = gr.Button("🤖 AI RECOMMENDER\n(Semantic Search)", variant="primary", elem_classes=["launcher-btn"], link=AI_URL)
            b2 = gr.Button("📈 EXECUTIVE DASHBOARD\n(Analytics)", variant="secondary", elem_classes=["launcher-btn"], link=ANALYTICS_URL)
        
        # --- NEW: BACK TO HOME BUTTON ---
        gr.HTML("<br>")
        gr.Button("⬅ Log Out / Return to Home", variant="secondary", link=LANDING_URL)

        b1.click(fn=lambda: log_interaction("NAV_CLICK", "Admin launched AI App"))
        b2.click(fn=lambda: log_interaction("NAV_CLICK", "Admin launched Analytics App"))
    return portal

def build_ai():
    with gr.Blocks(title="Netflix AI") as ai_page:
        gr.HTML(f"<style>{custom_css}</style>")
        with gr.Row():
            # NAVIGATION BAR FOR AI APP
            gr.Button("User Portal", size="sm", link=PORTAL_USER_URL)
            gr.Button("Admin Portal", size="sm", link=PORTAL_ADMIN_URL)
            gr.Button("Log Out", size="sm", link=LANDING_URL)
        
        gr.HTML("<h1>NETFLIX <span style='color:#b3b3b3;'>AI Recommender</span></h1>")
        with gr.Row():
            with gr.Column(scale=4):
                txt_input = gr.Textbox(placeholder="Try: 'A scary movie about space aliens'", label="")
            with gr.Column(scale=1):
                btn_search = gr.Button("SEARCH", variant="primary")
        out_html = gr.HTML(label="Results")
        gr.Examples(
        examples=["A scary movie about aliens that is popular", "A romantic comedy released recently", "Find me a scary movie about aliens that is popular",
            "I want a short funny movie with good ratings"],
        inputs=txt_input,
        outputs=out_html,
        fn=search_logic,
        run_on_click=True
        )
        btn_search.click(search_logic, inputs=txt_input, outputs=out_html)
        txt_input.submit(search_logic, inputs=txt_input, outputs=out_html)
    return ai_page

def build_analytics():
    with gr.Blocks(title="Netflix Analytics") as analytics_page:
        gr.HTML(f"<style>{custom_css}</style>")

        with gr.Row():
            gr.Button("⬅ Admin Portal", size="sm", link=PORTAL_ADMIN_URL)
            gr.HTML("<div style='flex-grow:1;'></div>") 
        
        gr.HTML("<h1>NETFLIX <span style='color:white;'>EXECUTIVE ANALYTICS</span></h1>")
        
        with gr.Tabs():
            # --- TAB 1: CONTENT INTELLIGENCE ---
            with gr.TabItem("🎬 Content Intelligence"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 💎 Hidden Gems (Quality vs. Popularity)")
                        p1 = gr.Plot(label="Hidden Gems")
                    with gr.Column():
                        gr.Markdown("### ⏳ Content Vintage (Decades)")
                        p2 = gr.Plot(label="Content Vintage")
            
            # --- TAB 2: AUDIENCE DEMOGRAPHICS ---
            with gr.TabItem("👥 Audience Demographics"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🗣️ Community Voice (Reviews by Age)")
                        p3 = gr.Plot(label="Age Contribution")
                    with gr.Column():
                        gr.Markdown("### 🎯 Strategic Segments (MPAA)")
                        p4 = gr.Plot(label="Audience Segments")

            # --- TAB 3: GLOBAL & TRENDS ---
            with gr.TabItem("🌍 Global & Trends"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🗺️ Regional Preferences")
                        p5 = gr.Plot(label="Geo Preferences")
                    with gr.Column():
                        gr.Markdown("### 📈 Monthly Watch Trends")
                        p6 = gr.Plot(label="Monthly Trends")

        # --- LOAD EVENTS ---
        # Gradio automatically handles the Matplotlib Figure objects returned by these functions
        analytics_page.load(plot_hidden_gems, outputs=p1)
        analytics_page.load(plot_content_vintage, outputs=p2)
        analytics_page.load(plot_age_contribution, outputs=p3)
        analytics_page.load(plot_strategic_audience, outputs=p4)
        analytics_page.load(plot_geo_preferences, outputs=p5)
        analytics_page.load(plot_monthly_trends, outputs=p6)

    return analytics_page

# ==========================================
# 6. APP MOUNTING & STARTUP
# ==========================================
app = FastAPI()

print("Building Gradio Apps...")
landing_app = build_landing()
user_login_app = build_user_login()
admin_login_app = build_admin_login()
user_portal_app = build_user_portal()
admin_portal_app = build_admin_portal()
ai_app = build_ai()
analytics_app = build_analytics()

app = gr.mount_gradio_app(app, ai_app, path=AI_URL)
app = gr.mount_gradio_app(app, analytics_app, path=ANALYTICS_URL)
app = gr.mount_gradio_app(app, user_login_app, path=LOGIN_USER_URL)
app = gr.mount_gradio_app(app, admin_login_app, path=LOGIN_ADMIN_URL)
app = gr.mount_gradio_app(app, user_portal_app, path=PORTAL_USER_URL)
app = gr.mount_gradio_app(app, admin_portal_app, path=PORTAL_ADMIN_URL)
app = gr.mount_gradio_app(app, landing_app, path=LANDING_URL)

if __name__ == "__main__":
    import uvicorn
    
    # =======================================================
    # 🚀 AUTOMATIC PUBLIC LINK SETUP
    # =======================================================
    try:
        from pyngrok import ngrok
        
        # 🟢 FIX: SET YOUR AUTH TOKEN HERE
        # Replace the string below with your actual token from the website
        ngrok.set_auth_token("36PWvn5z0Weg3YT1dNtXIUBXlYl_7aZ5Jn8t2QnPdtUPooXc1") 
        
        ngrok.kill()
        public_url = ngrok.connect(8000).public_url
        
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🌍 PUBLIC LINK GENERATED: {public_url}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
    except ImportError:
        print("⚠️ 'pyngrok' is not installed.")
    except Exception as e:
        print(f"⚠️ Could not generate public link: {e}")

    # =======================================================
    # START SERVER
    # =======================================================
    print("🚀 Server starting on local port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)