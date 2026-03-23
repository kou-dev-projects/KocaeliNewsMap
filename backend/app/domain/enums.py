from enum import Enum


class NewsCategory(str, Enum):
    TRAFIK_KAZASI = "trafik_kazasi"
    YANGIN = "yangin"
    HIRSIZLIK = "hirsizlik"
    ELEKTRIK_KESINTISI = "elektrik_kesintisi"
    KULTUREL_ETKINLIK = "kulturel_etkinlik"
    UNKNOWN = "unknown"


class KocaeliDistrict(str, Enum):
    IZMIT = "izmit"
    GEBZE = "gebze"
    DARICA = "darica"
    GOLCUK = "golcuk"
    KORFEZ = "korfez"
    KARTEPE = "kartepe"
    BASISKELE = "basiskele"
    CAYIROVA = "cayirova"
    DILOVASI = "dilovasi"
    KANDIRA = "kandira"
    KARAMURSEL = "karamursel"
    DERINCE = "derince"
