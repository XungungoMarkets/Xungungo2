from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import requests


SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "*/*",
    "Accept-Language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,es-CL;q=0.5",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
    ),
    "Origin": "https://finance.yahoo.com",
    "Referer": "https://finance.yahoo.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    'sec-ch-ua-platform': '"Windows"',
})


@dataclass(frozen=True)
class SearchResult:
    symbol: str
    longname: str
    exch: str = ""
    type_disp: str = ""


class YahooSearchClient:
    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or SESSION
        self.url = "https://query2.finance.yahoo.com/v1/finance/search"

    def search(self, searchterm: str, limit: int = 20) -> List[SearchResult]:
        searchterm = (searchterm or "").strip()
        if not searchterm:
            return []

        params = {
            "q": searchterm,
            "lang": "en-US",
            "region": "US",
            "quotesCount": max(1, min(limit, 50)),
            "quotesQueryId": "tss_match_phrase_query",
            "multiQuoteQueryId": "multi_quote_single_token_query",
            "enableCb": "false",
            "enableNavLinks": "true",
            "enableCulturalAssets": "true",
            "enableNews": "false",
            "enableResearchReports": "false",
            "enableLists": "false",
            "listsCount": 2,
            "recommendCount": 6,
            "enablePrivateCompany": "true",
        }

        resp = self.session.get(self.url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        out: List[SearchResult] = []
        for item in data.get("quotes", []) or []:
            symbol = item.get("symbol")
            longname = item.get("longname") or item.get("shortname")
            if not symbol or not longname:
                continue
            out.append(
                SearchResult(
                    symbol=str(symbol),
                    longname=str(longname),
                    exch=str(item.get("exchDisp") or item.get("exchange") or ""),
                    type_disp=str(item.get("typeDisp") or item.get("quoteType") or ""),
                )
            )
        return out