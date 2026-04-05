from __future__ import annotations

import pytest

import backend.app.services.ncbi_adapter as ncbi_module
from backend.app.repositories.evidence_repository import EvidenceRepository
from backend.app.schemas.enums import LicenseClass
from backend.app.services.ncbi_adapter import NCBIAdapter
from backend.app.settings import get_settings


def test_ncbi_adapter_uses_epost_efetch_for_batch_search_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_NCBI_ENABLED", "true")
    get_settings.cache_clear()
    adapter = NCBIAdapter(repository=EvidenceRepository())
    calls: list[tuple[str, str]] = []

    def fake_request_json(self, endpoint: str, params: dict[str, object]) -> dict[str, object]:
        calls.append(("json", endpoint))
        if endpoint == "esearch.fcgi":
            assert params["db"] == "pubmed"
            assert params["term"] == "EGFR prognosis"
            return {"esearchresult": {"idlist": ["11111111", "22222222"]}}
        raise AssertionError(f"unexpected json endpoint: {endpoint}")

    def fake_request_text(self, url: str, params: dict[str, object]) -> str:
        endpoint = url.rsplit("/", 1)[-1]
        calls.append(("text", endpoint))
        if endpoint == "epost.fcgi":
            assert params["id"] == "11111111,22222222"
            return "<ePostResult><QueryKey>1</QueryKey><WebEnv>NCBI_ENV</WebEnv></ePostResult>"
        if endpoint == "efetch.fcgi":
            assert params["query_key"] == "1"
            assert params["WebEnv"] == "NCBI_ENV"
            return """
                <PubmedArticleSet>
                  <PubmedArticle>
                    <MedlineCitation>
                      <PMID>11111111</PMID>
                      <Article>
                        <ArticleTitle>EGFR prognosis paper</ArticleTitle>
                        <Journal>
                          <JournalIssue><PubDate><Year>2024</Year><Month>03</Month></PubDate></JournalIssue>
                          <Title>Journal One</Title>
                        </Journal>
                        <AuthorList>
                          <Author><LastName>Smith</LastName><ForeName>Jane</ForeName></Author>
                        </AuthorList>
                      </Article>
                    </MedlineCitation>
                    <PubmedData>
                      <ArticleIdList>
                        <ArticleId IdType="pubmed">11111111</ArticleId>
                        <ArticleId IdType="pmc">PMC111111</ArticleId>
                        <ArticleId IdType="doi">10.1000/egfr-1</ArticleId>
                      </ArticleIdList>
                    </PubmedData>
                  </PubmedArticle>
                  <PubmedArticle>
                    <MedlineCitation>
                      <PMID>22222222</PMID>
                      <Article>
                        <ArticleTitle>Second EGFR prognosis paper</ArticleTitle>
                        <Journal>
                          <JournalIssue><PubDate><Year>2025</Year><Month>01</Month></PubDate></JournalIssue>
                          <Title>Journal Two</Title>
                        </Journal>
                      </Article>
                    </MedlineCitation>
                    <PubmedData>
                      <ArticleIdList>
                        <ArticleId IdType="pubmed">22222222</ArticleId>
                        <ArticleId IdType="doi">10.1000/egfr-2</ArticleId>
                      </ArticleIdList>
                    </PubmedData>
                  </PubmedArticle>
                </PubmedArticleSet>
            """
        if endpoint == "oa.fcgi":
            if params["id"] == "PMC111111":
                return "<OA><records returned-count='1'><record id='PMC111111' /></records></OA>"
            return "<OA><records returned-count='0'></records></OA>"
        raise AssertionError(f"unexpected text endpoint: {endpoint}")

    monkeypatch.setattr(NCBIAdapter, "_request_json", fake_request_json)
    monkeypatch.setattr(NCBIAdapter, "_request_text", fake_request_text)

    records = adapter.search_pubmed("EGFR prognosis", max_results=2)
    assert [record.pmid for record in records] == ["11111111", "22222222"]
    assert records[0].license_class == LicenseClass.PMC_OA_SUBSET
    assert records[1].license_class == LicenseClass.METADATA_ONLY
    assert ("text", "epost.fcgi") in calls
    assert ("text", "efetch.fcgi") in calls

    call_count_before_cache_hit = len(calls)
    cached_records = adapter.search_pubmed("EGFR prognosis", max_results=2)
    assert [record.dedupe_key for record in cached_records] == ["PMID:11111111", "PMID:22222222"]
    assert len(calls) == call_count_before_cache_hit


def test_ncbi_adapter_rate_limit_waits_for_min_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_NCBI_RATE_LIMIT_PER_SEC", "2")
    get_settings.cache_clear()
    adapter = NCBIAdapter(repository=EvidenceRepository())
    monotonic_values = iter([100.0, 100.0, 100.2, 100.5])
    sleeps: list[float] = []

    monkeypatch.setattr(ncbi_module, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(ncbi_module, "sleep", lambda seconds: sleeps.append(seconds))

    adapter._apply_rate_limit()
    adapter._apply_rate_limit()

    assert sleeps == [pytest.approx(0.3, rel=1e-6)]
