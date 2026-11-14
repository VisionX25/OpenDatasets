"""Unit tests for scripts/audit_source_links.py.

Verifies link checking classifications, fallback mechanisms, offline mode,
and payload download avoidance using mocked network responses.
"""

from __future__ import annotations

import io
import socket
import ssl
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.audit_source_links import (
    CLASSIFICATION_AUTH_REQUIRED,
    CLASSIFICATION_DNS_ERROR,
    CLASSIFICATION_FORBIDDEN,
    CLASSIFICATION_NOT_CHECKED,
    CLASSIFICATION_NOT_FOUND,
    CLASSIFICATION_RATE_LIMITED,
    CLASSIFICATION_REACHABLE,
    CLASSIFICATION_REDIRECTED,
    CLASSIFICATION_SERVER_ERROR,
    CLASSIFICATION_SSL_ERROR,
    CLASSIFICATION_TIMEOUT,
    DEFAULT_USER_AGENT,
    MAX_STREAM_BYTES,
    CheckResult,
    PILOT_50_REPRESENTATIVE_URLS,
    check_single_url,
    check_url_live_detailed,
    classify_http_status,
    extract_dataset_urls,
    run_source_link_audit,
    write_csv_results,
    write_pilot_csv_results,
)


class MockHTTPResponse:
    """Mock HTTP response object mimicking http.client.HTTPResponse."""

    def __init__(self, status: int = 200, headers: dict[str, str] | None = None, body: bytes = b""):
        self.status = status
        self.code = status
        self.headers = headers or {}
        self._body = io.BytesIO(body)
        self.read_calls = 0
        self.bytes_read = 0

    def read(self, amt: int | None = None) -> bytes:
        self.read_calls += 1
        data = self._body.read(amt)
        self.bytes_read += len(data)
        return data

    def __enter__(self) -> MockHTTPResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def test_classify_http_status():
    """Verify HTTP status code to classification mapping."""
    assert classify_http_status(200) == CLASSIFICATION_REACHABLE
    assert classify_http_status(204) == CLASSIFICATION_REACHABLE
    assert classify_http_status(206) == CLASSIFICATION_REACHABLE
    assert classify_http_status(301) == CLASSIFICATION_REDIRECTED
    assert classify_http_status(302) == CLASSIFICATION_REDIRECTED
    assert classify_http_status(308) == CLASSIFICATION_REDIRECTED
    assert classify_http_status(401) == CLASSIFICATION_AUTH_REQUIRED
    assert classify_http_status(403) == CLASSIFICATION_FORBIDDEN
    assert classify_http_status(404) == CLASSIFICATION_NOT_FOUND
    assert classify_http_status(410) == CLASSIFICATION_NOT_FOUND
    assert classify_http_status(429) == CLASSIFICATION_RATE_LIMITED
    assert classify_http_status(500) == CLASSIFICATION_SERVER_ERROR
    assert classify_http_status(502) == CLASSIFICATION_SERVER_ERROR
    assert classify_http_status(503) == CLASSIFICATION_SERVER_ERROR


@patch("urllib.request.build_opener")
def test_check_url_reachable_200(mock_build_opener):
    """Test HTTP 200 response yields reachable."""
    mock_opener = MagicMock()
    mock_opener.open.return_value = MockHTTPResponse(200)
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/data")
    assert res.classification == CLASSIFICATION_REACHABLE
    assert res.status_code == 200
    assert res.redirect_url is None


