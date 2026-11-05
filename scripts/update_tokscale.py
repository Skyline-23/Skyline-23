"""Refresh GitHub-hosted cards without replacing them with failed API responses."""

from pathlib import Path
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ASSETS = Path(__file__).resolve().parents[1] / "assets"
MAX_BYTES = 1_000_000
SVG = "{http://www.w3.org/2000/svg}"


def fetch_card(theme: str) -> bytes:
    query = urlencode({"view": "3d", "color": "blue", "theme": theme})
    request = Request(
        f"https://tokscale.ai/api/embed/Skyline-23/svg?{query}",
        headers={"User-Agent": "Skyline-23-profile-card"},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                if response.headers.get_content_type() != "image/svg+xml":
                    raise ValueError("Tokscale did not return an SVG image")
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Tokscale image exceeds the size limit")
            root = ET.fromstring(data)
            if (
                root.tag != f"{SVG}svg"
                or root.get("data-template") != "3d"
                or root.get("viewBox") != "0 0 680 482"
                or root.get("width") != "680"
                or root.get("height") != "482"
                or "@Skyline-23" not in root.get("aria-label", "")
                or root.find(f"{SVG}g[@data-contribution-grid='3d']") is None
            ):
                raise ValueError("Tokscale returned an unexpected profile card")
            return data
        except (URLError, TimeoutError, ValueError, ET.ParseError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Tokscale card download failed")


def main() -> None:
    # Validate both themes before changing either last-known-good snapshot.
    cards = {theme: fetch_card(theme) for theme in ("light", "dark")}
    ASSETS.mkdir(parents=True, exist_ok=True)
    for theme, data in cards.items():
        path = ASSETS / f"tokscale-{theme}.svg"
        path.write_bytes(data)
        print(f"Updated {path.name} ({len(data):,} bytes)")


if __name__ == "__main__":
    main()
