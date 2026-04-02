from app.services.classifier.schemas import NewsCategory


CATEGORY_KEYWORDS: dict[NewsCategory, tuple[str, ...]] = {
    NewsCategory.TRAFIK_KAZASI: (
        # Güçlü kaza sinyalleri
        "trafik kazası",
        "zincirleme kaza",
        "maddi hasarlı kaza",
        "yaralanmalı kaza",
        "ölümlü kaza",
        "kaza",
        "çarpışma",
        "çarptı",
        "çarpıştı",
        "takla",
        "devrildi",
        "devrilme",
        # Yol / güzergâh bağlamı
        "yol kapandı",
        "trafik durdu",
        "kapanan yol",
        "tıkandı",
        "d100",
        "e5",
        "karayolu",
        "tem otoyolu",
        "tem yolu",
        "tem bağlantı yolu",
    ),

    NewsCategory.YANGIN: (
        # Yangın türleri
        "yangın",
        "alev",
        "tutuştu",
        "yandı",
        "yanıyor",
        "orman yangını",
        "bina yangını",
        "araç yangını",
        "fabrika yangını",
        "daire yangını",
        "iş yeri yangını",
        # Müdahale
        "itfaiye",
        "söndürme",
        "müdahale",
        "hortum",
        "yangın tüpü",
        "köpüklü",
        # Sonuçlar
        "duman",
        "kül",
        "enkaz",
        "tahliye edildi",
        "mahsur kaldı",
    ),

    NewsCategory.HIRSIZLIK: (
        # Suç türleri
        "hırsızlık",
        "hırsız",
        "çalındı",
        "çalınma",
        "soygun",
        "gasp",
        "kapkaç",
        "dolandırıcılık",
        "dolandırıcı",
        # Nesne / olay kalıpları
        "araç çalındı",
        "motosiklet çalındı",
        "para çalındı",
        "ev soyuldu",
        "iş yeri soyuldu",
        "banka soygunu",
    ),

    NewsCategory.ELEKTRIK_KESINTISI: (
        # Güçlü kesinti kalıpları
        "elektrik kesintisi",
        "elektrik kesildi",
        "elektrik arızası",
        "enerji kesintisi",
        "planlı kesinti",
        # Kurum / altyapı
        "kkedaş",
        "ayedaş",
        "toroslar edaş",
        "tedaş",
        "enerji şirketi",
        "dağıtım şirketi",
        "trafo",
        "trafo merkezi",
        "elektrik direği",
        "hat arızası",
        # Durum
        "karanlıkta kaldı",
        "ışıklar söndü",
        "jeneratör",
        "enerji yok",
    ),

    NewsCategory.KULTUREL_ETKINLIK: (
        # Kültür / sanat etkinlikleri
        "konser",
        "festival",
        "sergi",
        "tiyatro",
        "sinema",
        "kültürel etkinlik",
        "gösteri",
        # Organizasyon
        "kutlama",
        "anma töreni",
        "mezuniyet",
        "diploma töreni",
        # Kültür kurumları
        "müze",
        "kültür merkezi",
        "sanat galerisi",
        "resital",
        "sempozyum",
        "kongre",
        "konferans",
        # Etkinlik niteliği taşıyan spor organizasyonları
        "turnuva",
        "şampiyona",
        "yarışma",
    ),
}
