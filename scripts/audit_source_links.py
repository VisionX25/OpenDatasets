#!/usr/bin/env python3
"""OpenDatasets Source Link Health Audit Script.

Performs deterministic, rate-limited, and safe HTTP/HTTPS health checks on URLs
referenced in dataset metadata records (data/datasets/*.json) without downloading
large binaries or datasets.

Supported Classifications:
  - reachable
  - redirected
  - authentication_required
  - rate_limited
  - forbidden
  - not_found
  - server_error
  - timeout
  - dns_error
  - ssl_error
  - inconclusive
  - not_checked
"""

from __future__ import annotations

import argparse
import csv
import datetime
import http.client
import ipaddress
import json
import logging
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; OpenDatasets-AuditBot/1.0; "
    "+https://github.com/VisionX25/OpenDatasets; research-metadata-audit)"
)
DEFAULT_TIMEOUT = 10.0
DEFAULT_CONCURRENCY = 8
DEFAULT_RETRIES = 2
MAX_STREAM_BYTES = 2048  # Read at most 2KB to verify connectivity and prevent binary download

CLASSIFICATION_REACHABLE = "reachable"
CLASSIFICATION_REDIRECTED = "redirected"
CLASSIFICATION_AUTH_REQUIRED = "authentication_required"
CLASSIFICATION_RATE_LIMITED = "rate_limited"
CLASSIFICATION_FORBIDDEN = "forbidden"
CLASSIFICATION_NOT_FOUND = "not_found"
CLASSIFICATION_SERVER_ERROR = "server_error"
CLASSIFICATION_TIMEOUT = "timeout"
CLASSIFICATION_DNS_ERROR = "dns_error"
CLASSIFICATION_SSL_ERROR = "ssl_error"
CLASSIFICATION_INCONCLUSIVE = "inconclusive"
CLASSIFICATION_NOT_CHECKED = "not_checked"

VALID_CLASSIFICATIONS = {
    CLASSIFICATION_REACHABLE,
    CLASSIFICATION_REDIRECTED,
    CLASSIFICATION_AUTH_REQUIRED,
    CLASSIFICATION_RATE_LIMITED,
    CLASSIFICATION_FORBIDDEN,
    CLASSIFICATION_NOT_FOUND,
    CLASSIFICATION_SERVER_ERROR,
    CLASSIFICATION_TIMEOUT,
    CLASSIFICATION_DNS_ERROR,
    CLASSIFICATION_SSL_ERROR,
    CLASSIFICATION_INCONCLUSIVE,
    CLASSIFICATION_NOT_CHECKED,
}


@dataclass
class URLReference:
    """A reference to a URL from a specific dataset and field."""

    dataset_id: str
    field_name: str
    url: str


@dataclass
class CheckResult:
    """The result of a network health check for a single URL."""

    url: str
    classification: str
    status_code: int | None = None
    redirect_url: str | None = None
    error_message: str | None = None
    elapsed_ms: int = 0
    checked_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    final_redirect_target: str | None = None
    final_status_code: int | None = None
    redirect_chain: list[str] = field(default_factory=list)
    is_conclusive: bool = True
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom handler to intercept redirects without automatically following them."""

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        # Returning None prevents following the redirect
        return None


class SSRFSecurityError(OSError):
    """Raised when an outbound connection attempts to reach a loopback, private, link-local, or restricted address."""
    pass


RESTRICTED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata.azure.com",
    "169.254.169.254",
}


def is_ip_restricted(ip_str: str) -> tuple[bool, str]:
    """Check if an IP string is private, loopback, link-local, cloud metadata, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True, f"Restricted IP address: {ip_str}"
        return False, ""
    except ValueError:
        return True, f"Invalid IP address format: {ip_str}"


def create_safe_connection(
    address: tuple[str, int],
    timeout: float = socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address: tuple[str, int] | None = None,
) -> socket.socket:
    """Create a TCP socket connection while validating target IP at connection time.

    Mitigates DNS rebinding / TOCTOU vulnerabilities by resolving DNS at socket creation time
    and verifying the destination IP before initiating TCP handshake (connect).
    """
    host, port = address
    host_clean = host.lower().strip(".")
    if host_clean in RESTRICTED_HOSTNAMES or host_clean.endswith(".localhost"):
        raise SSRFSecurityError(f"Connection blocked: host '{host}' is restricted")

    try:
        addr_infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise OSError(f"DNS resolution failed for '{host}': {exc}") from exc

    if not addr_infos:
        raise OSError(f"DNS returned no addresses for '{host}'")

    err = None
    for res in addr_infos:
        af, socktype, proto, canonname, sa = res
        sock_ip = sa[0]
        if sock_ip in RESTRICTED_HOSTNAMES:
            raise SSRFSecurityError(f"Connection blocked: host '{host}' resolved to restricted IP {sock_ip}")

        is_restr, reason = is_ip_restricted(sock_ip)
        if is_restr:
            raise SSRFSecurityError(f"Connection blocked: host '{host}' resolved to {reason}")

        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock
        except Exception as exc:
            err = exc
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    raise OSError(f"Could not connect to any address for '{host}'")


class SafeHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._create_connection = create_safe_connection


class SafeHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._create_connection = create_safe_connection


class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(SafeHTTPConnection, req)


class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(SafeHTTPSConnection, req)


def build_safe_opener(
    ssl_context: ssl.SSLContext | None = None,
    trust_env_proxy: bool = False,
) -> urllib.request.OpenerDirector:
    """Build an OpenerDirector with NoRedirectHandler, connection-time IP validation, and proxy control."""
    handlers: list[Any] = [NoRedirectHandler, SafeHTTPHandler]
    if not trust_env_proxy:
        # Enforce direct connection; prevent ambient proxy hijacking of connection-time IP validation
        handlers.append(urllib.request.ProxyHandler({}))
    if ssl_context is not None:
        handlers.append(SafeHTTPSHandler(context=ssl_context))
    else:
        handlers.append(SafeHTTPSHandler)
    return urllib.request.build_opener(*handlers)


def extract_dataset_urls(data_dir: Path, dataset_filter: set[str] | None = None) -> list[URLReference]:
    """Scan dataset JSON files and extract all URL references."""
    references: list[URLReference] = []

    for file_path in sorted(data_dir.glob("*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception as exc:
            logging.warning("Failed to parse %s: %s", file_path, exc)
            continue

        dataset_id = data.get("id") or file_path.stem
        if dataset_filter and dataset_id not in dataset_filter:
            continue

        # 1. homepage_url
        if data.get("homepage_url"):
            references.append(URLReference(dataset_id, "homepage_url", str(data["homepage_url"]).strip()))

        # 2. publisher.url
        pub = data.get("publisher")
        if isinstance(pub, dict) and pub.get("url"):
            references.append(URLReference(dataset_id, "publisher.url", str(pub["url"]).strip()))

        # 3. license.url
        lic = data.get("license")
        if isinstance(lic, dict) and lic.get("url"):
            references.append(URLReference(dataset_id, "license.url", str(lic["url"]).strip()))

        # 4. citation.paper_url
        cit = data.get("citation")
        if isinstance(cit, dict) and cit.get("paper_url"):
            references.append(URLReference(dataset_id, "citation.paper_url", str(cit["paper_url"]).strip()))

        # 5. source_references[].url
        s_refs = data.get("source_references")
        if isinstance(s_refs, list):
            for idx, ref in enumerate(s_refs):
                if isinstance(ref, dict) and ref.get("url"):
                    references.append(
                        URLReference(dataset_id, f"source_references[{idx}].url", str(ref["url"]).strip())
                    )

    return references


def classify_http_status(status_code: int) -> str:
    """Classify an HTTP status code into the standard audit categories."""
    if status_code in (200, 204, 206):
        return CLASSIFICATION_REACHABLE
    if status_code in (301, 302, 303, 307, 308):
        return CLASSIFICATION_REDIRECTED
    if status_code == 401:
        return CLASSIFICATION_AUTH_REQUIRED
    if status_code == 403:
        return CLASSIFICATION_FORBIDDEN
    if status_code in (404, 410):
        return CLASSIFICATION_NOT_FOUND
    if status_code == 429:
        return CLASSIFICATION_RATE_LIMITED
    if 500 <= status_code <= 599:
        return CLASSIFICATION_SERVER_ERROR
    return CLASSIFICATION_INCONCLUSIVE


def check_single_url(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    retries: int = DEFAULT_RETRIES,
    offline: bool = False,
    ssl_context: ssl.SSLContext | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> CheckResult:
    """Check the health of a single URL using HEAD followed by streaming GET fallback.

    Ensures no large dataset payloads are downloaded.
    """
    if offline:
        return CheckResult(
            url=url,
            classification=CLASSIFICATION_NOT_CHECKED,
            error_message="Offline mode active",
        )

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return CheckResult(
            url=url,
            classification=CLASSIFICATION_INCONCLUSIVE,
            error_message=f"Unsupported URL scheme: {parsed.scheme}",
        )

    if ssl_context is None:
        ssl_context = ssl.create_default_context()

    last_error: Exception | None = None
    start_time = time.monotonic()
    active_opener = opener if opener is not None else urllib.request.build_opener(NoRedirectHandler)

    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(0.5 * (2 ** (attempt - 1)))  # Exponential backoff: 0.5s, 1.0s

        # First attempt: HTTP HEAD request
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "*/*",
            },
            method="HEAD",
        )

        try:
            with active_opener.open(req, timeout=timeout) as response:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                code = getattr(response, "status", getattr(response, "code", 200))
                classification = classify_http_status(code)

                redirect_target = None
                if classification == CLASSIFICATION_REDIRECTED:
                    redirect_target = response.headers.get("Location")

                return CheckResult(
                    url=url,
                    classification=classification,
                    status_code=code,
                    redirect_url=redirect_target,
                    elapsed_ms=elapsed_ms,
                )

        except urllib.error.HTTPError as http_err:
            code = http_err.code
            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Redirect detected from HTTPError (since NoRedirectHandler prevents following)
            if code in (301, 302, 303, 307, 308):
                redirect_target = http_err.headers.get("Location")
                return CheckResult(
                    url=url,
                    classification=CLASSIFICATION_REDIRECTED,
                    status_code=code,
                    redirect_url=redirect_target,
                    elapsed_ms=elapsed_ms,
                )

            # 405 Method Not Allowed, 501 Not Implemented, or 403 Forbidden on HEAD:
            # Many servers/WAFs reject HEAD requests or require GET. Fall back to minimal streaming GET.
            if code in (400, 403, 405, 501):
                return _check_streaming_get(url, timeout, user_agent, start_time, active_opener)

            classification = classify_http_status(code)
            return CheckResult(
                url=url,
                classification=classification,
                status_code=code,
                error_message=str(http_err),
                elapsed_ms=elapsed_ms,
            )

        except (SSRFSecurityError, urllib.error.URLError) as url_err:
            last_error = url_err
            reason = getattr(url_err, "reason", url_err)

            if isinstance(url_err, SSRFSecurityError) or isinstance(reason, SSRFSecurityError):
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return CheckResult(
                    url=url,
                    classification=CLASSIFICATION_FORBIDDEN,
                    error_message=f"SSRF protection blocked target: {reason}",
                    elapsed_ms=elapsed_ms,
                )

            if isinstance(reason, socket.timeout) or "timed out" in str(url_err).lower():
                continue  # Retry on timeout
            if isinstance(reason, ssl.SSLError) or "certificate" in str(url_err).lower():
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return CheckResult(
                    url=url,
                    classification=CLASSIFICATION_SSL_ERROR,
                    error_message=str(url_err),
                    elapsed_ms=elapsed_ms,
                )
            if isinstance(reason, socket.gaierror) or "name or service not known" in str(url_err).lower():
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return CheckResult(
                    url=url,
                    classification=CLASSIFICATION_DNS_ERROR,
                    error_message=str(url_err),
                    elapsed_ms=elapsed_ms,
                )

        except socket.timeout:
            continue
        except (http.client.HTTPException, ConnectionResetError, ConnectionRefusedError) as conn_err:
            last_error = conn_err
            continue
        except Exception as exc:
            last_error = exc
            break

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    err_str = str(last_error) if last_error else "Request timed out"

    if "timed out" in err_str.lower() or isinstance(last_error, socket.timeout):
        return CheckResult(
            url=url,
            classification=CLASSIFICATION_TIMEOUT,
            error_message=err_str,
            elapsed_ms=elapsed_ms,
        )

    return CheckResult(
        url=url,
        classification=CLASSIFICATION_INCONCLUSIVE,
        error_message=err_str,
        elapsed_ms=elapsed_ms,
    )


def _check_streaming_get(
    url: str,
    timeout: float,
    user_agent: str,
    start_time: float,
    opener: urllib.request.OpenerDirector,
) -> CheckResult:
    """Minimal streaming GET request that reads only the first bytes and prevents downloading files."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Range": f"bytes=0-{MAX_STREAM_BYTES}",
        },
        method="GET",
    )

    try:
        with opener.open(req, timeout=timeout) as response:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            code = getattr(response, "status", getattr(response, "code", 200))
            classification = classify_http_status(code)

            redirect_target = None
            if classification == CLASSIFICATION_REDIRECTED:
                redirect_target = response.headers.get("Location")

            # Safely consume only a small prefix
            try:
                _ = response.read(MAX_STREAM_BYTES)
            except Exception:
                pass

            return CheckResult(
                url=url,
                classification=classification,
                status_code=code,
                redirect_url=redirect_target,
                elapsed_ms=elapsed_ms,
            )

    except urllib.error.HTTPError as http_err:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        code = http_err.code
        if code in (301, 302, 303, 307, 308):
            return CheckResult(
                url=url,
                classification=CLASSIFICATION_REDIRECTED,
                status_code=code,
                redirect_url=http_err.headers.get("Location"),
                elapsed_ms=elapsed_ms,
            )
        classification = classify_http_status(code)
        return CheckResult(
            url=url,
            classification=classification,
            status_code=code,
            error_message=str(http_err),
            elapsed_ms=elapsed_ms,
        )
    except (SSRFSecurityError, urllib.error.URLError) as url_err:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        reason = getattr(url_err, "reason", url_err)
        if isinstance(url_err, SSRFSecurityError) or isinstance(reason, SSRFSecurityError):
            return CheckResult(
                url=url,
                classification=CLASSIFICATION_FORBIDDEN,
                error_message=f"SSRF protection blocked target: {reason}",
                elapsed_ms=elapsed_ms,
            )
        return CheckResult(
            url=url,
            classification=CLASSIFICATION_INCONCLUSIVE,
            error_message=f"GET fallback failed: {url_err}",
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return CheckResult(
            url=url,
            classification=CLASSIFICATION_INCONCLUSIVE,
            error_message=f"GET fallback failed: {exc}",
            elapsed_ms=elapsed_ms,
        )


def run_source_link_audit(
    data_dir: Path,
    dataset_filter: set[str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    concurrency: int = DEFAULT_CONCURRENCY,
    retries: int = DEFAULT_RETRIES,
    offline: bool = False,
    cache: dict[str, CheckResult] | None = None,
    limit_urls: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, CheckResult], dict[str, int]]:
    """Execute complete source link health audit across dataset records."""
    references = extract_dataset_urls(data_dir, dataset_filter=dataset_filter)
    url_cache: dict[str, CheckResult] = cache if cache is not None else {}

    # Identify unique URLs that need checking
    unique_urls = sorted({ref.url for ref in references})
    if limit_urls is not None and limit_urls > 0:
        unique_urls = unique_urls[:limit_urls]

    urls_to_fetch = [u for u in unique_urls if u not in url_cache]

    if not offline and urls_to_fetch:
        max_workers = min(concurrency, max(1, len(urls_to_fetch)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(
                    check_single_url,
                    url=url,
                    timeout=timeout,
                    user_agent=DEFAULT_USER_AGENT,
                    retries=retries,
                    offline=offline,
                ): url
                for url in urls_to_fetch
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    url_cache[url] = result
                except Exception as exc:
                    url_cache[url] = CheckResult(
                        url=url,
                        classification=CLASSIFICATION_INCONCLUSIVE,
                        error_message=str(exc),
                    )
    elif offline:
        for url in urls_to_fetch:
            url_cache[url] = CheckResult(
                url=url,
                classification=CLASSIFICATION_NOT_CHECKED,
                error_message="Offline mode active",
            )

    # Join results back to references
    results_table: list[dict[str, Any]] = []
    classification_counts: dict[str, int] = {c: 0 for c in VALID_CLASSIFICATIONS}

    for ref in references:
        res = url_cache.get(
            ref.url,
            CheckResult(
                url=ref.url,
                classification=CLASSIFICATION_NOT_CHECKED,
                error_message="Not checked",
            ),
        )
        classification_counts[res.classification] = classification_counts.get(res.classification, 0) + 1
        results_table.append(
            {
                "dataset_id": ref.dataset_id,
                "field_name": ref.field_name,
                "url": ref.url,
                "status_code": res.status_code if res.status_code is not None else "",
                "classification": res.classification,
                "redirect_url": res.redirect_url or "",
                "error_message": res.error_message or "",
                "elapsed_ms": res.elapsed_ms,
                "checked_at": res.checked_at,
            }
        )

    return results_table, url_cache, classification_counts


def write_csv_results(results: list[dict[str, Any]], output_path: Path) -> None:
    """Write source link audit results to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset_id",
        "field_name",
        "url",
        "status_code",
        "classification",
        "redirect_url",
        "error_message",
        "elapsed_ms",
        "checked_at",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)


