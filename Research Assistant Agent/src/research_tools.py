"""
research_tools.py  –  Tool functions compatible with Google ADK.

Each function has a proper Google-style docstring (ADK reads them as the
tool description and parameter descriptions automatically).
"""

from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()


# ---------------------------------------------------------------------------
# Shared HTTP session
# ---------------------------------------------------------------------------

def _build_session(
    user_agent: str = "ResearchAgent/1.0 (mailto:your.email@example.com)",
) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent, "Accept": "*/*"})
    retry = Retry(
        total=5, connect=5, read=5, backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


_session = _build_session()


# ---------------------------------------------------------------------------
# PDF helpers (internal)
# ---------------------------------------------------------------------------

def _ensure_pdf_url(url: str) -> str:
    url = url.strip().replace("http://", "https://")
    url = url.replace("/abs/", "/pdf/")
    if not url.endswith(".pdf"):
        url += ".pdf"
    return url


def _clean_text(s: str) -> str:
    s = re.sub(r"-\n", "", s)
    s = re.sub(r"\r\n|\r", "\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _pdf_bytes_to_text(pdf_bytes: bytes, max_pages: Optional[int] = None) -> str:
    try:
        import fitz  # type: ignore  # PyMuPDF
        out: List[str] = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            limit = len(doc) if max_pages is None else min(max_pages, len(doc))
            for i in range(limit):
                out.append(doc.load_page(i).get_text("text"))
        return "\n".join(out)
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text_to_fp  # type: ignore
        buf_in, buf_out = BytesIO(pdf_bytes), BytesIO()
        extract_text_to_fp(buf_in, buf_out)
        return buf_out.getvalue().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"PDF text extraction failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def arxiv_search_tool(query: str, max_results: int = 3) -> List[Dict]:
    """Search arXiv for academic papers and return extracted text from their PDFs.

    Args:
        query: Keywords to search for on arXiv.
        max_results: Maximum number of papers to return.

    Returns:
        List of dicts with keys: title, authors, published, url, summary, link_pdf.
        On failure returns a single-item list with an 'error' key.
    """
    api_url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=all:{requests.utils.quote(query)}&start=0&max_results={max_results}"
    )
    try:
        resp = _session.get(api_url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return [{"error": f"arXiv request failed: {exc}"}]

    out: List[Dict] = []
    try:
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:10]
            url_abs = entry.findtext("atom:id", default="", namespaces=ns) or ""
            abstract = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            authors = [
                a.findtext("atom:name", default="", namespaces=ns)
                for a in entry.findall("atom:author", ns)
                if a.findtext("atom:name", namespaces=ns)
            ]
            link_pdf: Optional[str] = next(
                (lnk.attrib.get("href") for lnk in entry.findall("atom:link", ns)
                 if lnk.attrib.get("title") == "pdf"), None
            ) or (_ensure_pdf_url(url_abs) if url_abs else None)

            item: Dict = {
                "title": title, "authors": authors, "published": published,
                "url": url_abs, "summary": abstract, "link_pdf": link_pdf,
            }
            if link_pdf:
                try:
                    pdf_bytes = _session.get(link_pdf, timeout=90, allow_redirects=True).content
                    time.sleep(1.0)
                    text = _pdf_bytes_to_text(pdf_bytes, max_pages=6)
                    if text:
                        item["summary"] = _clean_text(text)[:5000]
                except Exception as exc:
                    item["pdf_error"] = str(exc)
            out.append(item)
        return out
    except ET.ParseError as exc:
        return [{"error": f"arXiv XML parse error: {exc}"}]
    except Exception as exc:
        return [{"error": f"Unexpected error: {exc}"}]


def tavily_search_tool(
    query: str,
    max_results: int = 5,
    include_images: bool = False,
) -> List[Dict]:
    """Perform a general web search using the Tavily API.

    Args:
        query: Search keywords.
        max_results: Number of results to return.
        include_images: Whether to include image URLs in results.

    Returns:
        List of dicts with keys: title, content, url.
        On failure returns a single-item list with an 'error' key.
    """
    from tavily import TavilyClient  # type: ignore

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [{"error": "TAVILY_API_KEY not set in environment."}]

    base_url = os.getenv("DLAI_TAVILY_BASE_URL")
    client = TavilyClient(api_key, **({"api_base_url": base_url} if base_url else {}))
    try:
        response = client.search(query=query, max_results=max_results, include_images=include_images)
        results: List[Dict] = [
            {"title": r.get("title", ""), "content": r.get("content", ""), "url": r.get("url", "")}
            for r in response.get("results", [])
        ]
        if include_images:
            results += [{"image_url": img} for img in response.get("images", [])]
        return results
    except Exception as exc:
        return [{"error": str(exc)}]


def wikipedia_search_tool(query: str, sentences: int = 5) -> List[Dict]:
    """Search Wikipedia and return a brief summary for the query.

    Args:
        query: Keywords to look up on Wikipedia.
        sentences: Number of sentences to include in the summary.

    Returns:
        Single-item list with keys: title, summary, url.
        On failure returns a single-item list with an 'error' key.
    """
    import wikipedia  # type: ignore

    try:
        page_title = wikipedia.search(query)[0]
        page = wikipedia.page(page_title)
        summary = wikipedia.summary(page_title, sentences=sentences)
        return [{"title": page.title, "summary": summary, "url": page.url}]
    except Exception as exc:
        return [{"error": str(exc)}]


# Convenience export
TOOL_FUNCTIONS = [arxiv_search_tool, tavily_search_tool, wikipedia_search_tool]
