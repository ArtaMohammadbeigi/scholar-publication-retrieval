# services/retrieval.py

import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.preprocess import preprocess_text

logger = logging.getLogger(__name__)

TOP_N = 5
CITATION_COVERAGE_THRESHOLD = 0.9  # 90%


def _parse_citation_count(cited_by) -> int | None:
    """
    Parse a citation count value into an int, or None if missing/unparseable.
    """
    if cited_by is None:
        return None
    if isinstance(cited_by, int):
        return cited_by
    cited_by = str(cited_by).strip()
    if not cited_by:
        return None
    try:
        return int(cited_by)
    except ValueError:
        return None


def _citation_coverage(publications: list[dict]) -> float:
    """
    Compute the fraction of publications that have a parsable citation count.
    """
    if not publications:
        return 0.0
    with_citations = sum(
        1 for p in publications
        if _parse_citation_count(p.get("cited_by", "")) is not None
    )
    return with_citations / len(publications)


def rank_publications(publications: list[dict], query: str, top_n: int = TOP_N) -> tuple[list[dict], float]:
    """
    Rank publications against the query using TF-IDF + cosine similarity.

    Ranking is always based purely on cosine similarity between the query
    and each publication's (title + description). Citation data is never
    used to affect the score. Citation coverage is only used to decide
    whether publications lacking citation data should be filtered out:

      - If >= 90% of publications have citation data, publications without
        citation data are removed before ranking.
      - If < 90% of publications have citation data, all publications are
        kept and ranked regardless of citation data.

    Args:
        publications: list of dicts with keys 'title', 'link', 'description', 'cited_by'.
        query: the search query string.
        top_n: number of top results to return.

    Returns:
        tuple:
            list[dict]: each with rank, title, similarity_score, citation_count, link.
            float: the fraction of publications that had a parsable citation count.
    """
    if not publications:
        logger.warning("rank_publications called with empty publication list.")
        return [], 0.0

    # --- Preprocess texts ---
    combined_texts = [
        preprocess_text(f"{pub.get('title', '')} {pub.get('description', '')}")
        for pub in publications
    ]
    processed_query = preprocess_text(query)

    # --- TF-IDF + cosine similarity ---
    corpus = [processed_query] + combined_texts
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)

    query_vector = tfidf_matrix[0:1]
    pub_vectors = tfidf_matrix[1:]

    similarities = cosine_similarity(query_vector, pub_vectors).flatten()

    for pub, score in zip(publications, similarities):
        pub["_similarity_score"] = float(score)
        pub["_citation_count"] = _parse_citation_count(pub.get("cited_by", ""))

    # --- Citation coverage filtering ---
    coverage = _citation_coverage(publications)
    logger.info(f"Citation coverage: {coverage:.2%}")

    if coverage >= CITATION_COVERAGE_THRESHOLD:
        filtered = [p for p in publications if p["_citation_count"] is not None]
        logger.info(
            f"Coverage >= {CITATION_COVERAGE_THRESHOLD:.0%}: filtering out "
            f"{len(publications) - len(filtered)} publications without citations."
        )
    else:
        filtered = publications
        logger.info(
            f"Coverage < {CITATION_COVERAGE_THRESHOLD:.0%}: keeping all publications."
        )

    # --- Sort and take top N ---
    ranked = sorted(filtered, key=lambda p: p["_similarity_score"], reverse=True)[:top_n]

    results = []
    for i, pub in enumerate(ranked, start=1):
        results.append({
            "rank": i,
            "title": pub.get("title", ""),
            "similarity_score": round(pub["_similarity_score"], 4),
            "citation_count": pub["_citation_count"] if pub["_citation_count"] is not None else "N/A",
            "link": pub.get("link", "")
        })

    logger.info(f"Returning top {len(results)} ranked publications.")
    return results, coverage