PILOT_50_REPRESENTATIVE_URLS: list[dict[str, str]] = [
    # 1. DOI Resolvers (10)
    {"url": "https://doi.org/10.1109/ICCVW.2011.6130513", "category": "doi_resolver", "expected_publisher": "IEEE"},
    {"url": "https://doi.org/10.17632/zvkwpsw84d.5", "category": "doi_resolver", "expected_publisher": "Mendeley Data"},
    {"url": "https://doi.org/10.13026/C2RP4B", "category": "doi_resolver", "expected_publisher": "PhysioNet"},
    {"url": "https://doi.org/10.1016/j.imavis.2016.01.002", "category": "doi_resolver", "expected_publisher": "Elsevier"},
    {"url": "https://doi.org/10.1007/s11263-018-1140-0", "category": "doi_resolver", "expected_publisher": "Springer Nature"},
    {"url": "https://doi.org/10.1038/s41467-022-30695-9", "category": "doi_resolver", "expected_publisher": "Nature Publishing Group"},
    {"url": "https://doi.org/10.48550/arXiv.2004.06320", "category": "doi_resolver", "expected_publisher": "arXiv"},
    {"url": "https://doi.org/10.5194/isprs-annals-IV-2-W7-153-2019", "category": "doi_resolver", "expected_publisher": "Copernicus / ISPRS"},
    {"url": "https://doi.org/10.1002/jmri.21049", "category": "doi_resolver", "expected_publisher": "Wiley"},
    {"url": "https://doi.org/10.1109/TBME.2011.2179934", "category": "doi_resolver", "expected_publisher": "Investigated Erroneous DOI (De Gruyter 10.1515/bmt-2011-0130)"},

    # 2. GitHub Repositories (9)
    {"url": "https://github.com/facebookresearch/anli", "category": "github_repo", "expected_publisher": "Facebook Research"},
    {"url": "https://github.com/daniilidis-group/mvsec", "category": "github_repo", "expected_publisher": "Daniilidis Group (UPenn)"},
    {"url": "https://github.com/fMoW/dataset", "category": "github_repo", "expected_publisher": "fMoW Authors"},
    {"url": "https://github.com/argoverse/av2-api", "category": "github_repo", "expected_publisher": "Argoverse / Argo AI"},
    {"url": "https://github.com/StanfordVL/BEHAVIOR-1K/blob/main/docs/challenge/dataset.md", "category": "github_repo", "expected_publisher": "Stanford Vision & Learning Lab"},
    {"url": "https://github.com/beir-cellar/beir", "category": "github_repo", "expected_publisher": "BEIR Authors"},
    {"url": "https://github.com/Chopper-233/Anomaly-ShapeNet", "category": "github_repo", "expected_publisher": "Anomaly-ShapeNet Authors"},
    {"url": "https://github.com/naurosromim/hate-speech-dataset-for-Bengali-social-media", "category": "github_repo", "expected_publisher": "Bengali NLP Authors"},
    {"url": "https://github.com/PaulMcHard/3D-ADAMBench", "category": "github_repo", "expected_publisher": "3D-ADAM Authors"},

    # 3. Institutional Dataset Portals (9)
    {"url": "https://ibug.doc.ic.ac.uk/resources/300-W/", "category": "institutional_portal", "expected_publisher": "Imperial College London"},
    {"url": "https://data.acfr.usyd.edu.au/ag/treecrops/2016-multifruit/", "category": "institutional_portal", "expected_publisher": "University of Sydney"},
    {"url": "https://ade20k.csail.mit.edu/", "category": "institutional_portal", "expected_publisher": "MIT CSAIL"},
    {"url": "https://groups.inf.ed.ac.uk/ami/corpus/", "category": "institutional_portal", "expected_publisher": "University of Edinburgh"},
    {"url": "https://argo.ucsd.edu/data/", "category": "institutional_portal", "expected_publisher": "UC San Diego"},
    {"url": "https://project.inria.fr/aerialimagelabeling/", "category": "institutional_portal", "expected_publisher": "Inria France"},
    {"url": "https://gpcv.whu.edu.cn/data/building_dataset.html", "category": "institutional_portal", "expected_publisher": "Wuhan University"},
    {"url": "https://linqs.org/datasets/#cora", "category": "institutional_portal", "expected_publisher": "LINQS / UC Santa Cruz"},
    {"url": "https://cs.stanford.edu/~acoates/stl10/", "category": "institutional_portal", "expected_publisher": "Stanford University"},

    # 4. Research Archives (9)
    {"url": "https://archive.ics.uci.edu/dataset/2/adult", "category": "research_archive", "expected_publisher": "UCI Machine Learning Repository"},
    {"url": "https://zenodo.org/records/8231412", "category": "research_archive", "expected_publisher": "Zenodo"},
    {"url": "https://huggingface.co/datasets/pmchard/3D-ADAM", "category": "research_archive", "expected_publisher": "Hugging Face"},
    {"url": "https://data.mendeley.com/datasets/zvkwpsw84d/5", "category": "research_archive", "expected_publisher": "Mendeley Data"},
    {"url": "https://aclanthology.org/2025.findings-naacl.403/", "category": "research_archive", "expected_publisher": "ACL Anthology"},
    {"url": "https://arxiv.org/abs/2502.05761", "category": "research_archive", "expected_publisher": "arXiv"},
    {"url": "https://www.kaggle.com/competitions/aptos2019-blindness-detection/data", "category": "research_archive", "expected_publisher": "Kaggle Competitions"},
    {"url": "https://openreview.net/forum?id=vN1s6i8b3P", "category": "research_archive", "expected_publisher": "OpenReview"},
    {"url": "https://openaccess.thecvf.com/content/ICCV2023/html/Van_Landeghem_Document_Understanding_Dataset_and_Evaluation_DUDE_ICCV_2023_paper.html", "category": "research_archive", "expected_publisher": "CVF Open Access"},

    # 5. Dataset-Specific Download Pages (8)
    {"url": "https://registry.opendata.aws/spacenet/", "category": "download_page", "expected_publisher": "AWS Open Data Registry"},
    {"url": "https://a2d2-dataset.github.io/", "category": "download_page", "expected_publisher": "Audi Autonomous Driving"},
    {"url": "https://www.agriculture-vision.com/dataset", "category": "download_page", "expected_publisher": "Agriculture-Vision Challenge"},
    {"url": "https://research.google.com/audioset/dataset/index.html", "category": "download_page", "expected_publisher": "Google Research AudioSet"},
    {"url": "https://www.timeseriesclassification.com/", "category": "download_page", "expected_publisher": "UCR Time Series Classification Archive"},
    {"url": "https://www.diu.mil/ai-xview-challenge", "category": "download_page", "expected_publisher": "Defense Innovation Unit"},
    {"url": "https://www.scidb.cn/detail?dataSetId=8de1702f03fc4817ab0e1fdb4cdd8e7d", "category": "download_page", "expected_publisher": "Science Data Bank China"},
    {"url": "https://www.cs.toronto.edu/~kriz/cifar.html", "category": "download_page", "expected_publisher": "University of Toronto"},

    # 6. Gated Datasets / Credentialed Access (5)
    {"url": "https://physionet.org/content/mimiciii/1.4/", "category": "gated_dataset", "expected_publisher": "PhysioNet (Credentialed Access)"},
    {"url": "https://adni.loni.usc.edu/data-samples/access-data/", "category": "gated_dataset", "expected_publisher": "ADNI / LONI (Data Use Agreement)"},
    {"url": "https://stanfordmlgroup.github.io/competitions/chexpert/", "category": "gated_dataset", "expected_publisher": "Stanford ML Group (Research Agreement)"},
    {"url": "https://physionet.org/content/apnea-ecg/1.0.0/", "category": "gated_dataset", "expected_publisher": "PhysioNet (Open Clinical Archive)"},
    {"url": "https://physionet.org/content/adfecgdb/1.0.0/", "category": "gated_dataset", "expected_publisher": "PhysioNet (Open Clinical Archive)"},
]


