from __future__ import annotations

from app.domain.enums import NewsCategory


CATEGORY_EXEMPLARS: dict[NewsCategory, tuple[str, ...]] = {
    NewsCategory.TRAFIK_KAZASI: (
        "D-100 karayolunda iki otomobil carpisti, yaralilar hastaneye kaldirildi.",
        "TEM otoyolunda zincirleme trafik kazasi nedeniyle ulasim bir sure aksadi.",
        "Motosiklet ile otomobilin karistigi kazada surucu yaralandi.",
        "Kontrolden cikan kamyon bariyerlere carpti, yol trafige kapandi.",
        "Kavsakta iki arac carpisirken ekipler olay yerine sevk edildi.",
    ),
    NewsCategory.YANGIN: (
        "Fabrikada yangin cikti, itfaiye alevlere mudahale etti.",
        "Ev yangininda duman nedeniyle bina tahliye edildi.",
        "Orman yangini ruzgarin etkisiyle buyudu, ekipler mudahale ediyor.",
        "Depoda cikan yangin kisa surede kontrol altina alindi.",
        "Arac yangininda alevler tum otomobili sardi.",
    ),
    NewsCategory.HIRSIZLIK: (
        "Hirsizlik suphelisi polis ekiplerince yakalandi.",
        "Dolandiricilik vakasinda milyonlarca lira kaybeden vatandas sikayetci oldu.",
        "Evden ziynet esyasi calan hirsiz kameraya yakalandi.",
        "Is yerinden para calan supheli gozaltina alindi.",
        "Telefonla dolandirdigi iddia edilen kisi tutuklandi.",
    ),
    NewsCategory.ELEKTRIK_KESINTISI: (
        "Planli elektrik kesintisi nedeniyle mahallede enerji verilemeyecek.",
        "SEDAŞ ariza nedeniyle elektrik kesintisi yasandigini duyurdu.",
        "Trafo arizasi sonrasi sokaklar karanlikta kaldi.",
        "Bakim calismasi sebebiyle enerji kesintisi uygulanacak.",
        "Dagitim sirketi elektrik arizasini gidermek icin sahada calisiyor.",
    ),
    NewsCategory.KULTUREL_ETKINLIK: (
        "Kutuphane Haftasi kapsaminda soylesi ve imza gunu duzenlendi.",
        "Festivalde konser ve tiyatro gosterileri buyuk ilgi gordu.",
        "Farkindalik gunu icin anlamli etkinlik ve ogrenci bulusmasi yapildi.",
        "Muzede sergi acilisi ve kultur sanat programi gerceklestirildi.",
        "Belediye tarafindan duzenlenen atolyeye gencler yogun katilim sagladi.",
    ),
    NewsCategory.UNKNOWN: (
        "Kocaelispor yonetimi taraftara ozel banka karti projesi icin gorusuyor.",
        "MHP ilce baskani mahalle baskanligina yeni gorevlendirme yapti.",
        "Fabrikada meydana gelen is kazasinda isci makineye sikisti.",
        "Belediye meclisinde faaliyet raporu ve butce teklifleri gorusuldu.",
        "Mahkemede gorulen davada saniklar hakkinda tutuklama ve tahliye karari verildi.",
        "Sendika temsilcisi ucret teklifine tepki gosteren aciklamalarda bulundu.",
        "Kulubun sponsorluk, proje ve gelir modeli calismalari kamuoyuna duyuruldu.",
    ),
}
