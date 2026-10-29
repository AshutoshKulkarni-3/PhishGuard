"""
PhishGuard — URL Feature Extraction
=====================================
Extracts a fixed-length vector of lexical and structural features from a raw
URL string.  No network requests are ever made.  Features are computed purely
from the URL text itself.

Public API
----------
    FEATURE_NAMES : list[str]
        Ordered list of feature names — the single source of truth.
        Both training and prediction must use this ordering.

    extract_features(url: str) -> dict[str, float | int]
        Extract features from a single URL string.
        Malformed or empty URLs return a zero-vector (all features = 0) so
        that the pipeline never crashes on bad input.

    extract_features_df(urls) -> pd.DataFrame
        Batch-extract features from an iterable of URLs.
        Returns a DataFrame with columns == FEATURE_NAMES.

Limitations (URL-only analysis)
--------------------------------
  1. Legitimate-looking URLs can still host phishing pages; feature values
     alone cannot prove or disprove malicious intent.
  2. IP-address hostnames are statistically more common in phishing but are
     also used by many legitimate internal/CDN services.
  3. HTTPS alone does not guarantee safety; many phishing sites use valid
     TLS certificates.
  4. Keyword matching is based on a static list and cannot account for
     obfuscated or misspelled keywords (e.g. "l0gin", "verìfy").
  5. URL shorteners collapse all structural signal into a short token.
  6. Internationalised domain names (IDN / punycode) may require additional
     decoding before features reflect their true structure.
  7. No temporal or reputation signals (domain age, WHOIS, blacklists) are
     included because they require external API calls.
  8. Feature values for a URL depend only on its text — the same URL always
     produces the same feature vector regardless of when it is evaluated.
"""

import math
import re
import string
from collections import Counter
from typing import Iterable
from urllib.parse import parse_qs, urlparse, urlunparse

import pandas as pd
import tldextract

# ── tldextract: use bundled TLD list only (no network calls at runtime) ──────
_TLD_EXTRACT = tldextract.TLDExtract(suffix_list_urls=None)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# The ONLY place feature names and order are defined.
# Any change here automatically propagates to training and prediction.
FEATURE_NAMES: list = [
    "url_length",           # total character count of the normalised URL string
    "hostname_length",      # character count of the hostname component
    "domain_length",        # character count of the registered domain (no subdomain/TLD)
    "tld_length",           # character count of the public suffix / TLD
    "path_length",          # character count of the path component
    "query_length",         # character count of the raw query string
    "n_dots",               # total '.' characters in the full URL
    "n_hyphens",            # total '-' characters in the full URL
    "n_underscores",        # total '_' characters in the full URL
    "n_digits",             # total digit characters [0-9] in the full URL
    "n_special_chars",      # count of: @ ! $ % ^ & * ( ) + = { } [ ] | ; ' " < > ?
    "n_slashes",            # total '/' characters in the path
    "n_query_params",       # number of distinct key=value pairs in query string
    "has_at_symbol",        # 1 if '@' appears anywhere in the URL
    "has_ip_hostname",      # 1 if the hostname is an IPv4 or IPv6 address
    "is_https",             # 1 if scheme is 'https', 0 otherwise
    "has_port",             # 1 if a port number is explicitly specified
    "n_subdomains",         # count of subdomain labels (e.g. a.b.example.com → 2)
    "has_suspicious_keyword",  # 1 if any keyword from SUSPICIOUS_KEYWORDS is present
    "url_entropy",          # Shannon entropy of the URL string (higher = more random)
    "domain_has_hyphen",    # 1 if the registered domain contains a hyphen
    "has_double_slash_in_path",  # 1 if '//' appears in the path (redirect trick)
    "path_token_count",     # number of '/' segments in the path
]

# Keywords statistically associated with phishing lures.
# NOTE: presence does not prove malice; absence does not prove safety.
SUSPICIOUS_KEYWORDS: frozenset = frozenset([
    "login", "logon", "signin", "signup", "sign-in", "sign-up",
    "verify", "verification", "validate", "validation",
    "account", "accounts", "update", "upgrade",
    "secure", "security", "confirm", "confirmation",
    "password", "passwd", "credential", "credentials",
    "auth", "authenticate", "authorization",
    "banking", "bank", "payment", "checkout", "billing",
    "suspend", "suspended", "unlock", "recover", "recovery",
    "alert", "urgent", "warning", "limited",
    "webscr", "cmd",  # PayPal-specific common phishing tokens
])

