# 🌐 PULSE — Kocaeli Yerel Haber İzleme Sistemi

**AI-destekli, gerçek zamanlı habercilik ve coğrafi haritalama platformu**

PULSE, Kocaeli ili yerel haber kaynaklarını otomatik olarak tarayan, NLP/ML pipeline'ıyla kategorize eden ve coğrafi koordinatlara yerleştirerek interaktif bir harita üzerinde sunan tam yığın bir sivil izleme platformudur. Anlık scrape tetikleme, SSE tabanlı canlı akış ve PWA desteğiyle masaüstü kalitesinde bir web uygulaması sunar.

---

## ✨ Özellikler

### 🗺️ İnteraktif Haber Haritası

- **Deck.gl + MapLibre GL** — GPU hızlandırmalı, yüksek performanslı harita katmanı
- **Kategori Renk Kodlaması** — Gündem, Trafik Kazası, Yangın, Elektrik Kesintisi, Hırsızlık, Kültürel Etkinlikler ve daha fazlası
- **İlçe & Tarih Filtresi** — Alt bar üzerinden ilçe ve zaman aralığı filtrelemesi
- **Kümeleme** — Yoğun bölgelerde akıllı marker kümeleme
- **Dark / Light Mode** — Tek tıkla tema değişimi

### 📡 Canlı Haber Akışı

- **SSE (Server-Sent Events)** — Yeni haberler anında sol panelde güncellenir
- **Canlı Kontrol Paneli** — Toplam / haritada / kaynak / son 6 saat metrik kartları
- **Scrape Tetikleme** — Arayüzden anında scrape başlatma ve canlı log izleme
- **Otomatik Sıfırlama** — Her tetiklemede veri temizlenerek taze veri çekilmesi seçeneği

### 🔍 Haber Detayı & Kaynak Referansı

- **Tam Metin Görüntüleyici** — Sağ panelde haber detayı, kategori, koordinat ve kaynak bilgisi
- **Çok Kaynaklı Birleştirme** — Aynı olay farklı kaynaklardan zenginleştirilir
- **"Haberin tamamını oku"** — Orijinal kaynağa yönlendirme

### 🤖 ML & NLP Pipeline

- **Named Entity Recognition (NER)** — `savasy/bert-base-turkish-ner-cased` (BERTTurk) veya `urchade/gliner_multi-v2.1` (GLiNER) ile yer ve kuruluş tanıma
- **Geocoding** — NER çıktısından koordinat çözümlemesi (Nominatim / mock provider)
- **Metin Embedding & Duplicate Detection** — Vektörel benzerlik ile tekrarlayan haberlerin tespiti
- **Kategorizer** — Keyword-based + opsiyonel semantic sınıflandırma

### ⚙️ Arka Plan Servisleri

- **Scheduler** — Her 3 saatte otomatik scrape (`Europe/Istanbul` timezone)
- **Worker** — Redis kuyruk tabanlı asenkron job işleyici
- **Ayrı ML Servisi** — Torch/Transformers bağımlılıkları lean API imajından izole edilmiş

---

## 📸 Ekran Görüntüleri

### Ana Harita — Açık Tema

![Ana harita görünümü — açık tema, kategori pinleri, ilçe filtresi](screenshots/PULSE%20Kocaeli%20News%20Map%20-%20PULSE%2022.05.2026%2017_24_49.png)

### Canlı Kontrol Paneli

| Metrik Kartları & Scrape Kontrolü | Dark Tema Harita |
| --------------------------------- | ---------------- |
| ![Canlı kontrol paneli — metrik kartlar ve scrape tetikleme](screenshots/PULSE%20Kocaeli%20News%20Map%20-%20PULSE%2022.05.2026%2017_26_17.png) | ![Dark mod harita görünümü](screenshots/PULSE%20Kocaeli%20News%20Map%20-%20PULSE%2022.05.2026%2017_26_47.png) |

### Haber Detay Paneli

| Yangın Haberi Detayı | Trafik Kazası — Çok Kaynaklı |
| -------------------- | ----------------------------- |
| ![Yangın haberi — kategori, koordinat ve tam metin](screenshots/PULSE%20Kocaeli%20News%20Map%20-%20PULSE%2022.05.2026%2017_27_47.png) | ![Trafik kazası — çok kaynaklı haber detayı](screenshots/PULSE%20Kocaeli%20News%20Map%20-%20PULSE%2022.05.2026%2017_28_51.png) |

---

## 🏗️ Mimari

