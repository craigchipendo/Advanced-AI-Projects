-- ==========================================================
-- PART 3:  Create Data Warehouse for Search Recommendation Analytics
-- Based on netflix_oltp schema from Part 1
-- ==========================================================

CREATE DATABASE IF NOT EXISTS dw_netflix_analytics;
USE dw_netflix_analytics;

-- ----------------------------------------------------------
-- Dimension:  Users (demographics, region, subscription)
-- ----------------------------------------------------------
CREATE TABLE DimUser (
    UserKey      INT AUTO_INCREMENT PRIMARY KEY,
    UserID       VARCHAR(50),
    CountryCode  VARCHAR(100),
    AgeGroup     VARCHAR(20),
    Subscription VARCHAR(50),
    LastLogin    DATE
);

-- ----------------------------------------------------------
-- Dimension:  Titles / Content
-- ----------------------------------------------------------
CREATE TABLE DimTitle (
    TitleKey     INT AUTO_INCREMENT PRIMARY KEY,
    TitleID      VARCHAR(50),
    Title        VARCHAR(255),
    Type         VARCHAR(20),
    ReleaseYear  INT,
    MpaaRating   VARCHAR(20),
    Genre        VARCHAR(255)
);

-- ----------------------------------------------------------
-- Dimension:  Calendar Dates
-- ----------------------------------------------------------
CREATE TABLE DimDate (
    DateKey   INT PRIMARY KEY,
    FullDate  DATE,
    Year      INT,
    Month     INT,
    Day       INT
);

-- ----------------------------------------------------------
-- Fact:  Viewing & Review Metrics
-- Grain = User × Title × Date
-- ----------------------------------------------------------
CREATE TABLE FactUserContentMetrics (
    FactKey          BIGINT AUTO_INCREMENT PRIMARY KEY,
    UserKey          INT,
    TitleKey         INT,
    DateKey          INT,
    TotalWatchMins   INT,
    AvgRating        DECIMAL(4,2),
    ReviewCount      INT,
    FOREIGN KEY (UserKey)  REFERENCES DimUser(UserKey),
    FOREIGN KEY (TitleKey) REFERENCES DimTitle(TitleKey),
    FOREIGN KEY (DateKey)  REFERENCES DimDate(DateKey)
);

-- ==========================================================
-- PART 3:  ETL — Extract, Transform & Load Data from netflix_oltp
-- ==========================================================
USE dw_netflix_analytics;

-- -------------------------
-- 1. Load DimUser
-- -------------------------
INSERT INTO DimUser (UserID, CountryCode, AgeGroup, Subscription, LastLogin)
SELECT 
    su.User_ID AS UserID,
    su.Country AS CountryCode,
    CASE 
        WHEN su.Age < 18 THEN 'Under 18'
        WHEN su.Age BETWEEN 18 AND 25 THEN '18-25'
        WHEN su.Age BETWEEN 26 AND 35 THEN '26-35'
        WHEN su.Age BETWEEN 36 AND 50 THEN '36-50'
        WHEN su.Age > 50 THEN '50+'
        ELSE 'Unknown'
    END AS AgeGroup,
    su.Subscription_Type AS Subscription,
    STR_TO_DATE(su.Last_Login, '%Y-%m-%d') AS LastLogin
FROM netflix_oltp.stg_users su;

-- -------------------------
-- 2. Load DimTitle
-- -------------------------
INSERT INTO DimTitle (TitleID, Title, Type, ReleaseYear, MpaaRating, Genre)
SELECT 
    show_id AS TitleID,
    title AS Title,
    type AS Type,
    release_year AS ReleaseYear,
    rating AS MpaaRating,
    TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(listed_in, ',', n.n), ',', -1)) AS Genre
FROM netflix_oltp.stg_titles
JOIN (
    -- Generate numbers 1–6 for splitting (supports up to 6 genres per title)
    SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3 
    UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6
) n
WHERE n.n <= 1 + LENGTH(listed_in) - LENGTH(REPLACE(listed_in, ',', ''));




-- -------------------------
-- 3. Load DimDate (from View and Review dates)
-- -------------------------
INSERT INTO DimDate (DateKey, FullDate, Year, Month, Day)
SELECT DISTINCT 
    DATE_FORMAT(StartTime,'%Y%m%d') AS DateKey,
    DATE(StartTime),
    YEAR(StartTime),
    MONTH(StartTime),
    DAY(StartTime)
FROM netflix_oltp.ViewingActivity
WHERE StartTime IS NOT NULL
UNION
SELECT DISTINCT 
    DATE_FORMAT(ReviewDate,'%Y%m%d'),
    ReviewDate,
    YEAR(ReviewDate),
    MONTH(ReviewDate),
    DAY(ReviewDate)
FROM netflix_oltp.ContentReviews
WHERE ReviewDate IS NOT NULL;

-- -------------------------
-- 4. Load Fact (User × Title × Date)
-- -------------------------
INSERT INTO FactUserContentMetrics (UserKey, TitleKey, DateKey, TotalWatchMins, AvgRating, ReviewCount)
SELECT 
    du.UserKey,
    dt.TitleKey,
    DATE_FORMAT(va.StartTime,'%Y%m%d') AS DateKey,
    SUM(va.DurationMinutes)              AS TotalWatchMins,
    ROUND(AVG(cr.Rating),2)              AS AvgRating,
    COUNT(cr.ReviewID)                   AS ReviewCount
FROM netflix_oltp.ViewingActivity va
JOIN dw_netflix_analytics.DimUser  du ON du.UserID  = va.UserID
LEFT JOIN dw_netflix_analytics.DimTitle dt ON dt.TitleID = va.TitleID
LEFT JOIN netflix_oltp.ContentReviews cr 
       ON cr.UserID = va.UserID AND cr.TitleID = va.TitleID
GROUP BY du.UserKey, dt.TitleKey, DateKey;

select * 
from FactUserContentMetrics;
