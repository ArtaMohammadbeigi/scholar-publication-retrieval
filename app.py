# app.py

import logging
from logging.handlers import RotatingFileHandler
import os

from flask import Flask, render_template, request

from services.scholar_scraper import (
    scrape_professor_publications,
    ScraperError,
    ProfileNotFoundError,
    NoPublicationsError,
)
from services.retrieval import rank_publications

# --- Logging setup ---
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
console_handler.setFormatter(console_formatter)

file_handler = RotatingFileHandler(
    "logs/app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(console_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# --- Flask app ---
app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    professor_name = request.form.get("professor_name", "").strip()
    query = request.form.get("query", "").strip()

    if not professor_name or not query:
        return render_template(
            "index.html",
            error="Please provide both a professor name and a search query."
        )

    logger.info(f"Search requested: professor='{professor_name}', query='{query}'")

    try:
        publications = scrape_professor_publications(professor_name)
    except ProfileNotFoundError:
        logger.warning(f"Profile not found for professor: {professor_name}")
        return render_template(
            "index.html",
            error=f"Could not find a Google Scholar profile for '{professor_name}'. "
                  f"Please check the name and try again."
        )
    except NoPublicationsError:
        logger.warning(f"No publications found for professor: {professor_name}")
        return render_template(
            "index.html",
            error=f"No publications were found for '{professor_name}'."
        )
    except ScraperError as e:
        logger.error(f"Scraper error: {e}")
        return render_template(
            "index.html",
            error="An error occurred while scraping Google Scholar. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Unexpected error during scraping: {e}")
        return render_template(
            "index.html",
            error="An unexpected error occurred. Please try again later."
        )

    total_scraped = len(publications)

    try:
        results, citation_coverage = rank_publications(publications, query, top_n=5)
    except Exception as e:
        logger.exception(f"Unexpected error during ranking: {e}")
        return render_template(
            "index.html",
            error="An unexpected error occurred while ranking publications."
        )

    return render_template(
        "results.html",
        professor_name=professor_name,
        query=query,
        results=results,
        citation_coverage=citation_coverage,
        total_scraped=total_scraped,
    )


if __name__ == "__main__":
    app.run(debug=True)
