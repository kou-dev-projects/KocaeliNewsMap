"""
Cloudflare / bot-engeli tespit yardımcıları.

Tüm scraper modüllerinde _looks_like_blocked() tekrarlanıyordu.
Bu modül tek merkezi bir fonksiyonla yanlış pozitif riskini azaltır.
"""
from __future__ import annotations


def looks_like_blocked(html: str) -> bool:
    """
    HTML'in bir Cloudflare/bot-engeli sayfası olup olmadığını kontrol eder.

    Kurallar:
    - "cf-challenge" veya "cf-chl-widget" → kesin Cloudflare
    - "just a moment" + kısa sayfa → Cloudflare bekleme sayfası
    - "your request was blocked" → WAF engeli
    - "attention required" + kısa sayfa → Cloudflare captcha
    - "challenge-platform" TEK BAŞINA yeterli DEĞİL (Daktilo CMS'de
      meşru JS asset'leri bu stringi içerir)
    """
    if not html:
        return True  # boş yanıt = engel varsay

    lowered = html.lower()
    html_len = len(html)

    # Kesin Cloudflare belirtileri
    if "cf-challenge" in lowered or "cf-chl-widget" in lowered:
        return True

    # WAF engeli
    if "your request was blocked" in lowered:
        return True

    # Kısa sayfalar — gerçek haber sayfaları 10KB+'dır
    is_short = html_len < 15_000

    if is_short and "just a moment" in lowered:
        return True

    if is_short and "attention required" in lowered:
        return True

    # "challenge-platform" sadece <div id="challenge-platform"> olarak
    # Cloudflare sayfalarında bulunur, meşru JS bundle'larında da geçer
    if is_short and 'id="challenge-platform"' in lowered:
        return True

    return False
