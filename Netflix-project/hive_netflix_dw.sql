-- ======================================================================
--  HIVE DATA WAREHOUSE FOR NETFLIX ANALYTICS
--  netflix_dw database
--  Author: Gad Rukundo (Team 14)
--  Description:
--     - Creates Hive database
--     - Creates raw external tables mapping to S3 files
--     - Creates warehouse star-schema tables in Parquet
--     - Performs ETL into dimension + fact tables
--     - Executes analytical (decision-making) queries
-- ======================================================================


-- ======================================================================
-- 1. SETUP
-- ======================================================================

CREATE DATABASE IF NOT EXISTS netflix_dw;
USE netflix_dw;

-- Dynamic partitioning settings
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

-- Increase limits so ETL can create many partitions
SET hive.exec.max.dynamic.partitions = 5000;
SET hive.exec.max.dynamic.partitions.pernode = 1000;
SET hive.exec.max.created.files = 50000;



-- ======================================================================
-- 2. RAW EXTERNAL TABLES (FROM S3)
--    These are schema-on-read tables pointing directly to CSVs in S3
-- ======================================================================

-- -------- RAW TITLES --------
CREATE EXTERNAL TABLE IF NOT EXISTS raw_stg_titles (
    show_id        STRING,
    type           STRING,
    title          STRING,
    director       STRING,
    cast_list      STRING,
    country        STRING,
    date_added_str STRING,
    release_year   INT,
    rating         STRING,
    duration       STRING,
    listed_in      STRING,
    description    STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\""
)
STORED AS TEXTFILE
LOCATION 's3://bigdatafinalprojectgad/netflix/staging/titles/'
TBLPROPERTIES ("skip.header.line.count"="1");


-- -------- RAW EPISODES --------
CREATE EXTERNAL TABLE IF NOT EXISTS raw_stg_episodes (
    episode_id      STRING,
    show_id         STRING,
    season_number   INT,
    episode_number  INT,
    title           STRING,
    runtime_minutes INT,
    air_date_str    STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\""
)
STORED AS TEXTFILE
LOCATION 's3://bigdatafinalprojectgad/netflix/staging/episodes/'
TBLPROPERTIES ("skip.header.line.count"="1");


-- -------- RAW WATCH EVENTS --------
CREATE EXTERNAL TABLE IF NOT EXISTS raw_stg_watch_events (
    event_id         STRING,
    user_id          STRING,
    content_id       STRING,
    content_type     STRING,
    start_time_str   STRING,
    duration_minutes INT,
    device_type      STRING,
    country_code     STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\""
)
STORED AS TEXTFILE
LOCATION 's3://bigdatafinalprojectgad/netflix/staging/watch_events/'
TBLPROPERTIES ("skip.header.line.count"="1");


-- -------- RAW CONTENT REVIEWS --------
CREATE EXTERNAL TABLE IF NOT EXISTS raw_stg_content_reviews (
    review_id        STRING,
    user_id          STRING,
    user_type        STRING,
    show_id          STRING,
    rating           INT,
    review_date_str  STRING,
    comment          STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\""
)
STORED AS TEXTFILE
LOCATION 's3://bigdatafinalprojectgad/netflix/staging/content_reviews/'
TBLPROPERTIES ("skip.header.line.count"="1");



-- ======================================================================
-- 3. STAR SCHEMA WAREHOUSE TABLES (PARQUET)
-- ======================================================================

-- -------- DIMENSION: TITLES --------
CREATE TABLE IF NOT EXISTS dim_titles (
    title_id      STRING,
    title         STRING,
    type          STRING,
    release_year  INT,
    rating        STRING,
    description   STRING,
    date_added    DATE
)
STORED AS PARQUET;


-- -------- DIMENSION: EPISODES --------
CREATE TABLE IF NOT EXISTS dim_episodes (
    episode_id      STRING,
    title_id        STRING,
    season_number   INT,
    episode_number  INT,
    episode_title   STRING,
    runtime_minutes INT,
    air_date        DATE
)
STORED AS PARQUET;


