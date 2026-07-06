# README.md

# Scholar Publication Retrieval

A simple Flask web application for a university Information Retrieval assignment.
It scrapes a professor's Google Scholar publications, computes TF-IDF-based
cosine similarity against a user query, and returns the top 5 most relevant
publications.

## Features

- Scrapes Google Scholar profile pages using Selenium.
- Extracts publication `title`, `link`, `description`, and `cited_by`.
- Preprocesses text (lowercasing, punctuation removal, stopword removal).
- Computes TF-IDF vectors and cosine similarity between query and publications.
- Applies conditional citation-based filtering (does not affect ranking score):
  - If ≥ 90% of publications have citation data, publications without it are filtered out.
  - Otherwise, all publications are kept.
- Displays top 5 results with rank, title, similarity score, citation count, and link.
- Logs to both console and `logs/app.log`.

## Project Structure

├── app.py              # Main Flask application entry point
├── services/           # Backend logic
│   ├── scholar_scraper.py # Selenium-based Google Scholar scraper
│   ├── preprocess.py      # Text cleaning and NLP preprocessing
│   └── retrieval.py       # TF-IDF, cosine similarity, and ranking logic
├── templates/          # HTML files
│   ├── index.html      # Search homepage
│   └── results.html    # Search results display
├── static/             # CSS and styling
│   └── style.css
├── logs/               # Application logs
│   └── app.log
└── requirements.txt    # Project dependencies 


## Setup
1. Create and activate a virtual environment:
bash

python -m venv venv

source venv/bin/activate # on Windows: venv\Scripts\activate

2. Install dependencies:
bash

pip install -r requirements.txt

3. Download NLTK stopwords (done automatically on first run, but can be run manually):
python

python -c “import nltk; nltk.download(‘stopwords’)”

4. Make sure Google Chrome is installed. ChromeDriver is managed automaticallyvia webdriver-manager.
## Running the App
bash

python app.py

Then open http://127.0.0.1:5000 in your browser.

## Usage
1. Enter a professor’s name (as it would be searched on Google Scholar) and asearch query.
2. Submit the form. A Chrome browser window will open to perform the scrape.
3. Important: If Google Scholar shows a CAPTCHA, solve it manually in theopened browser window, then press Enter in the terminal to continue.
4. Results will display the top 5 publications ranked by cosine similarity,along with citation counts (if available) and links.
## Known Limitations
- CAPTCHAs: Google Scholar may present CAPTCHAs. Since the scraper runsin non-headless mode, you must solve them manually in the browser windowwhen prompted in the terminal.
- Rate Limiting / IP Bans: Frequent or rapid scraping may lead totemporary blocking by Google Scholar.
- HTML Structure Changes: The scraper relies on Google Scholar’s currentHTML structure; changes to the site may break selectors.
- Non-headless Browser Requirement: A visible browser window is requiredfor manual CAPTCHA solving.
## Notes on Ranking Logic
- Relevance ranking is always based solely on cosine similarity betweenthe query and each publication’s combined title + description text.
- Citation count is only used to decide whether to filter outpublications missing citation data (when coverage is high), and isdisplayed for informational purposes. It never influences the similarityscore itself.
## Tech Stack
- Python 3
- Flask
- Selenium
- scikit-learn (TF-IDF, cosine similarity)
- NLTK (stopwords)
- Standard Python logging