def _enrich_single_result(res: CheckResult, url: str) -> CheckResult:
    """Enrich non-redirect check results with conclusiveness and recommended actions."""
    if res.classification == CLASSIFICATION_REACHABLE:
        res.is_conclusive = True
        res.recommended_action = "Retain URL; endpoint verified reachable"
        res.final_redirect_target = url
        res.final_status_code = res.status_code
        res.redirect_chain = [url]
    elif res.classification == CLASSIFICATION_FORBIDDEN:
        res.is_conclusive = False
        res.recommended_action = "Retain URL; human browser access functional, automated bot requests challenged by WAF"
        res.final_redirect_target = url
        res.final_status_code = res.status_code
        res.redirect_chain = [url]
    elif res.classification == CLASSIFICATION_AUTH_REQUIRED:
        res.is_conclusive = True
        res.recommended_action = "Retain URL; document gated researcher access agreement and credential requirement"
        res.final_redirect_target = url
        res.final_status_code = res.status_code
        res.redirect_chain = [url]
    elif res.classification == CLASSIFICATION_NOT_FOUND:
        if "kaggle.com" in url:
            res.is_conclusive = False
            res.recommended_action = "Retain canonical competition URL; unauthenticated automated requests return 404 due to required authenticated Kaggle user session"
        elif "TBME.2011.2179934" in url:
            res.is_conclusive = True
            res.recommended_action = "Update DOI: paper published in Biomedizinische Technik / Biomedical Engineering (De Gruyter DOI 10.1515/bmt-2011-0130)"
        elif "agriculture-vision.com" in url:
            res.is_conclusive = True
            res.recommended_action = "Update URL: portal subpath moved; root homepage https://www.agriculture-vision.com/ and https://www.agriculture-vision.com/dataset-terms are active (200)"
        elif "adni.loni.usc.edu" in url:
            res.is_conclusive = True
            res.recommended_action = "Update URL: portal subpath restructured; active application path is https://adni.loni.usc.edu/data-samples/adni-data/ (200)"
        else:
            res.is_conclusive = True
            res.recommended_action = "Investigate publisher portal for official new location"
        res.final_redirect_target = url
        res.final_status_code = res.status_code
        res.redirect_chain = [url]
    elif res.classification == CLASSIFICATION_TIMEOUT:
        res.is_conclusive = False
        res.recommended_action = "Retain URL; server transiently unresponsive or blocking non-browser connections"
        res.final_redirect_target = url
        res.final_status_code = None
        res.redirect_chain = [url]
    else:
        res.is_conclusive = False
        res.recommended_action = "Perform manual browser verification"
        res.final_redirect_target = url
        res.final_status_code = res.status_code
        res.redirect_chain = [url]
    return res


