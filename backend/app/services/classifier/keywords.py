from app.services.classifier.schemas import NewsCategory

CATEGORY_KEYWORDS: dict[NewsCategory, tuple[str, ...]] = {
    NewsCategory.TRAFIK_KAZASI: (
        # Kaza çeşitleri
        "kaza", "çarpışma", "zincirleme", "takla", "devrildi", "devrilme",
        "çarptı", "çarpıştı", "bariyere", "refüje", "hendek",
        # Araç tipleri — kazaya özgü bağlam
        "otomobil", "kamyon", "motosiklet", "bisiklet", "tır",
        "minibüs", "servis", "ambulans çağrıldı",
        # Sonuçlar
        "yaralı", "yaralandı", "hayatını kaybetti", "can verdi",
        "hastaneye kaldırıldı", "sedye",
        # Trafik durumu
        "trafik durdu", "yol kapandı", "kapanan yol", "tıkandı",
        "d100", "tem", "e5", "karayolu",
    ),

    NewsCategory.YANGIN: (
        # Yangın çeşitleri
        "yangın", "alev", "tutuştu", "yandı", "yanıyor",
        "orman yangını", "bina yangını", "araç yangını",
        "fabrika yangını", "daire yangını", "iş yeri yangını",
        # Müdahale
        "itfaiye", "söndürme", "müdahale", "hortum",
        "yangın tüpü", "köpüklü",
        # Sonuçlar
        "duman", "kül", "hasar", "enkaz",
        "tahliye edildi", "mahsur kaldı",
    ),

    NewsCategory.HIRSIZLIK: (
        # Suç çeşitleri
        "hırsızlık", "hırsız", "çalındı", "çalınma",
        "soygun", "gasp", "kapkaç", "dolandırıcılık",
        "dolandırıcı", "sahte",
        # Nesne
        "araç çalındı", "motosiklet çalındı", "para çalındı",
        "kıymetli eşya", "kasa",
        # Eylem
        "yakalandı", "gözaltına alındı", "tutuklandı",
        "suçüstü", "operasyon",
        # Yer
        "iş yeri soyuldu", "ev soyuldu", "banka soygunu",
    ),

    NewsCategory.ELEKTRIK_KESINTISI: (
        # Kesinti
        "elektrik kesintisi", "elektrik kesildi", "elektrik arızası",
        "enerji kesintisi", "kesinti", "planlı kesinti",
        # Kurumlar
        "kkedaş", "ayedaş", "toroslar edaş", "tedaş",
        "enerji şirketi", "dağıtım şirketi",
        # Ekipman
        "trafo", "trafo merkezi", "elektrik direği",
        "hat arızası", "kablo",
        # Durum
        "karanlıkta kaldı", "ışıklar söndü", "jeneratör",
        "yedek güç", "enerji yok",
    ),

    NewsCategory.KULTUREL_ETKINLIK: (
        # Etkinlik tipleri
        "konser", "festival", "sergi", "tiyatro", "sinema",
        "etkinlik", "gösteri", "performans",
        # Organizasyon
        "kutlama", "anma", "anma töreni",
        "mezuniyet", "diploma",
        # Kültür
        "müze", "kültür merkezi", "sanat galerisi",
        "resital", "sempozyum", "kongre", "konferans",
        # Spor etkinliği
        "turnuva", "şampiyona", "yarışma",
    ),
}