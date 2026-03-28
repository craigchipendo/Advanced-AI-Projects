"""
research_tools.py  –  Tool functions compatible with Google ADK.

Ported from the reference implementation. Each public function keeps
Google-style docstrings (ADK reads them as tool descriptions automatically).
Tool defs and tool_mapping are also exported for direct use if needed.
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
    user_agent: str = "LF-ADP-Agent/1.0 (mailto:your.email@example.com)",
) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    )
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_redirect=False,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


session = _build_session()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def ensure_pdf_url(abs_or_pdf_url: str) -> str:
    url = abs_or_pdf_url.strip().replace("http://", "https://")
    if "/pdf/" in url and url.endswith(".pdf"):
        return url
    url = url.replace("/abs/", "/pdf/")
    if not url.endswith(".pdf"):
        url += ".pdf"
    return url


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def clean_text(s: str) -> str:
    s = re.sub(r"-\n", "", s)          # "transfor-\nmers" -> "transformers"
    s = re.sub(r"\r\n|\r", "\n", s)    # normalise line endings
    s = re.sub(r"[ \t]+", " ", s)      # collapse spaces
    s = re.sub(r"\n{3,}", "\n\n", s)   # max one blank line
    return s.strip()


def fetch_pdf_bytes(pdf_url: str, timeout: int = 90) -> bytes:
    r = session.get(pdf_url, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r.content


def pdf_bytes_to_text(pdf_bytes: bytes, max_pages: Optional[int] = None) -> str:
    # 1) PyMuPDF
    try:
        import fitz  # type: ignore  # PyMuPDF
        out = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            n = len(doc)
            limit = n if max_pages is None else min(max_pages, n)
            for i in range(limit):
                out.append(doc.load_page(i).get_text("text"))
        return "\n".join(out)
    except Exception:
        pass

    # 2) pdfminer.six
    try:
        from pdfminer.high_level import extract_text_to_fp  # type: ignore
        buf_in = BytesIO(pdf_bytes)
        buf_out = BytesIO()
        extract_text_to_fp(buf_in, buf_out)
        return buf_out.getvalue().decode("utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"PDF text extraction failed: {e}")


def maybe_save_pdf(pdf_bytes: bytes, dest_dir: str, filename: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, _safe_filename(filename))
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


# ---------------------------------------------------------------------------
# arXiv search tool
# ---------------------------------------------------------------------------

def arxiv_search_tool(
    query: str,
    max_results: int = 3,
) -> List[Dict]:
    """Search arXiv for academic papers and return extracted text from their PDFs.

    Args:
        query: Keywords to search for on arXiv.
        max_results: Maximum number of papers to return.

    Returns:
        List of dicts with keys: title, authors, published, url, summary, link_pdf.
        On failure returns a single-item list with an 'error' key.
    """
    # Internal flags
    _INCLUDE_PDF    = True
    _EXTRACT_TEXT   = True
    _MAX_PAGES      = 6
    _TEXT_CHARS     = 5000
    _SAVE_FULL_TEXT = False
    _SLEEP_SECONDS  = 1.0

    api_url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=all:{requests.utils.quote(query)}"
        f"&start=0&max_results={max_results}"
    )

    out: List[Dict] = []
    try:
        resp = session.get(api_url, timeout=60)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return [{"error": f"arXiv API request failed: {e}"}]

    try:
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:10]
            url_abs = entry.findtext("atom:id", default="", namespaces=ns) or ""
            abstract_summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()

            authors = []
            for a in entry.findall("atom:author", ns):
                nm = a.findtext("atom:name", default="", namespaces=ns)
                if nm:
                    authors.append(nm)

            link_pdf = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf":
                    link_pdf = link.attrib.get("href")
                    break
            if not link_pdf and url_abs:
                link_pdf = ensure_pdf_url(url_abs)

            item: Dict = {
                "title": title,
                "authors": authors,
                "published": published,
                "url": url_abs,
                "summary": abstract_summary,
                "link_pdf": link_pdf,
            }

            pdf_bytes = None
            if (_INCLUDE_PDF or _EXTRACT_TEXT) and link_pdf:
                try:
                    pdf_bytes = fetch_pdf_bytes(link_pdf, timeout=90)
                    time.sleep(_SLEEP_SECONDS)
                except Exception as e:
                    item["pdf_error"] = f"PDF fetch failed: {e}"

            if _EXTRACT_TEXT and pdf_bytes:
                try:
                    text = pdf_bytes_to_text(pdf_bytes, max_pages=_MAX_PAGES)
                    text = clean_text(text) if text else ""
                    if text:
                        item["summary"] = text if _SAVE_FULL_TEXT else text[:_TEXT_CHARS]
                except Exception as e:
                    item["text_error"] = f"Text extraction failed: {e}"

            out.append(item)
        return out

    except ET.ParseError as e:
        return [{"error": f"arXiv API XML parse failed: {e}"}]
    except Exception as e:
        return [{"error": f"Unexpected error: {e}"}]


arxiv_tool_def = {
    "type": "function",
    "function": {
        "name": "arxiv_search_tool",
        "description": "Searches arXiv and (internally) fetches PDFs to memory and extracts text.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords."},
                "max_results": {"type": "integer", "default": 3},
            },
            "required": ["query"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tavily search tool
# ---------------------------------------------------------------------------

def tavily_search_tool(
    query: str,
    max_results: int = 5,
    include_images: bool = False,
) -> List[Dict]:
    """Perform a general web search using the Tavily API.

    Args:
        query: The search query.
        max_results: Number of results to return (default 5).
        include_images: Whether to include image results.

    Returns:
        List of dicts with keys: title, content, url.
        On failure returns a single-item list with an 'error' key.
    """
    from tavily import TavilyClient  # type: ignore

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [{"error": "TAVILY_API_KEY not found in environment variables."}]

    client = TavilyClient(api_key, api_base_url=os.getenv("DLAI_TAVILY_BASE_URL"))

    try:
        response = client.search(
            query=query,
            max_results=max_results,
            include_images=include_images,
        )

        results: List[Dict] = []
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                }
            )

        if include_images:
            for img_url in response.get("images", []):
                results.append({"image_url": img_url})

        return results

    except Exception as e:
        return [{"error": str(e)}]


tavily_tool_def = {
    "type": "function",
    "function": {
        "name": "tavily_search_tool",
        "description": "Performs a general-purpose web search using the Tavily API.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for retrieving information from the web.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image results.",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
}


# ---------------------------------------------------------------------------
# Wikipedia search tool
# ---------------------------------------------------------------------------

def wikipedia_search_tool(query: str, sentences: int = 5) -> List[Dict]:
    """Search Wikipedia and return a brief summary for the query.

    Args:
        query: Search query for Wikipedia.
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
    except Exception as e:
        return [{"error": str(e)}]


wikipedia_tool_def = {
    "type": "function",
    "function": {
        "name": "wikipedia_search_tool",
        "description": "Searches for a Wikipedia article summary by query string.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for the Wikipedia article.",
                },
                "sentences": {
                    "type": "integer",
                    "description": "Number of sentences in the summary.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

# ADK-compatible list (functions with docstrings — ADK reads them directly)
TOOL_FUNCTIONS = [arxiv_search_tool, tavily_search_tool, wikipedia_search_tool]

# OpenAI-style tool definitions (for direct API use / aisuite compatibility)
TOOL_DEFS = [arxiv_tool_def, tavily_tool_def, wikipedia_tool_def]

# Name → callable mapping (for manual tool dispatch)
tool_mapping = {
    "arxiv_search_tool":     arxiv_search_tool,
    "tavily_search_tool":    tavily_search_tool,
    "wikipedia_search_tool": wikipedia_search_tool,
}
