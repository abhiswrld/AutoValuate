# AutoValuate

**Live Demo:** [autovaluate.netlify.app](https://autovaluate.netlify.app)

AutoValuate is an end-to-end machine learning application that scrapes live used car listings, predicts their true market value using XGBoost, and highlights underpriced deals in real-time.

Instead of relying on static, pre-cleaned datasets, AutoValuate features a custom-built web scraper that extracts real-time data from Craigslist. It processes messy HTML using BeautifulSoup and custom NLP logic, feeds it into a trained regression model, and serves it through a React frontend to find arbitrage opportunities for buyers.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Machine Learning:** XGBoost, Scikit-Learn, Pandas, NumPy, Seaborn, Matplotlib
- **Web Scraping:** Playwright, BeautifulSoup
- **Frontend:** React, Vite, Tailwind CSS, Framer Motion
- **DevOps & Deployment:** Docker, GitHub Actions (CI/CD), Render (Backend), Netlify (Frontend)

## Architecture and Pipeline

1. **Data Ingestion** — A custom Playwright scraper bypasses anti-bot protections and infinite-scroll limitations to extract live listings from Craigslist. Instead of standard pagination, the scraper simulates physical mouse wheel scrolling to trigger the site's virtual DOM. It currently runs on an automated daily CI/CD schedule across 10 major US markets, successfully capturing over 15,000 live listings and growing.

2. **Data Processing** — Raw listing titles (e.g., "2014 Audi A7 Prestige Quattro") are parsed using Regex and custom dictionary-based NLP. The pipeline extracts and structures the Year, Make, and Model, while filtering out extreme price and mileage outliers to ensure dataset integrity.

3. **Model Training** — An XGBoost Regressor is trained on the cleaned dataset. The model evaluates features including age, mileage, make, model, and location to predict fair market value. It currently achieves an R-Squared of 0.69 and a Mean Absolute Error (MAE) of approximately $3,100. The trained model and One-Hot Encoder are exported as .pkl artifacts.

4. **Live Inference API** — A FastAPI backend serves the trained model. Users can paste a live Craigslist URL into the frontend. The backend uses Playwright to scrape that specific posting in real-time, cleans the extracted text, and runs it through the ML model to determine if the car is a "Steal" or "Overpriced".

## Features

- **Live URL Valuation:** Paste any Craigslist URL to get an instant AI valuation and deal verdict.
- **Nationwide Market Feed:** A dashboard of live listings automatically evaluated by the AI, displaying the listed price versus the predicted market value across major US cities.
- **Sleek UI:** Built with Tailwind CSS and Framer Motion for a premium, responsive user experience.

## V2 Roadmap (Completed)

AutoValuate has successfully implemented all V2 milestones, transforming the platform into a full-scale, production-ready application:

### Infrastructure & MLOps

- [x] ~~**PostgreSQL Database Integration:** Transitioning from static CSVs to a live cloud database to enable lightning-fast queries and handle 100,000+ records.~~
- [x] ~~**Automated ETL Pipeline:** Expanding the GitHub Actions CI/CD to automatically run the scraper, clean the data, and load it into the database daily without manual intervention.~~
- [x] ~~**Asynchronous Background Tasks:** Implementing FastAPI BackgroundTasks so live URL evaluations return a ticket instantly, preventing the UI from freezing during heavy Playwright scraping.~~

### Accuracy & Data Depth

- [x] ~~**Deep Scraping (Condition & Title Status):** Building a secondary scraper to visit individual listing URLs and extract crucial attributes (Clean/Salvage Title, Condition, Transmission) to feed into XGBoost, aiming to reduce MAE to under $1,500.~~
- [X] ~~**Advanced NLP / LLM Integration:** Replacing the hardcoded Make/Model dictionary with a smarter approach using spaCy (Named Entity Recognition) or an LLM API to automatically extract Make, Model, and Trim (e.g., distinguishing a base model Civic from a Civic EX-L) without manual database maintenance.~~

### User Experience & Personalization

- [x] ~~**User Authentication:** Adding Google OAuth and Email/Password login so users have personalized profiles.~~
- [x] ~~**Watchlists & Alerts:** Allowing authenticated users to save specific cars to a personal watchlist to track price changes over time.~~
- [x] ~~**City Filtering:** Enabling users to select their preferred city/region to dynamically filter the Market Feed.~~

### Data Visualization

- [x] ~~**Market Insights Dashboard:** Building out the Insights page with interactive charts (Recharts) showing price depreciation curves by make/model and the visual impact of mileage on price.~~
- [x] ~~**Listing Image Integration:** Updating the scraper to capture the actual photos from Craigslist postings and using them as the background for the glassmorphism cards in the Market Feed.~~
## V3 Roadmap (Planned)

AutoValuate is continuously evolving. The following features are currently in active development for the upcoming V3 release:

### Real-Time Alerts & Notifications
- [ ] **Watchlist Price Drops:** Implement a background CRON job to track price drops on saved cars and send automated email alerts to users.

### Community Moderation & Data Quality
- [x] ~~**Automated Dead Link Sweeping:** Implement a continuous background worker that verifies and purges sold/deleted Craigslist listings from the database to keep the feed pristine.~~
- [x] ~~**Crowdsourced Reporting:** Allow authenticated users to flag dead listings directly from the UI.~~

### Advanced AI Integration
- [ ] **Conversational RAG Agent:** A natural language AI assistant that helps users find the perfect car with a chill, human-like personality. Users can ask queries like "reliable car near Cupertino under 20k", and the agent will use Retrieval-Augmented Generation to search the live database and recommend specific active listings. The bot will also proactively send out email alerts if new cars pop up that match a user's saved collection or specific requests.
- [ ] **Computer Vision Valuation:** Use image recognition models to evaluate car condition directly from listing photos (e.g., detecting body damage or interior wear) to adjust the predicted price dynamically.
- [ ] **VIN Decoder API:** Allow users to input a VIN to automatically fetch precise trim specs, original MSRP, and recall history.
