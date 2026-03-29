from app.scrapers.base.crawl_api_client import _looks_like_block_page


def test_challenge_platform_token_alone_is_not_blocked():
    html = (
        "<html><head><script>const marker='challenge-platform';</script></head><body>"
        + ("x" * 16000)
        + "</body></html>"
    )
    assert _looks_like_block_page(html) is False


def test_short_page_with_challenge_platform_id_is_blocked():
    html = '<html><body><div id="challenge-platform"></div></body></html>'
    assert _looks_like_block_page(html) is True
