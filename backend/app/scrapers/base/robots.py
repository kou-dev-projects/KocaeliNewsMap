import requests
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


class RobotsChecker:
    def __init__(
        self,
        user_agent: str = "*",
        timeout_s: float = 10.0,
        strict: bool = False,
    ):
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.strict = strict
        self._cache: dict[str, RobotFileParser | None] = {}

    def _robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(base, "/robots.txt")

    def _fetch_and_parse(self, robots_url: str) -> RobotFileParser | None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get(
                robots_url,
                headers=headers,
                timeout=self.timeout_s,
                allow_redirects=True,
            )
        except Exception:
            return None

        if response.status_code != 200:
            return None

        rp = RobotFileParser()
        rp.parse(response.text.splitlines())
        return rp

    def can_fetch(self, url: str) -> tuple[bool, str]:
        robots_url = self._robots_url(url)

        if robots_url not in self._cache:
            self._cache[robots_url] = self._fetch_and_parse(robots_url)

        parser = self._cache[robots_url]

        if parser is None:
            if self.strict:
                return False, f"robots.txt could not be verified: {robots_url}"
            return True, f"robots.txt could not be verified: {robots_url}"

        allowed = parser.can_fetch(self.user_agent, url)
        if allowed:
            return True, f"allowed by robots.txt: {robots_url}"

        return False, f"disallowed by robots.txt: {robots_url}"