from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_SEMVER = re.compile(r"(?<![A-Za-z])v?(\d+(?:\.\d+){0,3})(?:[-+][0-9A-Za-z.-]+)?$")
_CACHE_TTL = 900
_CACHE: dict[str, tuple[float, dict[str, object]]] = {}


@dataclass(frozen=True)
class VersionCheck:
    current: str | None
    latest: str | None
    source: str | None
    state: str


def _parse_image(image: str) -> tuple[str, str] | None:
    value = image.strip()
    if not value or value.startswith("sha256:") or "/" not in value:
        return None
    repository, _, tag = value.rpartition(":")
    if "/" not in repository:
        repository = f"library/{repository}"
    return repository, tag or "latest"


def _version_key(tag: str) -> tuple[int, ...] | None:
    match = _SEMVER.search(tag)
    return tuple(int(part) for part in match.group(1).lstrip("v").split(".")) if match else None


def _lookup(repository: str) -> list[str]:
    request = Request(
        f"https://registry.hub.docker.com/v2/repositories/{repository}/tags?page_size=100",
        headers={"Accept": "application/json", "User-Agent": "homelab-monitor/1.0"},
    )
    with urlopen(request, timeout=5) as response:
        payload = json.load(response)
    return [str(item.get("name", "")) for item in payload.get("results", [])]


def check_image(image: str) -> VersionCheck:
    parsed = _parse_image(image)
    if not parsed:
        return VersionCheck(None, None, None, "unknown")
    repository, current = parsed
    now = time.monotonic()
    cached = _CACHE.get(repository)
    try:
        tags = cached[1]["tags"] if cached and now - cached[0] < _CACHE_TTL else _lookup(repository)
        if not cached or now - cached[0] >= _CACHE_TTL:
            _CACHE[repository] = (now, {"tags": tags})
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return VersionCheck(current, None, "docker-hub", "unknown")
    candidates = [(tag, _version_key(tag)) for tag in tags if _version_key(tag) is not None]
    excluded_tokens = ("nightly", "nightlies", "unstable", "development", "develop", "beta", "alpha", "rc", "preview", "arm64", "arm32", "armhf", "amd64", "aarch64", "s390x", "ppc64", "sha-", "edge", "latest", "pr-")
    candidates = [(tag, key) for tag, key in candidates if "_" not in tag and not any(token in tag.lower() for token in excluded_tokens)]
    latest = max(candidates, key=lambda item: item[1])[0] if candidates else None
    if current == "latest":
        state = "unknown"
    elif latest is None:
        state = "unknown"
    else:
        current_key = _version_key(current)
        state = "unknown" if current_key is None else ("up_to_date" if current_key >= _version_key(latest) else "update_available")
    return VersionCheck(current, latest, "docker-hub", state)


async def lookup_resources(resources: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    images = [(str(resource["id"]), str(resource["metadata"].get("image", ""))) for resource in resources if resource.get("kind") == "container" and isinstance(resource.get("metadata"), dict) and resource["metadata"].get("image")]
    results = await asyncio.gather(*(asyncio.to_thread(check_image, image) for _, image in images))
    return {resource_id: {"current_version": result.current, "latest_version": result.latest, "version_source": result.source, "update_status": result.state} for (resource_id, _), result in zip(images, results, strict=True)}