-- -------- FACT: WATCH EVENTS --------
CREATE TABLE IF NOT EXISTS fact_watch_events (
    event_id         STRING,
    user_id          STRING,
    content_id       STRING,
    content_type     STRING,
    start_time       TIMESTAMP,
    duration_minutes INT,
    device_type      STRING,
    country_code     STRING
)
PARTITIONED BY (event_date DATE)
STORED AS PARQUET;


-- -------- FACT: CONTENT REVIEWS --------
CREATE TABLE IF NOT EXISTS fact_content_reviews (
    review_id    STRING,
    user_id      STRING,
    user_type    STRING,
    show_id      STRING,
    rating       INT,
    review_date  DATE,
    comment      STRING
)
PARTITIONED BY (review_year INT)
STORED AS PARQUET;



-- ======================================================================
-- 4. ETL INTO WAREHOUSE TABLES
-- ======================================================================

-- -------- LOAD dim_titles --------
INSERT OVERWRITE TABLE dim_titles
SELECT
    show_id                         AS title_id,
    title,
    type,
    release_year,
    rating,
    description,
    TO_DATE(
        FROM_UNIXTIME(
            UNIX_TIMESTAMP(date_added_str, 'MMMM d, yyyy')
        )
    ) AS date_added
FROM raw_stg_titles;


-- -------- LOAD dim_episodes --------
INSERT OVERWRITE TABLE dim_episodes
SELECT
    episode_id,
    show_id             AS title_id,
    season_number,
    episode_number,
    title               AS episode_title,
    runtime_minutes,
    TO_DATE(air_date_str) AS air_date
FROM raw_stg_episodes;


-- -------- LOAD fact_watch_events (partitioned by event_date) --------
INSERT OVERWRITE TABLE fact_watch_events PARTITION (event_date)
SELECT
    event_id,
    user_id,
    content_id,
    content_type,
    FROM_UNIXTIME(
        UNIX_TIMESTAMP(start_time_str, 'yyyy-MM-dd HH:mm:ss')
    ) AS start_time,
    duration_minutes,
    device_type,
    country_code,
    TO_DATE(start_time_str) AS event_date
FROM raw_stg_watch_events;


-- -------- LOAD fact_content_reviews (partitioned by review_year) --------
INSERT OVERWRITE TABLE fact_content_reviews PARTITION (review_year)
SELECT
    review_id,
    user_id,
    user_type,
    show_id,
    rating,
    TO_DATE(review_date_str) AS review_date,
    comment,
    YEAR(TO_DATE(review_date_str)) AS review_year
FROM raw_stg_content_reviews;



-- ======================================================================
-- 5. ANALYTICAL / DECISION-MAKING QUERIES
-- ======================================================================

-- -------- Q1: Top 10 most-watched titles --------
SELECT
    t.title,
    COUNT(*) AS total_views
FROM fact_watch_events f
JOIN dim_titles t
    ON f.content_id = t.title_id
GROUP BY t.title
ORDER BY total_views DESC
LIMIT 10;


-- -------- Q2: Average viewing duration per country --------
SELECT
    country_code,
    AVG(duration_minutes) AS avg_watch_minutes,
    COUNT(*) AS total_events
FROM fact_watch_events
GROUP BY country_code
ORDER BY avg_watch_minutes DESC;


-- -------- Q3: Average rating for Movies vs TV Shows --------
SELECT
    t.type,
    AVG(f.rating) AS avg_rating,
    COUNT(*)     AS review_count
FROM fact_content_reviews f
JOIN dim_titles t
    ON f.show_id = t.title_id
GROUP BY t.type;


-- -------- Q4: Daily Active Users (DAU) --------
SELECT
    event_date,
    COUNT(DISTINCT user_id) AS dau
FROM fact_watch_events
GROUP BY event_date
ORDER BY event_date;


-- ======================================================================
-- END OF FILE
-- ======================================================================