@patch("urllib.request.build_opener")
def test_check_url_redirect_301_302(mock_build_opener):
    """Test HTTP 301/302 response yields redirected and records Location."""
    mock_opener = MagicMock()
    headers = {"Location": "https://example.com/new-location"}
    mock_opener.open.side_effect = urllib.error.HTTPError(
        "https://example.com/old", 301, "Moved Permanently", headers, None
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/old")
    assert res.classification == CLASSIFICATION_REDIRECTED
    assert res.status_code == 301
    assert res.redirect_url == "https://example.com/new-location"


@patch("urllib.request.build_opener")
def test_check_url_auth_required_401(mock_build_opener):
    """Test HTTP 401 response yields authentication_required."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.HTTPError(
        "https://example.com/gated", 401, "Unauthorized", {}, None
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/gated")
    assert res.classification == CLASSIFICATION_AUTH_REQUIRED
    assert res.status_code == 401


@patch("urllib.request.build_opener")
def test_check_url_forbidden_403(mock_build_opener):
    """Test HTTP 403 response yields forbidden."""
    mock_opener = MagicMock()
    # HEAD returns 403, and fallback GET also returns 403
    mock_opener.open.side_effect = urllib.error.HTTPError(
        "https://example.com/waf", 403, "Forbidden", {}, None
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/waf")
    assert res.classification == CLASSIFICATION_FORBIDDEN
    assert res.status_code == 403


@patch("urllib.request.build_opener")
def test_check_url_not_found_404(mock_build_opener):
    """Test HTTP 404 response yields not_found."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.HTTPError(
        "https://example.com/missing", 404, "Not Found", {}, None
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/missing")
    assert res.classification == CLASSIFICATION_NOT_FOUND
    assert res.status_code == 404


@patch("urllib.request.build_opener")
def test_check_url_rate_limited_429(mock_build_opener):
    """Test HTTP 429 response yields rate_limited."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.HTTPError(
        "https://example.com/rate-limited", 429, "Too Many Requests", {}, None
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/rate-limited")
    assert res.classification == CLASSIFICATION_RATE_LIMITED
    assert res.status_code == 429


@patch("urllib.request.build_opener")
def test_check_url_server_error_500(mock_build_opener):
    """Test HTTP 500 response yields server_error."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.HTTPError(
        "https://example.com/down", 500, "Internal Server Error", {}, None
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/down")
    assert res.classification == CLASSIFICATION_SERVER_ERROR
    assert res.status_code == 500


@patch("urllib.request.build_opener")
def test_check_url_timeout(mock_build_opener):
    """Test network timeout yields timeout."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = socket.timeout("timed out")
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/timeout", retries=0)
    assert res.classification == CLASSIFICATION_TIMEOUT


@patch("urllib.request.build_opener")
def test_check_url_dns_failure(mock_build_opener):
    """Test DNS resolution failure yields dns_error."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.URLError(
        socket.gaierror(-2, "Name or service not known")
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://nonexistent-domain-xyz.org")
    assert res.classification == CLASSIFICATION_DNS_ERROR


@patch("urllib.request.build_opener")
def test_check_url_ssl_error(mock_build_opener):
    """Test SSL certificate error yields ssl_error."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.URLError(
        ssl.SSLCertVerificationError(1, "certificate verify failed")
    )
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://expired-ssl.example.com")
    assert res.classification == CLASSIFICATION_SSL_ERROR


@patch("urllib.request.build_opener")
def test_check_url_head_unsupported_fallback_get_success(mock_build_opener):
    """Test HEAD 405 Method Not Allowed falls back to streaming GET and succeeds."""
    mock_opener = MagicMock()

    # First call is HEAD -> 405
    # Second call is GET -> 200
    head_error = urllib.error.HTTPError("https://example.com/no-head", 405, "Method Not Allowed", {}, None)
    get_success = MockHTTPResponse(200, body=b"<!DOCTYPE html><html><body>Hello</body></html>")

    mock_opener.open.side_effect = [head_error, get_success]
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/no-head")
    assert res.classification == CLASSIFICATION_REACHABLE
    assert res.status_code == 200
    assert mock_opener.open.call_count == 2


@patch("urllib.request.build_opener")
def test_check_url_large_binary_downloads_avoided(mock_build_opener):
    """Verify that large dataset downloads are prevented by reading at most MAX_STREAM_BYTES."""
    mock_opener = MagicMock()

    # HEAD returns 405, triggering streaming GET fallback
    head_error = urllib.error.HTTPError("https://example.com/huge.zip", 405, "Method Not Allowed", {}, None)
    # Huge 100MB body simulated
    large_body = b"X" * (MAX_STREAM_BYTES * 10)
    mock_get_response = MockHTTPResponse(200, headers={"Content-Type": "application/zip"}, body=large_body)

    mock_opener.open.side_effect = [head_error, mock_get_response]
    mock_build_opener.return_value = mock_opener

    res = check_single_url("https://example.com/huge.zip")
    assert res.classification == CLASSIFICATION_REACHABLE
    # Assert only MAX_STREAM_BYTES was consumed, not the full payload
    assert mock_get_response.bytes_read <= MAX_STREAM_BYTES


def test_check_url_offline_mode():
    """Verify offline mode makes zero network requests and marks not_checked."""
    res = check_single_url("https://example.com/offline", offline=True)
    assert res.classification == CLASSIFICATION_NOT_CHECKED
    assert res.status_code is None
    assert "Offline mode" in (res.error_message or "")


def test_deterministic_report_generation(tmp_path: Path):
    """Verify write_csv_results generates deterministic CSV outputs."""
    results = [
        {
            "dataset_id": "dataset-b",
            "field_name": "homepage_url",
            "url": "https://example.com/b",
            "status_code": 200,
            "classification": "reachable",
            "redirect_url": "",
            "error_message": "",
            "elapsed_ms": 150,
            "checked_at": "2026-11-14T12:00:00Z",
        },
        {
            "dataset_id": "dataset-a",
            "field_name": "license.url",
            "url": "https://example.com/license",
            "status_code": 301,
            "classification": "redirected",
            "redirect_url": "https://example.com/license-v2",
            "error_message": "",
            "elapsed_ms": 200,
            "checked_at": "2026-11-14T12:00:00Z",
        },
    ]

    out_csv = tmp_path / "test_report.csv"
    write_csv_results(results, out_csv)

    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 3
    assert "dataset_id,field_name,url" in lines[0]
    assert "dataset-b,homepage_url,https://example.com/b,200,reachable" in lines[1]
    assert "dataset-a,license.url,https://example.com/license,301,redirected" in lines[2]


def test_pilot_50_representative_urls_structure():
    """Verify PILOT_50_REPRESENTATIVE_URLS has 50 unique URLs spanning all 6 categories."""
    assert len(PILOT_50_REPRESENTATIVE_URLS) == 50
    urls = [x["url"] for x in PILOT_50_REPRESENTATIVE_URLS]
    assert len(set(urls)) == 50, "Duplicate URL detected in pilot sample"

    categories = {x["category"] for x in PILOT_50_REPRESENTATIVE_URLS}
    expected_categories = {
        "doi_resolver",
        "github_repo",
        "institutional_portal",
        "research_archive",
        "download_page",
        "gated_dataset",
    }
    assert categories == expected_categories


@patch("scripts.audit_source_links.check_single_url")
def test_check_url_live_detailed_200(mock_check_single):
    """Verify check_url_live_detailed handles 200 reachable conclusively."""
    mock_check_single.return_value = CheckResult(
        url="https://example.com/dataset",
        classification=CLASSIFICATION_REACHABLE,
        status_code=200,
        elapsed_ms=120,
    )

    res = check_url_live_detailed("https://example.com/dataset")
    assert res.classification == CLASSIFICATION_REACHABLE
    assert res.status_code == 200
    assert res.is_conclusive is True
    assert "verified reachable" in res.recommended_action
    assert res.redirect_chain == ["https://example.com/dataset"]


@patch("scripts.audit_source_links.check_single_url")
def test_check_url_live_detailed_redirect_chain(mock_check_single):
    """Verify check_url_live_detailed traces multi-hop redirect chains."""
    mock_check_single.side_effect = [
        CheckResult(
            url="https://doi.org/10.1234/test",
            classification=CLASSIFICATION_REDIRECTED,
            status_code=302,
            redirect_url="https://publisher.com/article",
        ),
        CheckResult(
            url="https://publisher.com/article",
            classification=CLASSIFICATION_REACHABLE,
            status_code=200,
        ),
    ]

    res = check_url_live_detailed("https://doi.org/10.1234/test")
    assert res.classification == CLASSIFICATION_REDIRECTED
    assert res.status_code == 302
    assert res.final_status_code == 200
    assert res.final_redirect_target == "https://publisher.com/article"
    assert res.redirect_chain == ["https://doi.org/10.1234/test", "https://publisher.com/article"]
    assert res.is_conclusive is True
    assert "canonical DOI resolver" in res.recommended_action


@patch("scripts.audit_source_links.check_single_url")
def test_check_url_live_detailed_403_inconclusive(mock_check_single):
    """Verify 403 Forbidden is treated as inconclusive due to WAF anti-bot mechanisms."""
    mock_check_single.return_value = CheckResult(
        url="https://portal.univ.edu/data",
        classification=CLASSIFICATION_FORBIDDEN,
        status_code=403,
        error_message="HTTP Error 403: Forbidden",
    )

    res = check_url_live_detailed("https://portal.univ.edu/data")
    assert res.classification == CLASSIFICATION_FORBIDDEN
    assert res.is_conclusive is False
    assert "WAF" in res.recommended_action


def test_write_pilot_csv_results(tmp_path: Path):
    """Verify write_pilot_csv_results formats all 14 required pilot fields."""
    pilot_data = [
        {
            "url": "https://doi.org/10.1000/182",
            "dataset_ids": "dataset-a; dataset-b",
            "category": "doi_resolver",
            "expected_publisher": "IDF",
            "status_code": 302,
            "final_redirect_target": "https://handle.net/1000/182",
            "final_status_code": 200,
            "redirect_chain": "https://doi.org/10.1000/182 -> https://handle.net/1000/182",
            "classification": "redirected",
            "error_type": "HTTP 302 Redirect",
            "check_date": "2026-11-14T12:00:00Z",
            "is_conclusive": "true",
            "recommended_action": "Retain canonical DOI resolver",
            "elapsed_ms": 250,
        }
    ]
    out_csv = tmp_path / "pilot_test.csv"
    write_pilot_csv_results(pilot_data, out_csv)
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8")
    assert "url,dataset_ids,category" in content
    assert "doi_resolver" in content
    assert "https://doi.org/10.1000/182" in content