# IPv4 pattern: four octets 0-255
_IPV4_PATTERN = re.compile(
    r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
)

# IPv6 pattern (simplified: contains colons)
_IPV6_PATTERN = re.compile(r"^\[?[0-9a-fA-F:]+\]?$")

# Characters counted as "special" for the n_special_chars feature
_SPECIAL_CHARS: frozenset = frozenset("@!$%^&*()+={}[]|;'\"<>?")


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_url(raw: str) -> str:
    """
    Return a consistently normalised URL string.

    Rules
    -----
    - Strip surrounding whitespace.
    - If no scheme is present, prepend 'http://' so urlparse produces a
      non-empty netloc (without a scheme, urlparse puts everything in path).
    - Lower-case the scheme and hostname only; preserve path/query case
      because some servers treat path case as significant.
    - RFC 3986 §6.2.3: In HTTP/HTTPS URIs, an authority with an empty path
      is normalized to a path of "/" so that lexical and structural features
      consistently align between root domains and subpaths.
    """
    url = raw.strip()
    if not url:
        return ""
    # Prepend scheme if missing
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", url):
        url = "http://" + url

    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path
        if parsed.hostname and not path:
            path = "/"
        url = urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
    except Exception:
        pass

    return url


def _is_ipv4(hostname: str) -> bool:
    """Return True if hostname is a dotted-quad IPv4 address."""
    m = _IPV4_PATTERN.match(hostname)
    if not m:
        return False
    return all(0 <= int(m.group(i)) <= 255 for i in range(1, 5))


def _is_ipv6(hostname: str) -> bool:
    """Return True if hostname looks like an IPv6 address (bracketed or raw)."""
    h = hostname.strip("[]")
    return bool(_IPV6_PATTERN.match(h)) and ":" in h


def _is_ip_hostname(hostname: str) -> bool:
    """Return True if the hostname is an IP address (v4 or v6)."""
    return _is_ipv4(hostname) or _is_ipv6(hostname)


def _shannon_entropy(text: str) -> float:
    """
    Compute the Shannon entropy of a string in bits per character.

    High entropy (> ~4.0) suggests random-looking tokens common in
    generated/obfuscated URLs.  Low entropy suggests human-readable words.
    """
    if not text:
        return 0.0
    freq = Counter(text)
    length = len(text)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
        if count > 0
    )


