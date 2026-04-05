from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic, sleep
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ..schemas.agents import SearchResultItem
from ..schemas.enums import EvidenceSourceType, LicenseClass
from ..settings import AppSettings, get_settings


class NCBIAdapterError(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class NCBIEvidenceRecord:
    pmid: str | None
    pmcid: str | None
    doi: str | None
    title: str
    journal: str | None
    year: int | None
    license_class: LicenseClass
    oa_subset_flag: bool
    match_reason: str
    dedupe_key: str
    metadata_json: dict[str, Any] = field(default_factory=dict)

    def to_search_result(self) -> SearchResultItem:
        return SearchResultItem(
            pmid=self.pmid,
            pmcid=self.pmcid,
            doi=self.doi,
            title=self.title,
            journal=self.journal,
            year=self.year,
            license_class=self.license_class,
            oa_subset_flag=self.oa_subset_flag,
            match_reason=self.match_reason,
            dedupe_key=self.dedupe_key,
        )

    def external_id_norm(self) -> str:
        if self.pmid:
            return f"PMID:{self.pmid}"
        if self.pmcid:
            return f"PMCID:{self.pmcid}"
        if self.doi:
            return f"DOI:{self.doi}"
        raise ValueError("ncbi evidence record requires pmid, pmcid, or doi")

    def source_type(self) -> EvidenceSourceType:
        if self.pmid:
            return EvidenceSourceType.PUBMED
        if self.pmcid:
            return EvidenceSourceType.PMC
        return EvidenceSourceType.PUBMED

    def to_cache(self) -> dict[str, Any]:
        return {
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "doi": self.doi,
            "title": self.title,
            "journal": self.journal,
            "year": self.year,
            "license_class": self.license_class.value,
            "oa_subset_flag": self.oa_subset_flag,
            "match_reason": self.match_reason,
            "dedupe_key": self.dedupe_key,
            "metadata_json": self.metadata_json,
        }

    @classmethod
    def from_cache(cls, payload: dict[str, Any]) -> "NCBIEvidenceRecord":
        return cls(
            pmid=payload.get("pmid"),
            pmcid=payload.get("pmcid"),
            doi=payload.get("doi"),
            title=payload["title"],
            journal=payload.get("journal"),
            year=payload.get("year"),
            license_class=LicenseClass(payload.get("license_class", LicenseClass.UNKNOWN.value)),
            oa_subset_flag=bool(payload.get("oa_subset_flag", False)),
            match_reason=payload.get("match_reason", "ncbi_cache_hit"),
            dedupe_key=payload["dedupe_key"],
            metadata_json=dict(payload.get("metadata_json", {})),
        )


@dataclass(slots=True)
class NCBIAdapter:
    repository: object
    settings: AppSettings = field(default_factory=get_settings)

    _rate_lock: Lock = Lock()
    _last_request_started_at: float = 0.0

    def search_pubmed(self, query: str, *, max_results: int) -> list[NCBIEvidenceRecord]:
        cache_key = f"{self._normalize_query(query)}::{max_results}"
        cached = self._search_cache_get(cache_key)
        if cached is not None:
            return cached
        records = self._search_remote(query, max_results=max_results)
        self._search_cache_set(cache_key, records)
        return records

    def resolve_identifier(self, identifier: str) -> NCBIEvidenceRecord | None:
        cache_key = self._normalize_identifier(identifier)
        cached = self._resolve_cache_get(cache_key)
        if cached is not None:
            return cached
        record = self._resolve_remote(identifier)
        self._resolve_cache_set(cache_key, record)
        return record

    def _search_remote(self, query: str, *, max_results: int) -> list[NCBIEvidenceRecord]:
        search_payload = self._request_json(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results,
            },
        )
        pmids = search_payload.get("esearchresult", {}).get("idlist", [])
        if not isinstance(pmids, list) or not pmids:
            return []
        return self._fetch_records(pmids, match_reason="ncbi_entrez_search")

    def _resolve_remote(self, identifier: str) -> NCBIEvidenceRecord | None:
        kind, normalized = self._classify_identifier(identifier)
        if kind is None:
            return None
        if kind == "pmid":
            records = self._fetch_records([normalized], match_reason="ncbi_identifier_resolve")
            return records[0] if records else None

        search_term = {
            "pmcid": f"{normalized}[pmc]",
            "doi": f"{normalized}[doi]",
        }[kind]
        search_payload = self._request_json(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "term": search_term,
                "retmode": "json",
                "retmax": 1,
            },
        )
        pmids = search_payload.get("esearchresult", {}).get("idlist", [])
        if not isinstance(pmids, list) or not pmids:
            return None
        records = self._fetch_records(pmids[:1], match_reason="ncbi_identifier_resolve")
        return records[0] if records else None

    def _fetch_records(self, pmids: list[str], *, match_reason: str) -> list[NCBIEvidenceRecord]:
        ordered_pmids = list(dict.fromkeys(pmid for pmid in pmids if pmid))
        if not ordered_pmids:
            return []
        if len(ordered_pmids) == 1:
            return self._fetch_summaries(ordered_pmids, match_reason=match_reason)
        query_key, web_env = self._post_history(ordered_pmids)
        return self._fetch_records_via_history(query_key=query_key, web_env=web_env, match_reason=match_reason)

    def _fetch_summaries(self, pmids: list[str], *, match_reason: str) -> list[NCBIEvidenceRecord]:
        summary_payload = self._request_json(
            "esummary.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
            },
        )
        result = summary_payload.get("result", {})
        ordered_ids = result.get("uids", pmids)
        records: list[NCBIEvidenceRecord] = []
        for pmid in ordered_ids:
            summary = result.get(str(pmid))
            if not isinstance(summary, dict):
                continue
            records.append(self._build_record(summary, match_reason=match_reason))
        return records

    def _post_history(self, pmids: list[str]) -> tuple[str, str]:
        payload = self._request_text(
            f"{self.settings.ncbi_base_url}/epost.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(pmids),
            },
        )
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            raise NCBIAdapterError("ncbi returned invalid epost xml") from exc
        query_key = self._as_nonempty_string(root.findtext(".//QueryKey"))
        web_env = self._as_nonempty_string(root.findtext(".//WebEnv"))
        if query_key is None or web_env is None:
            raise NCBIAdapterError("ncbi epost response missing QueryKey or WebEnv")
        return query_key, web_env

    def _fetch_records_via_history(
        self,
        *,
        query_key: str,
        web_env: str,
        match_reason: str,
    ) -> list[NCBIEvidenceRecord]:
        payload = self._request_text(
            f"{self.settings.ncbi_base_url}/efetch.fcgi",
            {
                "db": "pubmed",
                "query_key": query_key,
                "WebEnv": web_env,
                "retmode": "xml",
                "rettype": "abstract",
            },
        )
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            raise NCBIAdapterError("ncbi returned invalid efetch xml") from exc
        records: list[NCBIEvidenceRecord] = []
        for article in root.findall(".//PubmedArticle"):
            record = self._build_record_from_pubmed_article(article, match_reason=match_reason)
            if record is not None:
                records.append(record)
        return records

    def _build_record(self, summary: dict[str, Any], *, match_reason: str) -> NCBIEvidenceRecord:
        pmid = self._article_id(summary, "pubmed") or self._as_nonempty_string(summary.get("uid"))
        pmcid = self._article_id(summary, "pmc")
        doi = self._article_id(summary, "doi")
        license_class, oa_subset_flag = self._resolve_license(pmcid)
        journal = self._as_nonempty_string(summary.get("fulljournalname")) or self._as_nonempty_string(summary.get("source"))
        authors = [
            author.get("name")
            for author in summary.get("authors", [])
            if isinstance(author, dict) and author.get("name")
        ]
        metadata_json = {
            "authors": authors,
            "pubdate": self._as_nonempty_string(summary.get("pubdate")),
            "epubdate": self._as_nonempty_string(summary.get("epubdate")),
            "source": self._as_nonempty_string(summary.get("source")),
            "fulljournalname": self._as_nonempty_string(summary.get("fulljournalname")),
        }
        return NCBIEvidenceRecord(
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            title=self._as_nonempty_string(summary.get("title")) or "Untitled PubMed record",
            journal=journal,
            year=self._extract_year(summary),
            license_class=license_class,
            oa_subset_flag=oa_subset_flag,
            match_reason=match_reason,
            dedupe_key=self._dedupe_key(pmid=pmid, pmcid=pmcid, doi=doi),
            metadata_json={key: value for key, value in metadata_json.items() if value not in (None, [], "")},
        )

    def _build_record_from_pubmed_article(
        self,
        article: ElementTree.Element,
        *,
        match_reason: str,
    ) -> NCBIEvidenceRecord | None:
        medline = article.find("./MedlineCitation")
        article_node = medline.find("./Article") if medline is not None else None
        pubmed_data = article.find("./PubmedData")
        if medline is None or article_node is None:
            return None

        pmid = self._as_nonempty_string(medline.findtext("./PMID"))
        title = self._flatten_xml_text(article_node.find("./ArticleTitle")) or "Untitled PubMed record"
        journal = self._flatten_xml_text(article_node.find("./Journal/Title"))
        year = self._extract_article_year(article_node, pubmed_data)
        pmcid = None
        doi = None
        if pubmed_data is not None:
            for article_id in pubmed_data.findall(".//ArticleId"):
                id_type = (article_id.attrib.get("IdType") or "").lower()
                value = self._flatten_xml_text(article_id)
                if value is None:
                    continue
                if id_type == "pmc":
                    pmcid = value.upper()
                elif id_type == "doi":
                    doi = value
                elif id_type == "pubmed" and pmid is None:
                    pmid = value

        if pmid is None and pmcid is None and doi is None:
            return None

        license_class, oa_subset_flag = self._resolve_license(pmcid)
        authors = self._extract_article_authors(article_node)
        metadata_json = {
            "authors": authors,
            "pubdate": self._extract_pubdate_text(article_node),
        }
        return NCBIEvidenceRecord(
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            title=title,
            journal=journal,
            year=year,
            license_class=license_class,
            oa_subset_flag=oa_subset_flag,
            match_reason=match_reason,
            dedupe_key=self._dedupe_key(pmid=pmid, pmcid=pmcid, doi=doi),
            metadata_json={key: value for key, value in metadata_json.items() if value not in (None, [], "")},
        )

    def _resolve_license(self, pmcid: str | None) -> tuple[LicenseClass, bool]:
        if pmcid is None:
            return LicenseClass.METADATA_ONLY, False
        try:
            payload = self._request_text(self.settings.pmc_oa_base_url, {"id": pmcid})
            root = ElementTree.fromstring(payload)
        except (NCBIAdapterError, ElementTree.ParseError):
            return LicenseClass.METADATA_ONLY, False
        record = root.find("./records/record")
        if record is not None and record.get("id"):
            return LicenseClass.PMC_OA_SUBSET, True
        return LicenseClass.METADATA_ONLY, False

    def _request_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(self._request_text(f"{self.settings.ncbi_base_url}/{endpoint}", params))
        except json.JSONDecodeError as exc:
            raise NCBIAdapterError(f"ncbi returned invalid json for {endpoint}") from exc

    def _request_text(self, url: str, params: dict[str, Any]) -> str:
        self._apply_rate_limit()
        request_params = {
            **params,
            "tool": self.settings.ncbi_tool,
        }
        if self.settings.ncbi_email:
            request_params["email"] = self.settings.ncbi_email
        if self.settings.ncbi_api_key:
            request_params["api_key"] = self.settings.ncbi_api_key
        target_url = f"{url}?{urlencode(request_params, doseq=True)}"
        request = Request(
            target_url,
            headers={"User-Agent": f"{self.settings.ncbi_tool} ({self.settings.ncbi_email or 'no-email'})"},
        )
        try:
            with urlopen(request, timeout=self.settings.ncbi_timeout_seconds) as response:
                return response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover
            raise NCBIAdapterError(f"ncbi request failed for {target_url}") from exc

    def _apply_rate_limit(self) -> None:
        rate_limit = self.settings.ncbi_rate_limit_per_sec
        if rate_limit is None:
            rate_limit = 10.0 if self.settings.ncbi_api_key else 3.0
        if rate_limit <= 0:
            return
        min_interval = 1.0 / rate_limit
        with self._rate_lock:
            now = monotonic()
            wait_seconds = min_interval - (now - self._last_request_started_at)
            if wait_seconds > 0:
                sleep(wait_seconds)
            self._last_request_started_at = monotonic()

    def _search_cache_get(self, cache_key: str) -> list[NCBIEvidenceRecord] | None:
        entry = self.repository.store.ncbi_search_cache.get(cache_key)
        if not self._is_cache_entry_fresh(entry):
            return None
        return [NCBIEvidenceRecord.from_cache(payload) for payload in entry.get("records", [])]

    def _search_cache_set(self, cache_key: str, records: list[NCBIEvidenceRecord]) -> None:
        self.repository.store.ncbi_search_cache[cache_key] = {
            "cached_at": utcnow().isoformat(),
            "records": [record.to_cache() for record in records],
        }

    def _resolve_cache_get(self, cache_key: str) -> NCBIEvidenceRecord | None:
        entry = self.repository.store.ncbi_resolve_cache.get(cache_key)
        if not self._is_cache_entry_fresh(entry):
            return None
        record = entry.get("record")
        if record is None:
            return None
        return NCBIEvidenceRecord.from_cache(record)

    def _resolve_cache_set(self, cache_key: str, record: NCBIEvidenceRecord | None) -> None:
        self.repository.store.ncbi_resolve_cache[cache_key] = {
            "cached_at": utcnow().isoformat(),
            "record": record.to_cache() if record is not None else None,
        }

    def _is_cache_entry_fresh(self, entry: dict[str, Any] | None) -> bool:
        if not isinstance(entry, dict):
            return False
        cached_at_raw = entry.get("cached_at")
        if not isinstance(cached_at_raw, str):
            return False
        try:
            cached_at = datetime.fromisoformat(cached_at_raw)
        except ValueError:
            return False
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return cached_at >= utcnow() - timedelta(hours=self.settings.ncbi_cache_ttl_hours)

    @staticmethod
    def _classify_identifier(identifier: str) -> tuple[str | None, str]:
        normalized = identifier.strip()
        upper = normalized.upper()
        if upper.startswith("PMID:"):
            return "pmid", normalized.split(":", 1)[1].strip()
        if upper.startswith("PMCID:"):
            return "pmcid", normalized.split(":", 1)[1].strip().upper()
        if upper.startswith("DOI:"):
            return "doi", normalized.split(":", 1)[1].strip().lower()
        if upper.startswith("PMC"):
            return "pmcid", upper
        if "/" in normalized:
            return "doi", normalized.lower()
        if normalized.isdigit():
            return "pmid", normalized
        return None, normalized

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        kind, normalized = NCBIAdapter._classify_identifier(identifier)
        return f"{kind or 'raw'}::{normalized}"

    @staticmethod
    def _normalize_query(query: str) -> str:
        return " ".join(query.split()).lower()

    @staticmethod
    def _article_id(summary: dict[str, Any], idtype: str) -> str | None:
        for article_id in summary.get("articleids", []):
            if isinstance(article_id, dict) and article_id.get("idtype") == idtype:
                value = article_id.get("value")
                if isinstance(value, str) and value:
                    return value.upper() if idtype == "pmc" else value
        return None

    @staticmethod
    def _extract_year(summary: dict[str, Any]) -> int | None:
        for candidate in [summary.get("sortpubdate"), summary.get("pubdate"), summary.get("epubdate")]:
            if not isinstance(candidate, str):
                continue
            for token in candidate.replace("/", " ").split():
                if token.isdigit() and len(token) == 4:
                    return int(token)
        return None

    @staticmethod
    def _extract_article_year(article_node: ElementTree.Element, pubmed_data: ElementTree.Element | None) -> int | None:
        for candidate in [
            NCBIAdapter._extract_pubdate_text(article_node),
            NCBIAdapter._extract_article_date_text(article_node),
            NCBIAdapter._extract_history_pubdate_text(pubmed_data),
        ]:
            if not candidate:
                continue
            for token in candidate.replace("/", " ").split():
                if token.isdigit() and len(token) == 4:
                    return int(token)
        return None

    @staticmethod
    def _dedupe_key(*, pmid: str | None, pmcid: str | None, doi: str | None) -> str:
        if pmid:
            return f"PMID:{pmid}"
        if pmcid:
            return f"PMCID:{pmcid}"
        if doi:
            return f"DOI:{doi}"
        raise ValueError("dedupe key requires pmid, pmcid, or doi")

    @staticmethod
    def _as_nonempty_string(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _flatten_xml_text(element: ElementTree.Element | None) -> str | None:
        if element is None:
            return None
        text = "".join(element.itertext()).strip()
        return text or None

    @staticmethod
    def _extract_pubdate_text(article_node: ElementTree.Element) -> str | None:
        pub_date = article_node.find("./Journal/JournalIssue/PubDate")
        if pub_date is None:
            return None
        parts = [
            NCBIAdapter._flatten_xml_text(pub_date.find("./Year")),
            NCBIAdapter._flatten_xml_text(pub_date.find("./Month")),
            NCBIAdapter._flatten_xml_text(pub_date.find("./Day")),
            NCBIAdapter._flatten_xml_text(pub_date.find("./MedlineDate")),
        ]
        return " ".join(part for part in parts if part) or None

    @staticmethod
    def _extract_article_date_text(article_node: ElementTree.Element) -> str | None:
        article_date = article_node.find("./ArticleDate")
        if article_date is None:
            return None
        parts = [
            NCBIAdapter._flatten_xml_text(article_date.find("./Year")),
            NCBIAdapter._flatten_xml_text(article_date.find("./Month")),
            NCBIAdapter._flatten_xml_text(article_date.find("./Day")),
        ]
        return " ".join(part for part in parts if part) or None

    @staticmethod
    def _extract_history_pubdate_text(pubmed_data: ElementTree.Element | None) -> str | None:
        if pubmed_data is None:
            return None
        pubmed_pub_date = pubmed_data.find(".//PubMedPubDate")
        if pubmed_pub_date is None:
            return None
        parts = [
            NCBIAdapter._flatten_xml_text(pubmed_pub_date.find("./Year")),
            NCBIAdapter._flatten_xml_text(pubmed_pub_date.find("./Month")),
            NCBIAdapter._flatten_xml_text(pubmed_pub_date.find("./Day")),
        ]
        return " ".join(part for part in parts if part) or None

    @staticmethod
    def _extract_article_authors(article_node: ElementTree.Element) -> list[str]:
        authors: list[str] = []
        for author in article_node.findall("./AuthorList/Author"):
            collective_name = NCBIAdapter._flatten_xml_text(author.find("./CollectiveName"))
            if collective_name:
                authors.append(collective_name)
                continue
            last_name = NCBIAdapter._flatten_xml_text(author.find("./LastName"))
            fore_name = NCBIAdapter._flatten_xml_text(author.find("./ForeName"))
            initials = NCBIAdapter._flatten_xml_text(author.find("./Initials"))
            if last_name and fore_name:
                authors.append(f"{last_name} {fore_name}")
            elif last_name and initials:
                authors.append(f"{last_name} {initials}")
            elif last_name:
                authors.append(last_name)
            elif fore_name:
                authors.append(fore_name)
        return authors
