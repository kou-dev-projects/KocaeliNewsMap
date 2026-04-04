from __future__ import annotations

# Türkçe hal ekleri — en uzundan kısaya sıralı
# Uzun önce — "İzmit'tekiler" için "tekiler" yerine "deki" yakalanır
_CASE_SUFFIXES = (
    # Locative derivational
    "dekiler", "dakiler", "tekiler", "takiler",
    "deki", "daki", "teki", "taki",
    # Locative
    "nde", "nda", "de", "da", "te", "ta",
    # Ablative
    "nden", "ndan", "den", "dan", "ten", "tan",
    # Dative
    "ne", "na", "ye", "ya",
    # Accusative
    "ni", "nı", "nu", "nü", "yi", "yı", "yu", "yü", "i", "ı", "u", "ü",
    # Genitive
    "nin", "nın", "nun", "nün", "in", "ın", "un", "ün",
    # Instrumental
    "yle", "yla", "le", "la",
    # Plural + case
    "ler", "lar",
)

# Apostrof karakterleri — Unicode varyantları
_APOSTROPHES = ("'", "'", "`", "\u02bc")


def strip_suffixes(text: str) -> str:

    result = text.strip()

    # Apostrof varsa — önce onu böl
    for apos in _APOSTROPHES:
        if apos in result:
            parts = result.split(apos, 1)
            root = parts[0].strip()
            if root:
                return root
            break

    # Apostrof yoksa — suffix listesi ile dene
    lower = result.lower()
    for suffix in _CASE_SUFFIXES:
        if lower.endswith(suffix) and len(result) > len(suffix) + 2:
            return result[: -len(suffix)]

    return result


def generate_candidates(text: str) -> list[str]:
   
    candidates = [text]

    stripped = strip_suffixes(text)
    if stripped != text:
        candidates.append(stripped)

    # Apostrof temizlenmiş versiyon
    for apos in _APOSTROPHES:
        clean = text.replace(apos, "")
        if clean not in candidates:
            candidates.append(clean)
            stripped_clean = strip_suffixes(clean)
            if stripped_clean not in candidates:
                candidates.append(stripped_clean)

    return candidates