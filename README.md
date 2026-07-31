# AutoValuate

Live Demo: https://autovaluate.netlify.app

AutoValuate is an end-to-end machine learning application that scrapes live used car listings, predicts their true market value using XGBoost, and highlights underpriced deals in real-time.

Instead of relying on static, pre-cleaned datasets, AutoValuate features a custom-built web scraper that extracts real-time data from Craigslist. It processes messy HTML using BeautifulSoup and custom NLP logic, feeds it into a trained regression model, and serves it through a React frontend to find arbitrage opportunities for buyers.

## Tech Stack
* **Backend:** Python, FastAPI, Uvicorn
* **Machine Learning:** XGBoost, Scikit-Learn, Pandas, NumPy, Seaborn, Matplotlib
* **Web Scraping:** Playwright, BeautifulSoup
* **Frontend:** React, Vite, Tailwind CSS, Framer Motion
* **Deployment:** Docker, Render (Backend), Netlify (Frontend)

## Architecture and Pipeline

**1. Data Ingestion:**
A custom Playwright scraper bypasses anti-bot protections and infinite-scroll limitations to extract live listings from Craigslist. Instead of standard pagination, the scraper simulates physical mouse wheel scrolling to trigger the site's virtual DOM, successfully capturing over 2,000 live listings.

**2. Data Processing:**
Raw listing titles (e.g., "2014 Audi A7 Prestige Quattro") are parsed using Regex and custom dictionary-based NLP. The pipeline extracts and structures the Year, Make, and Model, while filtering out extreme price and mileage outliers to ensure dataset integrity.

**3. Model Training:**
An XGBoost Regressor is trained on the cleaned dataset. The model evaluates features including age, mileage, make, model, and location to predict fair market value. It achieves a Mean Absolute Error (MAE) of approximately $3,000. The trained model and One-Hot Encoder are exported as artifacts.

**4. Live Inference API:**
A FastAPI backend serves the trained model. Users can paste a live Craigslist URL into the frontend. The backend uses Playwright to scrape that specific posting in real-time, cleans the extracted text, and runs it through the ML model to determine if the car is a "Steal" or "Overpriced".

## Features
* **Live URL Valuation:** Paste any Craigslist URL to get an instant AI valuation and deal verdict.
* **Market Feed:** A dashboard of live listings automatically evaluated by the AI, displaying the listed price versus the predicted market value.
* **Sleek UI:** Built with Tailwind CSS and Framer Motion for a premium, responsive user experience.

## V2 Roadmap (Work in Progress)

AutoValuate is currently a functional V1 MVP. The following features and improvements are planned for V2:

* **Multi-City Data Expansion:** Expanding the scraper to cover multiple major US markets (New York, Los Angeles, Chicago, Seattle) to increase the dataset from 2,000 to over 100,000 records.
* **PostgreSQL Database Integration:** Transitioning from a static CSV to a live database. A cron job will run the scraper hourly to ingest new listings and automatically delete listings older than 30 days to keep the market feed current and fast.
* **Advanced NLP for Trim Extraction:** Implementing spaCy or an LLM API to accurately extract specific vehicle trims (e.g., distinguishing a base model Civic from a Civic EX-L) to further reduce the MAE and increase prediction accuracy.
* **Market Insights Dashboard:** Building out the Insights page with interactive charts (Recharts) showing depreciation curves by make and the impact of mileage on price.
* **User Accounts and Watchlists:** Adding authentication so users can save specific cars to a personal watchlist to track price changes over time.
* **Listing Image Integration:** Updating the scraper to capture the actual photos from Craigslist postings and using them as the background for the glassmorphism cards in the Market Feed.
