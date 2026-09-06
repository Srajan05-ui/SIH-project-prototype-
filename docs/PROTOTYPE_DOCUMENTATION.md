# AirPrice India — SIH26056 Prototype Documentation

> **Project:** Smart Hackathon India 2026, Problem ID: SIH26056
> **Goal:** Build a Real-Time Airfare Price Index for India (like CPI but only for airline tickets)
> **Status:** Live & Deployed

---

## Table of Contents

1. [What is this Project? (Simple Explanation)](#1-what-is-this-project)
2. [The Big Picture — How Everything Connects](#2-the-big-picture)
3. [Glossary — Every Important Term Explained](#3-glossary)
4. [Technology Stack — Every Tool Used and Why](#4-technology-stack)
5. [File-by-File Code Explanation](#5-file-by-file-code-explanation)
6. [Complete Data Flow — Step by Step](#6-complete-data-flow)
7. [The CPI Math — How It Is Calculated](#7-the-cpi-math)
8. [Anomaly Detection — How We Catch Bad Data](#8-anomaly-detection)
9. [Automation — How the System Runs Itself](#9-automation)
10. [Dashboard — What the User Sees](#10-dashboard)
11. [What Results the Prototype Provides](#11-what-results-the-prototype-provides)
12. [Recommended Scraping Times](#12-recommended-scraping-times)
13. [Important Problems We Faced While Building](#13-important-problems-we-faced)

---

## 1. What Is This Project?

### The Simple Problem
Every month, India's Ministry of Statistics (MoSPI) publishes the Consumer Price Index (CPI) — a number that tells you if things are getting more expensive or cheaper. But MoSPI's airfare data is collected manually and published with a 30 to 45 day delay. By the time you read it, the price has already changed.

### Our Solution
We built a fully automated system that scrapes live airfare prices from the internet every day, calculates its own real-time airfare CPI, and shows it on an interactive dashboard — giving a signal that is 30 days *faster* than the official government data.

### In One Line
> "We are the real-time airfare equivalent of the stock market ticker, but for CPI."

---

## 2. The Big Picture

The system has 4 major layers that work together:

```
LAYER 1: DATA COLLECTION (Scrapers)
  Tier 1: Google Flights (fast-flights library)
  Tier 2: Direct Airline APIs (IndiGo, Air India mock)
  Tier 0: DGCA Government Data (mock for prototype)
              |
              | Raw price data written to database
              v
LAYER 2: DATA PROCESSING (Pipeline Scripts)
  Stage 3: cleaning.py  -> Remove duplicate & outlier prices
  Stage 4: index_calc.py -> Calculate CPI for each route
  Stage 5: anomaly.py   -> Detect suspicious price spikes
              |
              | Clean, processed data stored in DB
              v
LAYER 3: CLOUD DATABASE (Supabase / PostgreSQL)
  Stores all raw + cleaned fare data and computed CPI values
  Accessible from anywhere in the world (cloud hosted)
              |
              | Dashboard reads data live from DB
              v
LAYER 4: DASHBOARD (Streamlit Web App)
  Interactive India map, CPI charts, fare trends, anomaly alerts
  Publicly accessible URL — judges can open it on their phone
```

**Automation Layer:**
- **Local PC:** smart_scheduler.py triggers the pipeline 5 times a day
- **Cloud (GitHub Actions):** Triggers the pipeline on remote Ubuntu servers even when the PC is off

---

## 3. Glossary

| Term | What It Means in Plain Language |
|---|---|
| **CPI (Consumer Price Index)** | A number that shows how much prices have changed. If CPI = 110, prices are 10% higher than before. Base is always 100. |
| **Base Period** | The starting date we compare everything to. On the base date, CPI = exactly 100. |
| **Airfare Index** | Same as CPI but specifically for airline ticket prices. |
| **Inflation** | When prices go up. CPI > 100 means inflation. |
| **Deflation** | When prices go down. CPI < 100 means deflation. |
| **Route** | A specific flight path. E.g., DEL to BOM means Delhi to Mumbai. |
| **Booking Window** | How many days in advance the ticket is being bought. A "7-day window" means the ticket is for a flight 7 days from today. |
| **Scraping** | Automatically reading data from a website, the same way a human would read it, but done by a computer program at high speed. |
| **Tier** | A ranking of our data sources from best to worst quality. Tier 1 = real data, Tier 0 = government. |
| **Pipeline** | A sequence of programs that run one after another. Like a factory assembly line. |
| **Laspeyres Index** | The official formula used by India's government to calculate CPI. We use the same formula. |
| **Outlier** | A price that is so extreme (too high or too low) that it is mathematically impossible to be real. We flag and ignore these. |
| **Anomaly** | A suspicious price spike that could be real (festival pricing) OR a data collection bug. We alert humans to investigate. |
| **Z-Score** | A mathematical measure of "how unusual is this number compared to normal?" If Z-Score > 2.5, it is very unusual. |
| **IQR (Interquartile Range)** | A statistical method to find outliers. Anything outside 1.5 times the "normal range" is an outlier. |
| **Supabase** | A cloud database service. Our data lives here permanently in the cloud. Free tier supports up to 500MB. |
| **PostgreSQL** | The type of database engine. The same database used by Instagram, Reddit, and Twitter. |
| **GitHub Actions** | A free service that runs our code automatically on cloud servers without us doing anything. |
| **Cron** | A scheduling system for computers. Like setting an alarm clock but for code. |
| **Streamlit** | A Python library that turns Python code into a beautiful web application automatically. |
| **Plotly** | A library for making interactive charts and maps. |
| **IST / UTC** | IST = Indian Standard Time (UTC+5:30). UTC = International time standard. GitHub servers use UTC so we must convert. |
| **fast-flights** | A Python library that reads Google Flights price data without needing an official API. |
| **SQLAlchemy** | A Python library that connects Python code to a database. |
| **Transaction Pooler** | A middleman that manages many database connections efficiently. Supabase provides this. |
| **Venv (.venv)** | Virtual Environment. An isolated copy of Python with only the packages this project needs. |

---

## 4. Technology Stack

### Core Language

| Technology | Version | Why We Use It |
|---|---|---|
| **Python** | 3.11 | Main programming language. Has the best data science and web scraping libraries in the world. |

### Data Collection

| Technology | Why We Use It |
|---|---|
| **fast-flights** | Reads Google Flights data without a browser. Gets real prices in 1-2 seconds per route. |
| **curl_cffi** | Makes our scraper look like a real browser to avoid being blocked by airline websites. |
| **tenacity** | Automatic retry library. If a network request fails, it tries again with exponential backoff. |

### Data Processing and Analysis

| Technology | Why We Use It |
|---|---|
| **Pandas** | Industry-standard library for data manipulation. We use it to clean, filter, group, and calculate CPI. |
| **scikit-learn** | Machine learning library. Used for optional Isolation Forest anomaly detection. |
| **SQLAlchemy** | Lets us talk to our PostgreSQL database using Python code instead of raw SQL. |
| **psycopg2-binary** | The driver that connects Python to PostgreSQL. |

### Database

| Technology | Why We Use It |
|---|---|
| **Supabase** | Cloud-hosted PostgreSQL database. Our data lives here permanently. |
| **PostgreSQL** | The actual database engine. Industry standard for production systems. |

### Dashboard and Visualization

| Technology | Why We Use It |
|---|---|
| **Streamlit** | Turns Python into a web app with zero HTML/CSS knowledge needed. |
| **Plotly** | Interactive charts used for the India map and the color-coded CPI bar chart. |

### Automation and DevOps

| Technology | Why We Use It |
|---|---|
| **GitHub Actions** | Free CI/CD cloud automation. Runs our scraper on Ubuntu servers 5 times per day for free. |
| **schedule** (Python library) | Local scheduling. Runs the pipeline on your laptop at specific times. |
| **python-dotenv** | Loads secret credentials from a .env file safely without hardcoding them. |

### APIs and Servers

| Technology | Why We Use It |
|---|---|
| **FastAPI** | High-performance Python web framework. Serves our mock airline API locally. |
| **Uvicorn** | The actual server that runs FastAPI. |

---

## 5. File-by-File Code Explanation

```
sih26056-collector/
|-- collector_tier1.py         <- Scraper: Google Flights (REAL DATA)
|-- collector_tier0_dgca.py    <- Scraper: DGCA government data (mock)
|-- collector_tier2_airline.py <- Scraper: Direct airline APIs (mock)
|-- cleaning.py                <- Stage 3: Remove bad data
|-- index_calc.py              <- Stage 4: Calculate CPI
|-- anomaly.py                 <- Stage 5: Detect price spikes
|-- dashboard.py               <- Stage 6: Web dashboard (Streamlit)
|-- api.py                     <- Local mock airline API server
|-- smart_scheduler.py         <- Local automation (runs pipeline on schedule)
|-- run_prototype.ps1          <- Master script: runs all stages in order
|-- config.py                  <- All settings in one place
|-- db.py                      <- Database connection manager
|-- storage.py                 <- Data model (defines a fare observation)
|-- schema.sql                 <- Database table definitions
|-- requirements.txt           <- List of all Python packages needed
|-- .env                       <- Secret credentials (NOT uploaded to GitHub)
|-- .github/
|   `-- workflows/
|       `-- smart_scraper.yml  <- GitHub Actions cloud automation
`-- docs/
    `-- PROTOTYPE_DOCUMENTATION.md  <- This file
```

### collector_tier1.py — The Main Scraper
- **What it does:** Queries Google Flights for economy class prices on 3 routes for 4 booking windows.
- **How:** Uses the fast-flights library which reads Google's internal binary data directly.
- **Important fix:** We explicitly set currency="INR" because GitHub US servers cause Google to return USD prices.
- **Output:** Writes raw fare rows to the fare_observations table in Supabase.

### cleaning.py — Data Quality Gate
- **Duplicate detection:** Same source, route, airline, and hour = duplicate. Keep only the first.
- **Outlier detection:** IQR method. Prices outside 1.5 times the normal range are flagged.
- **Key rule:** Data is NEVER deleted. Only flagged. The team can always see why a fare was excluded.
- **Output:** Writes all rows with is_duplicate and is_outlier columns to fare_observations_clean.

### index_calc.py — The CPI Engine
- **What it does:** Reads clean data and computes Airfare CPI for each route.
- **Formula:** CPI = 100 x (Current Average Price) / (Base Period Average Price)

### anomaly.py — The Alert System
- **Default method (Z-Score):** Rolling 10-observation window. If a price is more than 2.5 standard deviations above the rolling average, it fires a log alert.
- **Optional method (Isolation Forest):** Machine learning model that learns normal price patterns.
- **Demo mode:** Run with --inject-test-anomaly to simulate a 5x price spike in memory (not saved to DB).

### dashboard.py — The Web Interface
- **Section 1:** Interactive India map with glowing route lines, red city markers, bold city labels.
- **Section 2:** Fare trend line chart by booking window (3, 7, 14, 30 days ahead).
- **Section 3:** Raw data table of the 50 most recent observations.
- **Section 4:** CPI Calculator with route-level CPI, national weighted CPI, color-coded bar chart, and MoSPI comparison.

### smart_scheduler.py — The Local Alarm Clock
- Runs as a background daemon on your PC.
- When the scheduled time arrives, it calls run_prototype.ps1.
- Catch-up logic: Immediately runs the pipeline once when the script starts.
- Schedule: 03:55, 11:55, 18:55, 19:55, and 22:55 IST.

### .github/workflows/smart_scraper.yml — The Cloud Alarm Clock
- Runs the same pipeline on GitHub's free Ubuntu servers.
- Scheduled 30 minutes early to account for GitHub cron queue delays.
- Database password stored as a GitHub Secret and injected as an environment variable.

---

## 6. Complete Data Flow

```
Every Day (5 Times):
      |
      v
[smart_scheduler.py OR GitHub Actions cron]
      |
      | Triggers
      v
[run_prototype.ps1]
      |
      |-> [collector_tier1.py]
      |       Queries Google Flights for DEL->BOM, BOM->BLR, DEL->BLR
      |       For 4 booking windows: 3, 7, 14, 30 days
      |       Writes raw rows -> fare_observations (Supabase)
      |
      |-> [collector_tier0_dgca.py]
      |       Simulates DGCA government data source
      |       Writes mock data -> fare_observations (Supabase)
      |
      |-> [collector_tier2_airline.py]
      |       Hits local mock airline API (api.py)
      |       Writes mock data -> fare_observations (Supabase)
      |
      |-> [cleaning.py]
      |       Reads all raw rows from fare_observations
      |       Flags duplicates (same source+route+airline+hour)
      |       Flags outliers (IQR method per route+date group)
      |       Writes ALL rows with flags -> fare_observations_clean
      |
      |-> [index_calc.py]
      |       Reads only clean rows (is_duplicate=FALSE, is_outlier=FALSE)
      |       Computes CPI = 100 x (current avg) / (base period avg)
      |       Writes route-level index -> airfare_index (Supabase)
      |
      `-> [anomaly.py]
              Computes rolling Z-score per route
              Logs ALERT if Z-score > 2.5

              (All data now in Supabase)

[dashboard.py] - Reads live from Supabase on every page load
      |
      |-- Renders India map with route lines
      |-- Shows fare trend line chart
      |-- Shows recent observations table
      `-- Calculates and displays CPI in real time
```

---

## 7. The CPI Math

### Route-Level CPI (Single Route)
```
CPI = 100 x (Average Price Today) / (Average Price on Base Date)
```

**Example:**
- Base Date (Sept 1, 2026): Average DEL-BOM fare = Rs 5,000 -> CPI = 100
- Current (Sept 6, 2026): Average DEL-BOM fare = Rs 5,500
- CPI = 100 x 5500 / 5000 = 110
- Meaning: Prices are 10% higher than the base. INFLATION of 10%.

### National Airfare CPI (All Routes Combined)
We use a Passenger-Weighted Average. Routes with more observations have more weight.

```
National CPI = Sum(Route CPI x Number of Observations for that Route)
               -------------------------------------------------------
                         Total Observations Across All Routes
```

This is the same Laspeyres Index formula that India's official CPI uses. Our results are directly comparable to MoSPI's official numbers.

### Festival Spikes — Include or Exclude?
**INCLUDE.** A festival spike (e.g., prices jumping from Rs 7,000 to Rs 15,000 during Diwali) is REAL inflation. The consumer is actually paying that amount. CPI must reflect that burden on the consumer.

We only EXCLUDE data errors: glitches showing Rs 9,99,999 tickets, zero-rupee fares, or prices accidentally captured in USD.

---

## 8. Anomaly Detection

### What Is an Anomaly?
A price that is statistically far from the recent average. It could be a real market event (festival, strike, budget fare sale) or a data bug (scraper error, website glitch). We alert a human to investigate.

### How Z-Score Detection Works
```
For each route, every time a new price comes in:
  1. Calculate Rolling Average of the last 10 prices
  2. Calculate Rolling Standard Deviation of the last 10 prices
  3. Z-Score = (New Price - Rolling Average) / Standard Deviation
  4. If |Z-Score| > 2.5 -> Fire an ALERT in the logs
```

A Z-Score of 2.5 means there is roughly a 1.2% chance the spike is random. In plain language: something unusual is very likely happening.

### Isolation Forest (Advanced, Optional)
A machine learning model trained on historical price patterns. Learns what "normal" looks like and gives each price an anomaly score. Scores near -1 are highly anomalous. Requires at least 100+ data points to be reliable.

---

## 9. Automation

### Dual Automation Architecture

| | Local (Your PC) | Cloud (GitHub Actions) |
|---|---|---|
| **Script** | smart_scheduler.py | smart_scraper.yml |
| **Runs on** | Your Windows laptop | Ubuntu server in US data center |
| **Runs if PC is off?** | NO | YES |
| **Cost** | Free | Free (GitHub free tier) |
| **Schedule** | 03:55, 11:55, 18:55, 19:55, 22:55 IST | 30 minutes earlier to beat queue delays |

### Why Start 5 or 30 Minutes Early?
- **Local (5 min early):** The scraper takes ~5 minutes. Starting at 03:55 means data is in the database by 04:00.
- **Cloud (30 min early):** GitHub's free-tier cron shares servers with millions of developers. Jobs can be delayed 15-30 minutes. Starting at 03:30 ensures data arrives by 04:00.

---

## 10. Dashboard

The Streamlit dashboard is publicly deployed and accessible from any device with a browser.

### Section 1: Interactive India Route Map
- Full OpenStreetMap base layer of India
- Active flight routes shown as glowing cyan lines
- Airport cities shown as red dot markers with bold black city name labels
- Hovering over a route line shows: Route name + Current average fare

### Section 2: Fare Trend Chart
- User selects any route from a dropdown
- Line chart: average price vs booking window (3, 7, 14, 30 days ahead)
- Answers: "Is it cheaper to book 30 days early or 3 days before the flight?"

### Section 3: Observations Table
- Last 50 raw fare observations
- Shows: time, route, data source, airline, price, booking window

### Section 4: CPI Calculator
**Route-Level:**
- Pick any route, see its CPI and the full formula breakdown step-by-step
- Red alert if inflation, green alert if deflation

**National Level:**
- Weighted average CPI across all routes
- Color-coded bar chart (green = below base, red = above base)
- White dashed line at CPI = 100 (base reference)
- Live comparison against MoSPI's official published airfare benchmark

---

## 11. What Results the Prototype Provides

The prototype answers 5 key questions in real time:

1. **"Is airfare in India getting more expensive right now?"**
   -> National Airfare CPI with inflation/deflation signal

2. **"Which specific routes have the most inflation?"**
   -> Route-level CPI bar chart, color coded from green to red

3. **"What does our live data say vs the government's official data?"**
   -> Side-by-side comparison with MoSPI benchmark

4. **"Are there any suspicious price spikes I should investigate?"**
   -> Anomaly detection alerts in the logs

5. **"Is it cheaper to book early or late for a specific route?"**
   -> Booking window vs price line chart

---

## 12. Recommended Scraping Times

| Time (IST) | Why This Time Is Good |
|---|---|
| **04:00 AM** | Airlines run overnight pricing algorithms between 2-4 AM. By 4 AM, new prices are live. Best "morning snapshot." |
| **12:00 PM (Noon)** | Midday repricing. Airlines adjust prices mid-morning based on booking pace. Noon captures post-adjustment. |
| **07:00 PM** | Peak evening. Maximum consumers browsing after work. Prices are often highest. Critical to capture. |
| **08:00 PM** | Second evening check. Some airlines run a secondary update at 7-8 PM. 30-min gap catches both. |
| **11:00 PM** | Late night clearance. Airlines sometimes slash prices on unsold seats before midnight system reset. |

### General Rules
- **Avoid 2:00 AM to 3:30 AM IST.** Airlines are mid-recalculation. Prices may be transitional and incomplete.
- **Best single time:** 7:00 PM IST. Peak pricing, maximum consumer activity, most representative of what the average traveler actually pays.

---

## 13. Important Problems We Faced

### Problem 1: USD vs INR Currency Bug [CRITICAL]

**What happened:** All prices stored in the database were 2-digit numbers (e.g., 93, 89, 100) instead of thousands of rupees. The CPI was completely wrong.

**Root Cause:** GitHub Actions runs on servers in the United States. When fast-flights queries Google Flights without specifying a currency, Google detects the US IP address and returns prices in USD (e.g., $93). Our code was saving this as "93 INR", corrupting every CPI calculation.

**Scale of damage:** Approximately 8,600 corrupt rows were written to the database before the bug was caught.

**Fix Applied:** Added currency="INR" explicitly to the create_query() call in collector_tier1.py. Deleted all ~8,600 corrupt rows from the Supabase database.

**Lesson:** Always explicitly specify currency when scraping from code that runs on cloud servers in foreign countries.

---

### Problem 2: Plotly Version Deprecation [MEDIUM]

**What happened:** The dashboard would crash with "AttributeError: Scattermapbox" errors immediately on startup.

**Root Cause:** Plotly 7.0 completely removed the old Scattermapbox class and mapbox layout property. They were renamed to Scattermap and map respectively. Code written for Plotly 5.x/6.x crashed on Plotly 7.x.

**Fix Applied:** Rewrote all map rendering code in dashboard.py to use the new Plotly 7.0 API. Also switched from Mapbox satellite tiles to OpenStreetMap bright tiles (looks better and does not require an API key).

**Lesson:** Always check the library's changelog before upgrading major versions.

---

### Problem 3: New Schedule Times Not Loading [MEDIUM]

**What happened:** After adding 8 PM and 11 PM scraping times to the code, those times were never triggering.

**Root Cause:** The smart_scheduler.py process was already running in the background from before the code change. Python background processes do not auto-reload when source code changes. They keep running the old code that was loaded at startup.

**Fix Applied:** Kill the old scheduler process and restart it whenever smart_scheduler.py is modified.

**Lesson:** Any time you change a scheduler script, always restart the running process to load the new code.

---

### Problem 4: GitHub Actions Cron Delay [MEDIUM]

**What happened:** The 8 PM scrape was showing data at 8:22 PM instead of 8:00 PM.

**Root Cause:** GitHub's free-tier cron uses a shared queue. On busy days, jobs can be delayed 15-30 minutes because thousands of other developers' jobs are waiting ahead in the same queue.

**Fix Applied:** Moved all GitHub Actions cron times 30 minutes earlier. The scraper now starts at 7:30 PM so even with a 15-minute delay, data is processed and in the database by 8:00 PM.

**Lesson:** GitHub Actions free-tier cron is not suitable for exact-second scheduling. Always build in a buffer of at least 30 minutes.

---

### Problem 5: Deployed App Not Visible to Teammates [MINOR]

**What happened:** Team members and the judge got the message "You do not have access to this app or it does not exist."

**Root Cause:** When a private GitHub repository is connected to Streamlit Community Cloud, the deployed app is automatically set to "Private" visibility. Only the repository owner can see it by default.

**Fix Applied:** Changed the app's visibility to "Public" in Streamlit's Sharing settings. The GitHub code remains private; only the web dashboard URL is made public.

**Lesson:** After deploying to Streamlit, always verify the app visibility setting and test the link from an incognito window.

---

*Document prepared by the SIH26056 development team. Last updated: September 2026.*
