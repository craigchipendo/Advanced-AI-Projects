-- ==========================================================
-- PART 1: STAGING AREA 
-- ==========================================================

CREATE DATABASE netflix_oltp;
USE netflix_oltp;

-- Source: netflix_titles_clean_utf8.csv
CREATE TABLE IF NOT EXISTS stg_titles (
    show_id VARCHAR(50),
    type VARCHAR(50),
    title VARCHAR(500),
    director TEXT,
    cast_list TEXT,
    country VARCHAR(100),
    date_added VARCHAR(100),
    release_year INT,
    rating VARCHAR(20),
    duration VARCHAR(50),
    listed_in TEXT,
    description TEXT
);

-- Source: netflix_users_clean.csv
CREATE TABLE IF NOT EXISTS stg_users (
    User_ID VARCHAR(50),
    Name VARCHAR(255),
    Age INT,
    Country VARCHAR(100),
    Subscription_Type VARCHAR(50),
    Watch_Time_Hours DECIMAL(10, 2),
    Favorite_Genre VARCHAR(100),
    Last_Login VARCHAR(50) -- "2024-05-12"
);

-- Source: critic_users.csv
CREATE TABLE IF NOT EXISTS stg_critics (
    UserID VARCHAR(50),
    UserName VARCHAR(255),
    Country VARCHAR(100),
    SubscriptionType VARCHAR(50),
    UserType VARCHAR(50),
    JoinDate VARCHAR(50)
);

-- Source: dim_episodes.csv
CREATE TABLE IF NOT EXISTS stg_episodes (
    episode_id VARCHAR(50),
    show_id VARCHAR(50),
    season_number INT,
    episode_number INT,
    title VARCHAR(255),
    runtime_minutes INT,
    air_date VARCHAR(50)
);

-- Source: fact_watch_events.csv
CREATE TABLE IF NOT EXISTS stg_watch_events (
    event_id VARCHAR(50),
    user_id VARCHAR(50),
    content_id VARCHAR(50),
    content_type VARCHAR(20),
    start_time VARCHAR(50), 
    duration_minutes INT,
    device_type VARCHAR(50),
    country_code VARCHAR(10)
);

-- Source: fact_content_reviews.csv
CREATE TABLE IF NOT EXISTS stg_content_reviews (
    review_id VARCHAR(50),
    user_id VARCHAR(50),
    user_type VARCHAR(20),
    show_id VARCHAR(50),
    rating INT,
    review_date VARCHAR(50),
    comment TEXT
);

-- ==========================================================
-- PART 2: OLTP SCHEMA (Normalized Tables)
-- ==========================================================

-- 1. Reference Tables
CREATE TABLE IF NOT EXISTS SubscriptionPlans (
    PlanID SERIAL PRIMARY KEY,
    PlanName VARCHAR(50) UNIQUE NOT NULL, 
    Price DECIMAL(5, 2),
    MaxScreens INT
);

CREATE TABLE IF NOT EXISTS Roles (
    RoleID SERIAL PRIMARY KEY,
    RoleName VARCHAR(50) UNIQUE NOT NULL 
);

-- 2. User Management
DROP TABLE Users;
CREATE TABLE IF NOT EXISTS Users (
    UserID VARCHAR(50) PRIMARY KEY, 
    DisplayName VARCHAR(255),
    CountryCode VARCHAR(100),
    LastLogin DATE
);

CREATE TABLE IF NOT EXISTS UserRoles (
    UserID VARCHAR(50),
    RoleID BIGINT UNSIGNED, 
    PRIMARY KEY (UserID, RoleID),
    CONSTRAINT fk_ur_user FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT fk_ur_role FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
);

CREATE TABLE IF NOT EXISTS Subscriptions (
    SubscriptionID SERIAL PRIMARY KEY,
    UserID VARCHAR(50),
    PlanID BIGINT UNSIGNED, 
    Status VARCHAR(20) DEFAULT 'Active',
    CONSTRAINT fk_sub_user FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT fk_sub_plan FOREIGN KEY (PlanID) REFERENCES SubscriptionPlans(PlanID)
);

