"""
robots.txt gate — call check_allowed() before requesting ANY path on ANY
Tier 2 or Tier 3 domain. Brief §5.2: "Parse it per source before writing a
single line of scraper code. Where it disallows a path, we do not crawl
that path." This module makes that a runtime check, not a promise.

Usage:
    from robots_check import check_allowed
    if not check_allowed("https://www.goindigo.in/some/path"):
        raise RuntimeError("robots.txt disallows this path — do not proceed")
"""
from __future__ import annotations

import logging
import urllib.robotparser as robotparser
from functools import lru_cache
from urllib.parse import urlparse

import config

logger = logging.getLogger("sih26056.robots_check")

USER_AGENT = "SIH26056AirfareBot"  # descriptive, per brief §5.2 "Identify ourselves"


@lru_cache(maxsize=32)
def _parser_for_domain(scheme: str, domain: str) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser()
    rp.set_url(f"{scheme}://{domain}/robots.txt")
    rp.read()
    return rp


def check_allowed(url: str, user_agent: str = USER_AGENT) -> bool:
    parsed = urlparse(url)
    scheme = parsed.scheme
    domain = parsed.netloc

    # Skip robots check for local mock endpoints during dev/hackathon
    if domain.startswith("localhost") or domain.startswith("127.0.0.1"):
        return True

    try:
        rp = _parser_for_domain(scheme, domain)
        allowed = rp.can_fetch(user_agent, url)
    except Exception:
        logger.exception("Could not read/parse robots.txt for %s -- treating as DISALLOWED (fail closed)", domain)
        return False

    if not allowed:
        logger.warning("robots.txt DISALLOWS %s for UA=%s -- do not request this.", url, user_agent)
    return allowed
