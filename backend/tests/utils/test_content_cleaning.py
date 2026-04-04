from app.utils.content_cleaning import clean_news_text


def test_clean_news_text_removes_gallery_prompt_prefix():
    value = "Haber albümü için resme tıklayın - + Çayırova'da yeni spor lisesi yükseliyor."

    assert clean_news_text(value) == "Çayırova'da yeni spor lisesi yükseliyor."


def test_clean_news_text_removes_zoom_prompt():
    value = "Büyütmek için resme tıklayın - + Kocaeli'de yağmur etkili oldu."

    assert clean_news_text(value) == "Kocaeli'de yağmur etkili oldu."


def test_clean_news_text_keeps_normal_content():
    value = "Kocaeli Büyükşehir Belediyesi yeni proje tanıtımını yaptı."

    assert clean_news_text(value) == value