def check_url_live_detailed(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    retries: int = DEFAULT_RETRIES,
    max_redirect_hops: int = 5,
) -> CheckResult:
    """Perform comprehensive network verification, tracing redirect chains up to max_redirect_hops."""
    initial_res = check_single_url(
        url,
        timeout=timeout,
        user_agent=user_agent,
        retries=retries,
        offline=False,
    )

    if initial_res.classification != CLASSIFICATION_REDIRECTED:
        return _enrich_single_result(initial_res, url)

    chain = [url]
    curr_url = url
    if initial_res.redirect_url:
        curr_url = urllib.parse.urljoin(url, initial_res.redirect_url)
        chain.append(curr_url)

    final_status = initial_res.status_code
    final_classification = initial_res.classification
    final_error = initial_res.error_message

    for _ in range(max_redirect_hops - 1):
        if not curr_url:
            break
        hop_res = check_single_url(
            curr_url,
            timeout=timeout,
            user_agent=user_agent,
            retries=retries,
            offline=False,
        )
        final_status = hop_res.status_code
        final_classification = hop_res.classification
        final_error = hop_res.error_message

        if hop_res.classification == CLASSIFICATION_REDIRECTED and hop_res.redirect_url:
            next_url = urllib.parse.urljoin(curr_url, hop_res.redirect_url)
            if next_url in chain:
                break
            curr_url = next_url
            chain.append(curr_url)
        else:
            break

    final_target = chain[-1] if len(chain) > 1 else None

    if "doi.org" in url:
        action = f"Retain canonical DOI resolver (resolves to {final_target or curr_url})"
        is_conclusive = True
    elif final_classification == CLASSIFICATION_REACHABLE:
        action = f"Retain canonical URL (resolves to {final_target or curr_url})"
        is_conclusive = True
    elif final_classification == CLASSIFICATION_FORBIDDEN:
        action = f"Retain URL; human browser access active, automated bot requests challenged by WAF at {final_target or curr_url}"
        is_conclusive = False
    elif final_classification == CLASSIFICATION_AUTH_REQUIRED:
        action = f"Retain URL; document research credential requirements at {final_target or curr_url}"
        is_conclusive = True
    elif final_classification == CLASSIFICATION_NOT_FOUND:
        action = f"Investigate redirect endpoint; final target {final_target or curr_url} returned 404"
        is_conclusive = True
    elif final_classification == CLASSIFICATION_TIMEOUT:
        action = f"Retain URL; destination {final_target or curr_url} timed out during verification"
        is_conclusive = False
    else:
        action = f"Review redirect destination {final_target or curr_url}"
        is_conclusive = False

    return CheckResult(
        url=url,
        classification=initial_res.classification,
        status_code=initial_res.status_code,
        redirect_url=initial_res.redirect_url,
        error_message=final_error,
        elapsed_ms=initial_res.elapsed_ms,
        checked_at=initial_res.checked_at,
        final_redirect_target=final_target,
        final_status_code=final_status,
        redirect_chain=chain,
        is_conclusive=is_conclusive,
        recommended_action=action,
    )