-- 3. Content Catalog
CREATE TABLE IF NOT EXISTS Titles (
    TitleID VARCHAR(50) PRIMARY KEY, 
    Title VARCHAR(500),
    Type VARCHAR(20),
    ReleaseYear INT,
    MpaaRating VARCHAR(10),
    Description TEXT,
    DateAdded DATE
);

CREATE TABLE IF NOT EXISTS Episodes (
    EpisodeID VARCHAR(50) PRIMARY KEY,
    TitleID VARCHAR(50),
    SeasonNumber INT,
    EpisodeNumber INT,
    Title VARCHAR(255),
    RuntimeMinutes INT,
    AirDate DATE,
    CONSTRAINT fk_ep_title FOREIGN KEY (TitleID) REFERENCES Titles(TitleID)
);

-- 4. Activity & Logs
CREATE TABLE IF NOT EXISTS ViewingActivity (
    ActivityID VARCHAR(50) PRIMARY KEY,
    UserID VARCHAR(50),
    TitleID VARCHAR(50), -- Nullable
    EpisodeID VARCHAR(50), -- Nullable
    StartTime TIMESTAMP,
    DurationMinutes INT,
    DeviceType VARCHAR(50),
    CONSTRAINT fk_act_user FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT fk_act_title FOREIGN KEY (TitleID) REFERENCES Titles(TitleID),
    CONSTRAINT fk_act_ep FOREIGN KEY (EpisodeID) REFERENCES Episodes(EpisodeID)
);

CREATE TABLE IF NOT EXISTS ContentReviews (
    ReviewID VARCHAR(50) PRIMARY KEY,
    UserID VARCHAR(50),
    TitleID VARCHAR(50),
    Rating INT,
    Comment TEXT,
    ReviewDate DATE,
    CONSTRAINT fk_rev_user FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT fk_rev_title FOREIGN KEY (TitleID) REFERENCES Titles(TitleID)
);

-- ==========================================================
-- PART 3: LOAD & TRANSFORM (ELT Process)
-- ==========================================================

-- A. Load CSVs into Staging (Update paths!)
-- Ensure the CSV header row is skipped if present
-- ensure local_infile is ON for MySQL if using local paths
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/Users/craig/OneDrive/Desktop/Goizueta Business School/Courses/ISOM-671-4101 Managing Big Data - Fall 2025/Final Project/netflix_titles_clean_utf8.csv' 
INTO TABLE stg_titles FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE 'C:/Users/craig/OneDrive/Desktop/Goizueta Business School/Courses/ISOM-671-4101 Managing Big Data - Fall 2025/Final Project/netflix_users_clean.csv' 
INTO TABLE stg_users FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE 'C:/Users/craig/OneDrive/Desktop/Goizueta Business School/Courses/ISOM-671-4101 Managing Big Data - Fall 2025/Final Project/critic_users.csv' 
INTO TABLE stg_critics FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE 'C:/Users/craig/OneDrive/Desktop/Goizueta Business School/Courses/ISOM-671-4101 Managing Big Data - Fall 2025/Final Project/dim_episodes.csv' 
INTO TABLE stg_episodes FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE 'C:/Users/craig/OneDrive/Desktop/Goizueta Business School/Courses/ISOM-671-4101 Managing Big Data - Fall 2025/Final Project/fact_watch_events.csv' 
INTO TABLE stg_watch_events FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE 'C:/Users/craig/OneDrive/Desktop/Goizueta Business School/Courses/ISOM-671-4101 Managing Big Data - Fall 2025/Final Project/fact_content_reviews.csv' 
INTO TABLE stg_content_reviews FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;


-- B. Populate Reference Tables
INSERT IGNORE INTO Roles (RoleName) VALUES ('Subscriber'), ('Critic');

INSERT IGNORE INTO SubscriptionPlans (PlanName, Price, MaxScreens)
VALUES 
    ('Basic', 9.99, 1),
    ('Standard', 15.49, 2),
    ('Premium', 19.99, 4);

