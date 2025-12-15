-- ==========================================================
-- PART 3:  Analytical Queries for Decision-Making
-- Supports enhancement of emotion-based search recommendation
-- ==========================================================

USE dw_netflix_analytics;

-- Query for Table 1: Top 3 Highest Rated Genres by Country
WITH RankedGenres AS (
    SELECT 
        du.CountryCode, 
        dt.Genre, 
        ROUND(AVG(f.AvgRating), 2) AS AvgRating,
        RANK() OVER (PARTITION BY du.CountryCode ORDER BY AVG(f.AvgRating) DESC) as RankNum
    FROM FactUserContentMetrics f
    JOIN DimUser du ON f.UserKey = du.UserKey
    JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
    GROUP BY du.CountryCode, dt.Genre
    HAVING COUNT(*) > 10
)
SELECT CountryCode, Genre, AvgRating
FROM RankedGenres
WHERE RankNum <= 3
ORDER BY CountryCode, RankNum;

-- Query for Table 2: Streaming Hours by Audience Segment
SELECT 
    CASE 
        WHEN UPPER(dt.MpaaRating) IN ('TV-MA', 'R', 'NC-17', 'UR') THEN 'Adults (Mature)'
        WHEN UPPER(dt.MpaaRating) IN ('TV-14', 'PG-13') THEN 'Teens (13+)'
        WHEN UPPER(dt.MpaaRating) IN ('TV-PG', 'PG', 'G', 'TV-G', 'TV-Y', 'TV-Y7') THEN 'Kids & Family'
        ELSE 'Other'
    END AS AudienceSegment,
    ROUND(SUM(f.TotalWatchMins) / 60.0 / 1000000.0, 2) AS TotalStreamingHours_Millions
FROM FactUserContentMetrics f
JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
WHERE dt.MpaaRating IS NOT NULL
GROUP BY AudienceSegment
ORDER BY TotalStreamingHours_Millions DESC;

-- Query for Table 3: Top 5 Hidden Gem Genres (High Rating, Low Popularity)
SELECT 
    dt.Genre, 
    ROUND(AVG(f.AvgRating), 2) AS AvgRating,
    ROUND(SUM(f.TotalWatchMins) / 60.0, 0) AS TotalWatchHours
FROM FactUserContentMetrics f
JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
GROUP BY dt.Genre
HAVING AvgRating > 4.0  -- High Quality
ORDER BY TotalWatchHours ASC -- Lowest popularity first
LIMIT 5;

-- Query for Table 4: Total Reviews Contributed by Age Group
SELECT 
    du.AgeGroup, 
    COUNT(DISTINCT f.TitleKey) AS TotalReviewsContributed
FROM FactUserContentMetrics f
JOIN DimUser du ON f.UserKey = du.UserKey
WHERE f.ReviewCount > 0 
GROUP BY du.AgeGroup
ORDER BY TotalReviewsContributed DESC;

-- Query for Table 5: Monthly Watch Hours for Top 5 Genres
SELECT 
    dd.Year, 
    dd.Month, 
    dt.Genre, 
    ROUND(SUM(f.TotalWatchMins) / 60.0 / 1000000.0, 2) AS MonthlyHours_Millions
FROM FactUserContentMetrics f
JOIN DimDate dd ON f.DateKey = dd.DateKey
JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
WHERE dt.Genre IN (
    -- Subquery to find top 5 genres
    SELECT Genre FROM (
        SELECT dt.Genre, SUM(f.TotalWatchMins) as Total
        FROM FactUserContentMetrics f JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
        GROUP BY dt.Genre ORDER BY Total DESC LIMIT 5
    ) AS TopGenres
)
GROUP BY dd.Year, dd.Month, dt.Genre
ORDER BY dd.Year, dd.Month, dt.Genre;

-- Query for Table 6: Watch Time by Release Decade
SELECT 
    CASE 
        WHEN dt.ReleaseYear < 1990 THEN 'Pre-1990'
        WHEN dt.ReleaseYear BETWEEN 1990 AND 1999 THEN '1990s'
        WHEN dt.ReleaseYear BETWEEN 2000 AND 2009 THEN '2000s'
        WHEN dt.ReleaseYear BETWEEN 2010 AND 2019 THEN '2010s'
        WHEN dt.ReleaseYear >= 2020 THEN '2020s'
    END AS ReleaseDecade,
    ROUND(SUM(f.TotalWatchMins) / 60.0 / 1000000.0, 2) AS TotalWatchHours_Millions
FROM FactUserContentMetrics f
JOIN DimTitle dt ON f.TitleKey = dt.TitleKey
WHERE dt.ReleaseYear IS NOT NULL
GROUP BY ReleaseDecade
ORDER BY ReleaseDecade;