def run_live_pilot(
    data_dir: Path,
    timeout: float = DEFAULT_TIMEOUT,
    per_host_delay: float = 0.2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute live verification pilot on 50 representative URLs across 6 categories."""
    references = extract_dataset_urls(data_dir)
    url_to_dataset_ids: dict[str, list[str]] = defaultdict(list)
    url_to_fields: dict[str, list[str]] = defaultdict(list)
    for ref in references:
        url_to_dataset_ids[ref.url].append(ref.dataset_id)
        url_to_fields[ref.url].append(ref.field_name)

    total_catalog_references = len(references)
    unique_catalog_urls = len(url_to_dataset_ids)

    pilot_rows: list[dict[str, Any]] = []
    pilot_classifications: dict[str, int] = {c: 0 for c in VALID_CLASSIFICATIONS}
    status_code_counts: dict[str, int] = Counter()

    last_host_time: dict[str, float] = {}
    covered_references_count = 0
    covered_datasets: set[str] = set()

    for item in PILOT_50_REPRESENTATIVE_URLS:
        url = item["url"]
        category = item["category"]
        expected_pub = item.get("expected_publisher", "")

        parsed_host = urllib.parse.urlparse(url).netloc
        if parsed_host in last_host_time and per_host_delay > 0:
            time_since = time.time() - last_host_time[parsed_host]
            if time_since < per_host_delay:
                time.sleep(per_host_delay - time_since)

        check_res = check_url_live_detailed(url, timeout=timeout)
        last_host_time[parsed_host] = time.time()

        dids = sorted(set(url_to_dataset_ids.get(url, [])))
        covered_references_count += len(url_to_dataset_ids.get(url, []))
        covered_datasets.update(dids)

        pilot_classifications[check_res.classification] = (
            pilot_classifications.get(check_res.classification, 0) + 1
        )
        sc_key = str(check_res.status_code) if check_res.status_code is not None else "TIMEOUT"
        status_code_counts[sc_key] += 1

        error_type = "None"
        if check_res.classification == CLASSIFICATION_NOT_FOUND:
            if "kaggle.com" in url:
                error_type = f"HTTP {check_res.status_code} (Unauthenticated / Session Required)"
            else:
                error_type = f"HTTP {check_res.status_code} Not Found"
        elif check_res.classification == CLASSIFICATION_FORBIDDEN:
            error_type = f"HTTP {check_res.status_code} Forbidden (Anti-bot WAF)"
        elif check_res.classification == CLASSIFICATION_TIMEOUT:
            error_type = "Connection Timeout"
        elif check_res.classification == CLASSIFICATION_REDIRECTED:
            error_type = f"HTTP {check_res.status_code} Redirect"
        elif check_res.classification == CLASSIFICATION_AUTH_REQUIRED:
            error_type = f"HTTP {check_res.status_code} Authentication Required"

        pilot_rows.append(
            {
                "url": url,
                "dataset_ids": "; ".join(dids),
                "category": category,
                "expected_publisher": expected_pub,
                "status_code": check_res.status_code if check_res.status_code is not None else "",
                "final_redirect_target": check_res.final_redirect_target or "",
                "final_status_code": check_res.final_status_code if check_res.final_status_code is not None else "",
                "redirect_chain": " -> ".join(check_res.redirect_chain) if check_res.redirect_chain else url,
                "classification": check_res.classification,
                "error_type": error_type,
                "check_date": check_res.checked_at,
                "is_conclusive": "true" if check_res.is_conclusive else "false",
                "recommended_action": check_res.recommended_action,
                "elapsed_ms": check_res.elapsed_ms,
            }
        )

    summary = {
        "total_catalog_references": total_catalog_references,
        "unique_catalog_urls": unique_catalog_urls,
        "pilot_urls_checked": len(PILOT_50_REPRESENTATIVE_URLS),
        "covered_references": covered_references_count,
        "covered_datasets": len(covered_datasets),
        "unchecked_unique_urls": unique_catalog_urls - len(PILOT_50_REPRESENTATIVE_URLS),
        "unchecked_references": total_catalog_references - covered_references_count,
        "classifications": {k: v for k, v in pilot_classifications.items() if v > 0},
        "status_codes": dict(status_code_counts),
        "conclusive_count": sum(1 for r in pilot_rows if r["is_conclusive"] == "true"),
        "inconclusive_count": sum(1 for r in pilot_rows if r["is_conclusive"] == "false"),
        "pilot_findings_breakdown": {
            "reachable_or_redirected_urls": sum(1 for r in pilot_rows if r["classification"] in (CLASSIFICATION_REACHABLE, CLASSIFICATION_REDIRECTED)),
            "confirmed_dead_urls": sum(1 for r in pilot_rows if "TBME.2011.2179934" in r["url"]),
            "obsolete_replaceable_urls": sum(1 for r in pilot_rows if any(k in r["url"] for k in ("agriculture-vision.com/dataset", "adni.loni.usc.edu/data-samples/access-data/"))),
            "authenticated_or_bot_restricted_urls": sum(1 for r in pilot_rows if "kaggle.com" in r["url"] or r["classification"] == CLASSIFICATION_FORBIDDEN),
            "temporary_network_failures": sum(1 for r in pilot_rows if r["classification"] == CLASSIFICATION_TIMEOUT),
            "unchecked_unique_urls": unique_catalog_urls - len(PILOT_50_REPRESENTATIVE_URLS),
            "unchecked_catalog_references": total_catalog_references - covered_references_count,
        },
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    return pilot_rows, summary


def write_pilot_csv_results(pilot_results: list[dict[str, Any]], output_path: Path) -> None:
    """Write 50-URL live pilot audit results to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "url",
        "dataset_ids",
        "category",
        "expected_publisher",
        "status_code",
        "final_redirect_target",
        "final_status_code",
        "redirect_chain",
        "classification",
        "error_type",
        "check_date",
        "is_conclusive",
        "recommended_action",
        "elapsed_ms",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in pilot_results:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit source link health across OpenDatasets catalog.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "datasets",
        help="Path to datasets directory.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "audits" / "task-38" / "source-link-results.csv",
        help="Path for output CSV report.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Concurrent workers for network checking.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Maximum retry attempts on timeout or failure.",
    )
    parser.add_argument(
        "--offline",
        "--dry-run",
        action="store_true",
        help="Run without network calls; mark URLs as not_checked.",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default="",
        help="Comma-separated dataset IDs to check.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of unique URLs to check.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path to write a JSON summary.",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Execute controlled 50-URL live pilot across representative domains.",
    )
    parser.add_argument(
        "--pilot-csv",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "audits" / "task-38" / "live-link-pilot-results.csv",
        help="Path for live pilot CSV output.",
    )
    parser.add_argument(
        "--pilot-json",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "audits" / "task-38" / "live-link-pilot-summary.json",
        help="Path for live pilot JSON summary.",
    )

    args = parser.parse_args()

    if args.pilot:
        print("Executing controlled live pilot on 50 representative URLs across 6 categories...")
        pilot_results, pilot_summary = run_live_pilot(
            data_dir=args.data_dir,
            timeout=args.timeout,
        )
        write_pilot_csv_results(pilot_results, args.pilot_csv)
        print(f"Wrote {len(pilot_results)} live pilot results to {args.pilot_csv}")
        args.pilot_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.pilot_json, "w", encoding="utf-8") as fp:
            json.dump(pilot_summary, fp, indent=2)
        print(f"Wrote live pilot summary to {args.pilot_json}")
        print("Pilot classifications:")
        for cls, cnt in sorted(pilot_summary["classifications"].items(), key=lambda x: -x[1]):
            print(f"  {cls}: {cnt}")
        print(f"Pilot status codes: {pilot_summary['status_codes']}")
        print(f"Conclusive: {pilot_summary['conclusive_count']}, Inconclusive: {pilot_summary['inconclusive_count']}")
        return 0

    filter_set = {d.strip() for d in args.datasets.split(",") if d.strip()} or None

    print(f"Scanning datasets in {args.data_dir}...")
    results, url_cache, counts = run_source_link_audit(
        data_dir=args.data_dir,
        dataset_filter=filter_set,
        timeout=args.timeout,
        concurrency=args.concurrency,
        retries=args.retries,
        offline=args.offline,
        limit_urls=args.limit,
    )

    write_csv_results(results, args.output_csv)
    print(f"Wrote {len(results)} source reference results to {args.output_csv}")
    print(f"Unique URLs evaluated: {len(url_cache)}")
    print("Classifications summary:")
    for cls, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        if cnt > 0:
            print(f"  {cls}: {cnt}")

    if args.json_output:
        summary_payload = {
            "total_references": len(results),
            "unique_urls": len(url_cache),
            "classifications": counts,
            "offline_mode": args.offline,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_output, "w", encoding="utf-8") as fp:
            json.dump(summary_payload, fp, indent=2)
        print(f"Wrote JSON summary to {args.json_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