```
KocaeliNewsMap/
├── backend/                  # FastAPI — Python 3.13
│   └── app/
│       ├── api/              # REST endpoint'leri
│       ├── scrapers/         # Kaynak bazlı scraper'lar (Bizim Yaka, Ses Kocaeli, …)
│       ├── services/
│       │   ├── ner/          # BERTTurk / GLiNER / mock provider
│       │   ├── geocoding/    # Nominatim / mock provider
│       │   ├── embedding/    # Metin vektörü & duplicate detection
│       │   ├── classifier/   # Kategori sınıflandırıcı
│       │   └── scrape_events.py  # SSE event stream
│       ├── workers/
│       │   ├── job_worker.py     # Redis queue consumer
│       │   └── run_scheduler.py  # APScheduler scrape zamanleyici
│       ├── ml_app.py         # Ayrı ML inference servisi (port 8010)
│       └── main.py           # Ana API (port 8000)
├── frontend/                 # Next.js 16 + React 19 + TypeScript
│   └── src/
│       ├── app/              # App Router sayfaları
│       └── components/       # Harita, panel, filter bileşenleri
├── mongo-init/               # MongoDB şema init scripti
├── deploy/                   # Nginx edge proxy konfigürasyonu
└── docker-compose.yml        # Tüm servisler tek compose dosyasında
```

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji |
| ------ | --------- |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| **Harita** | MapLibre GL 5, Deck.gl 9 (GPU rendering) |
| **Animasyon** | Framer Motion 12 |
| **Backend** | FastAPI, Python 3.13, Uvicorn |
| **Veritabanı** | MongoDB 8, Redis 7 |
| **ML/NLP** | HuggingFace Transformers, BERTTurk, GLiNER, PyTorch |
| **Geocoding** | Nominatim (OpenStreetMap) |
| **Job Queue** | Redis Streams |
| **Scraping** | Playwright (headless Chromium) |
| **Container** | Docker, Docker Compose |
| **Edge Proxy** | Nginx |
| **PWA** | Web Push, VAPID, Service Worker |

---

## 🚀 Kurulum

### Ön Gereksinimler

- **Docker Desktop** (BuildKit etkin)
- **Node.js 20+** (sadece local frontend geliştirme için)
- **Python 3.13+** (sadece local backend geliştirme için)

### 1. Klonlama & Ortam Değişkenleri

```bash
git clone https://github.com/ozdmromer24/KocaeliNewsMap.git
cd KocaeliNewsMap
cp .env.example .env
```

`.env` dosyasında minimum gerekli alanlar:

```env
MONGO_URL=mongodb://localhost:27017
MONGO_DOCKER_URL=mongodb://mongodb:27017
MONGO_DB=kocaeli_news
REDIS_URL=redis://localhost:6379/0
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Docker ile Başlatma (Önerilen)

```powershell
# Backend servislerini başlat (ML olmadan — hafif mod)
docker compose up -d mongodb redis mongo-migrate backend worker scheduler

# Frontend dahil tam yığın
docker compose up -d
```

Servisler ve portları:

| Servis | Port |
| ------ | ---- |
| API (backend) | `http://localhost:8000` |
| Frontend | `http://localhost:3001` |
| Edge (Nginx) | `http://localhost:3000` |
| MongoDB | `localhost:27017` |
| Redis | `localhost:6379` |
| ML Servisi | `http://localhost:8010` |

### 3. Sağlık Kontrolü

```powershell
# API sağlık kontrolü
curl http://localhost:8000/livez    # {"status": "ok"}
curl http://localhost:8000/readyz   # MongoDB + Redis durumu
```

---

## 🔧 Local Geliştirme

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev          # http://localhost:3000
```

### ML Servisi (Opsiyonel)

```powershell
# ML base imajını bir kez build et
powershell -ExecutionPolicy Bypass -File .\backend\scripts\build_ml_base.ps1

# ML servisini başlat
docker compose up -d ml
```

---

## 🧪 Test & QA

```powershell
# Frontend smoke test (canlı backend gerektirir)
cd frontend
npm run qa:map:smoke

# PWA offline testi
npm run qa:pwa:offline

# Lighthouse PWA skoru
npm run qa:pwa:lighthouse

# Backend birim testleri
cd ..
python -m pytest backend/tests/
```

---

## 📰 Haber Kaynakları

| Kaynak | Domain |
| ------ | ------ |
| Bizim Yaka Kocaeli | `bizimyaka.com` |
| Ses Kocaeli | `seskocaeli.com` |
| Yeni Kocaeli | `yenikocaeli.com` |
| Çağdaş Kocaeli | `cagdaskocaeli.com` |
| Özgür Kocaeli | `ozgurkocaeli.com` |

---

## 📄 Dokümantasyon

- **[`DEVELOPMENT.md`](DEVELOPMENT.md)** — Docker modları, ML base imajı, scrape kontrol düzlemi, bağımlılık profilleri

---

## 👥 Yazarlar

**Ömer Faruk Özdemir**

- 📧 [ozdmromer24@gmail.com](mailto:ozdmromer24@gmail.com)
- 💼 [LinkedIn](https://linkedin.com/in/ozdmromer24)

**Merve Budak**

- 📧 [mervebudak813@gmail.com](mailto:mervebudak230@gmail.com)
- 💼 [LinkedIn](https://www.linkedin.com/in/merve-budak-90b0a0298/)

---

## 📝 Lisans

Bu proje kişisel portföy amaçlı geliştirilmiştir.