def _zero_vector() -> dict:
    """Return a feature dict with every feature set to 0 (safe fallback)."""
    return {name: 0 for name in FEATURE_NAMES}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(url: str) -> dict:
    """
    Extract a fixed-length feature vector from a single URL string.

    Parameters
    ----------
    url : str
        A raw URL string.  May be malformed or empty.

    Returns
    -------
    dict
        Keys are exactly FEATURE_NAMES in order.
        All values are numeric (int or float).
        If the URL is empty or entirely unparseable, every value is 0.

    Notes
    -----
    - No network requests are made.
    - A prepended 'http://' scheme is used only internally for parsing;
      the is_https feature reflects the *original* scheme.
    """
    if not isinstance(url, str) or not url.strip():
        return _zero_vector()

    normalised = _normalise_url(url)

    try:
        parsed = urlparse(normalised)
        try:
            hostname = parsed.hostname or ""
        except (ValueError, Exception):
            hostname = ""
        try:
            port = parsed.port
        except (ValueError, Exception):
            port = None
        path = parsed.path or ""
        query_str = parsed.query or ""
        scheme = parsed.scheme or ""
    except Exception:
        return _zero_vector()

    # tldextract: splits into subdomain / domain / suffix
    # Uses the bundled public-suffix list; no network call.
    try:
        tld_info = _TLD_EXTRACT(normalised)
        subdomain = tld_info.subdomain             # e.g. "mail.accounts"
        domain = tld_info.domain                # e.g. "google"
        suffix = tld_info.suffix                # e.g. "com" / "co.uk"
    except Exception:
        subdomain = ""
        domain = ""
        suffix = ""

    # ── Feature computation ───────────────────────────────────────────────
    url_lower = normalised.lower()

    # Lengths
    f_url_length      = len(normalised)
    f_hostname_length = len(hostname)
    f_domain_length   = len(domain)
    f_tld_length      = len(suffix)
    f_path_length     = len(path)
    f_query_length    = len(query_str)

    # Character counts (applied to full normalised URL)
    f_n_dots        = normalised.count(".")
    f_n_hyphens     = normalised.count("-")
    f_n_underscores = normalised.count("_")
    f_n_digits      = sum(c.isdigit() for c in normalised)
    f_n_special     = sum(c in _SPECIAL_CHARS for c in normalised)

    # Path-level counts
    f_n_slashes     = path.count("/")
    path_tokens     = [t for t in path.split("/") if t]   # non-empty segments
    f_path_tokens   = len(path_tokens)

    # Query parameters
    try:
        params        = parse_qs(query_str, keep_blank_values=True)
        f_n_params    = len(params)
    except Exception:
        f_n_params    = 0

    # Binary / boolean features
    f_has_at     = int("@" in normalised)
    f_has_ip     = int(_is_ip_hostname(hostname))
    f_is_https   = int(url.strip().lower().startswith("https://") or normalised.startswith("https://"))
    f_has_port   = int(port is not None)

    # Subdomains: count labels in the subdomain part
    # e.g. subdomain="mail.accounts" → 2 subdomains
    f_n_subdomains = len([s for s in subdomain.split(".") if s]) if subdomain else 0

    # Suspicious keyword check (case-insensitive, whole-word not required —
    # many phishing paths embed keywords inside longer tokens)
    f_has_suspicious = int(
        any(kw in url_lower for kw in SUSPICIOUS_KEYWORDS)
    )

    # Shannon entropy of the full URL
    f_entropy = round(_shannon_entropy(normalised), 6)

    # Domain hyphen (e.g. "paypal-secure.com" pattern)
    f_domain_hyphen = int("-" in domain)

    # Double slash in path is sometimes used in open-redirect attacks
    f_double_slash = int("//" in path)

    # ── Assemble result in FEATURE_NAMES order ────────────────────────────
    return {
        "url_length"               : f_url_length,
        "hostname_length"          : f_hostname_length,
        "domain_length"            : f_domain_length,
        "tld_length"               : f_tld_length,
        "path_length"              : f_path_length,
        "query_length"             : f_query_length,
        "n_dots"                   : f_n_dots,
        "n_hyphens"                : f_n_hyphens,
        "n_underscores"            : f_n_underscores,
        "n_digits"                 : f_n_digits,
        "n_special_chars"          : f_n_special,
        "n_slashes"                : f_n_slashes,
        "n_query_params"           : f_n_params,
        "has_at_symbol"            : f_has_at,
        "has_ip_hostname"          : f_has_ip,
        "is_https"                 : f_is_https,
        "has_port"                 : f_has_port,
        "n_subdomains"             : f_n_subdomains,
        "has_suspicious_keyword"   : f_has_suspicious,
        "url_entropy"              : f_entropy,
        "domain_has_hyphen"        : f_domain_hyphen,
        "has_double_slash_in_path" : f_double_slash,
        "path_token_count"         : f_path_tokens,
    }