-- C. Populate Users (Transforming Dates)
INSERT IGNORE INTO Users (UserID, DisplayName, CountryCode, LastLogin)
SELECT User_ID, Name, Country, STR_TO_DATE(Last_Login, '%Y-%m-%d') FROM stg_users;

INSERT IGNORE INTO Users (UserID, DisplayName, CountryCode, LastLogin)
SELECT UserID, UserName, Country, STR_TO_DATE(JoinDate, '%Y-%m-%d') FROM stg_critics;

-- D. Populate UserRoles & Subscriptions
-- Subscribers
INSERT IGNORE INTO UserRoles (UserID, RoleID)
SELECT User_ID, (SELECT RoleID FROM Roles WHERE RoleName = 'Subscriber') FROM stg_users;

INSERT IGNORE INTO Subscriptions (UserID, PlanID)
SELECT u.User_ID, p.PlanID
FROM stg_users u
JOIN SubscriptionPlans p ON u.Subscription_Type = p.PlanName;

-- Critics
INSERT IGNORE INTO UserRoles (UserID, RoleID)
SELECT UserID, (SELECT RoleID FROM Roles WHERE RoleName = 'Critic') FROM stg_critics;

-- E. Populate Content Catalog
INSERT IGNORE INTO Titles (TitleID, Title, Type, ReleaseYear, MpaaRating, Description, DateAdded)
SELECT show_id, title, type, release_year, rating, description, STR_TO_DATE(date_added, '%M %d, %Y')
FROM stg_titles;

INSERT IGNORE INTO Episodes (EpisodeID, TitleID, SeasonNumber, EpisodeNumber, Title, RuntimeMinutes, AirDate)
SELECT episode_id, show_id, season_number, episode_number, title, runtime_minutes, STR_TO_DATE(air_date, '%Y-%m-%d')
FROM stg_episodes;

-- F. Populate Activity
INSERT IGNORE INTO ViewingActivity (ActivityID, UserID, TitleID, EpisodeID, StartTime, DurationMinutes, DeviceType)
SELECT 
    event_id,
    user_id,
    CASE WHEN content_type = 'Movie' THEN content_id ELSE NULL END,   
    CASE WHEN content_type = 'Episode' THEN content_id ELSE NULL END, 
    STR_TO_DATE(start_time, '%Y-%m-%d %H:%i:%s'), 
    duration_minutes,
    device_type
FROM stg_watch_events;

-- G. Populate Reviews
INSERT IGNORE INTO ContentReviews (ReviewID, UserID, TitleID, Rating, Comment, ReviewDate)
SELECT review_id, user_id, show_id, rating, comment, STR_TO_DATE(review_date, '%Y-%m-%d')
FROM stg_content_reviews;


-- Check counts for normalized OLTP tables (excluding staging tables)
SELECT 'SubscriptionPlans' AS TableName, COUNT(*) AS RecordCount FROM SubscriptionPlans
UNION ALL
SELECT 'Roles', COUNT(*) FROM Roles
UNION ALL
SELECT 'Users', COUNT(*) FROM Users
UNION ALL
SELECT 'UserRoles', COUNT(*) FROM UserRoles
UNION ALL
SELECT 'Subscriptions', COUNT(*) FROM Subscriptions
UNION ALL
SELECT 'Titles', COUNT(*) FROM Titles
UNION ALL
SELECT 'Episodes', COUNT(*) FROM Episodes
UNION ALL
SELECT 'ViewingActivity', COUNT(*) FROM ViewingActivity
UNION ALL
SELECT 'ContentReviews', COUNT(*) FROM ContentReviews;


select * FROM SubscriptionPlans LIMIT 5;
SELECT * FROM Users LIMIT 5;
SELECT * FROM Subscriptions LIMIT 5;
SELECT * FROM Titles LIMIT 5;
SELECT * FROM Episodes LIMIT 5;
SELECT * FROM ViewingActivity LIMIT 5;
SELECT * FROM ContentReviews LIMIT 5;