def extract_features_df(urls: Iterable) -> pd.DataFrame:
    """
    Batch-extract features from an iterable of URL strings.

    Parameters
    ----------
    urls : iterable of str
        Any iterable yielding URL strings (list, pd.Series, generator).

    Returns
    -------
    pd.DataFrame
        Shape: (n_urls, len(FEATURE_NAMES))
        Columns are exactly FEATURE_NAMES in order.
        Index is reset to 0-based integers.
    """
    rows = [extract_features(u) for u in urls]
    if not rows:
        return pd.DataFrame(columns=FEATURE_NAMES)
    df = pd.DataFrame(rows, columns=FEATURE_NAMES)
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Self-tests  (run with:  python training/feature_extraction.py)
# ─────────────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    """
    Validate feature extraction across four URL categories.
    Prints a formatted summary and asserts expected invariants.
    """

    TEST_CASES = [
        {
            "label"      : "Legitimate HTTPS",
            "url"        : "https://www.google.com/search?q=python+tutorial&hl=en",
            "assertions" : {
                "is_https"               : 1,
                "has_at_symbol"          : 0,
                "has_ip_hostname"        : 0,
                "has_suspicious_keyword" : 0,
                "n_query_params"         : 2,
            },
        },
        {
            "label"      : "Suspicious phishing-like URL",
            "url"        : "http://paypal-secure.login-verify.com/account/update?cmd=login&user=victim@mail.com",
            "assertions" : {
                "is_https"               : 0,
                "has_at_symbol"          : 1,
                "has_suspicious_keyword" : 1,
                "domain_has_hyphen"      : 1,   # registered domain is "login-verify" → contains hyphen
                "n_query_params"         : 2,
            },
        },
        {
            "label"      : "IP-address hostname",
            "url"        : "http://192.168.1.1/admin/login.php",
            "assertions" : {
                "has_ip_hostname"        : 1,
                "is_https"               : 0,
                "n_subdomains"           : 0,
                "has_suspicious_keyword" : 1,   # 'login' in path
            },
        },
        {
            "label"      : "Malformed / no scheme",
            "url"        : "not_a_real_url_!!!",
            "assertions" : {},  # just check it doesn't crash and returns 23 features
        },
        {
            "label"      : "Empty string",
            "url"        : "",
            "assertions" : {k: 0 for k in FEATURE_NAMES},
        },
        {
            "label"      : "HTTP with port and deep path",
            "url"        : "http://example.com:8080/a/b/c/d?x=1",
            "assertions" : {
                "has_port"       : 1,
                "n_query_params" : 1,
                "path_token_count": 4,
                "is_https"       : 0,
            },
        },
        {
            "label"      : "IDN / punycode-style long subdomain chain",
            "url"        : "https://accounts.mail.secure.login.phish-example.net/reset/password",
            "assertions" : {
                "is_https"               : 1,
                "n_subdomains"           : 4,
                "domain_has_hyphen"      : 1,
                "has_suspicious_keyword" : 1,
            },
        },
    ]

    SEP = "─" * 70
    print(f"\n{'═' * 70}")
    print("  PhishGuard — Feature Extraction Self-Tests")
    print(f"{'═' * 70}")
    print(f"  Total features per URL : {len(FEATURE_NAMES)}")
    print(f"  Feature names          : {FEATURE_NAMES}\n")

    all_passed = True

    for tc in TEST_CASES:
        print(SEP)
        print(f"  TEST : {tc['label']}")
        print(f"  URL  : {tc['url'][:80]}")
        feats = extract_features(tc["url"])

        # Check the result has exactly the right keys in the right order
        assert list(feats.keys()) == FEATURE_NAMES, (
            f"Feature key mismatch!\n  Expected: {FEATURE_NAMES}\n  Got: {list(feats.keys())}"
        )

        # Print all feature values in a table
        print()
        for name in FEATURE_NAMES:
            print(f"    {name:<35} = {feats[name]}")

        # Run assertions
        failures = []
        for feat, expected in tc["assertions"].items():
            actual = feats[feat]
            status = "✅" if actual == expected else "❌"
            if actual != expected:
                failures.append(f"    {feat}: expected {expected}, got {actual}")
                all_passed = False
            print(f"\n  {status} ASSERT {feat} == {expected}  (got {actual})")

        if failures:
            for f in failures:
                print(f"  FAILURE: {f}")
        else:
            print(f"\n  ✅ All {len(tc['assertions'])} assertions passed.")

    print(f"\n{'═' * 70}")

    # Batch test
    print("\n  BATCH TEST — extract_features_df()")
    urls = [tc["url"] for tc in TEST_CASES]
    df   = extract_features_df(urls)
    assert list(df.columns) == FEATURE_NAMES, "Column order mismatch in DataFrame"
    assert len(df) == len(TEST_CASES), "Row count mismatch"
    print(f"  Shape: {df.shape}  ✅")
    print(f"\n{df.to_string()}\n")

    print(f"{'═' * 70}")
    if all_passed:
        print("  ALL TESTS PASSED ✅")
    else:
        print("  SOME TESTS FAILED ❌ — review output above.")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    _run_tests()
