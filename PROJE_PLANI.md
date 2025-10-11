# İnşaat Şirketi Finansal Yönetim Uygulaması - Proje Planı

## 🐍 Teknoloji Stack (Python Odaklı)

### Backend Geliştirme
- **FastAPI** - Modern, hızlı web framework
- **SQLAlchemy** - ORM ve veritabanı yönetimi
- **Pydantic** - Veri validasyonu
- **Celery** - Asenkron görevler (döviz kuru güncelleme)
- **Redis** - Cache ve mesaj kuyruğu

### Frontend (Masaüstü)
- **PyQt6/PySide6** - Modern masaüstü uygulaması
- **CustomTkinter** - Modern görünümlü Tkinter (alternatif)
- **Kivy** - Cross-platform UI (alternatif)

### Veritabanı
- **SQLite** - Geliştirme ve küçük kurulumlar için
- **PostgreSQL** - Production için (SQLAlchemy ile uyumlu)

### Raporlama ve Excel Entegrasyonu
- **openpyxl** - Excel dosya işleme
- **pandas** - Veri analizi ve manipülasyon
- **matplotlib/plotly** - Grafik oluşturma
- **reportlab** - PDF rapor oluşturma

### Döviz Kuru ve API
- **requests** - HTTP istekleri
- **aiohttp** - Asenkron HTTP
- **python-decouple** - Konfigürasyon yönetimi

### Test
- **pytest** - Unit ve integration testler
- **pytest-qt** - PyQt testleri
- **factory-boy** - Test verisi oluşturma

## 👥 Ekip Yapısı ve İş Bölümü

### Ekip Üyeleri (3 Kişi) - Python Uzmanları

#### 1. Proje Yöneticisi / Test Koordinatörü (Hibrit Rol)
**Sorumluluklar:**
**Proje Yönetimi:**
- Proje koordinasyonu ve takvim yönetimi
- Müşteri iletişimi
- Zaman yönetimi
- Risk yönetimi
- Proje dokümantasyonu

**Test ve Entegrasyon:**
- Test koordinasyonu ve planlama
- End-to-end testler
- Sistem entegrasyonu testleri
- Test dokümantasyonu
- Kalite kontrol
- MVP test kriterleri kontrolü

#### 2. Backend Developer (Python Uzmanı)
**Sorumluluklar:**
- FastAPI backend geliştirme
- Veritabanı tasarımı ve SQLAlchemy
- Döviz kuru API entegrasyonu
- Raporlama servisleri (PDF, Excel)
- Backend unit testler
- API dokümantasyonu
- Performance optimization
- Veri bütünlüğü kontrolleri

#### 3. Frontend Developer (Python + UI/UX)
**Sorumluluklar:**
- PyQt6 masaüstü uygulaması
- UI/UX tasarımı
- Excel benzeri tablo komponenti
- Kullanıcı deneyimi optimizasyonu
- Frontend testleri
- Kullanıcı kılavuzu
- UI dokümantasyonu
- API entegrasyonu

## 8 Haftalık Proje Takvimi

### HAFTA 1: Proje Hazırlığı ve Tasarım
**Hedef:** Proje altyapısının kurulması ve detaylı tasarım

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] Proje altyapısı kurulumu
- [ ] Teknik mimari dokümantasyonu
- [ ] Geliştirme standartları belirleme
- [ ] Proje dokümantasyonu
- [ ] Ekip koordinasyonu
- [ ] Test stratejisi belirleme
- [ ] Test altyapısı kurulumu

**Backend Developer:**
- [ ] Veritabanı şeması tasarımı (SQLAlchemy)
- [ ] FastAPI proje yapısı kurulumu
- [ ] Döviz kuru API araştırması
- [ ] Requirements.txt hazırlama
- [ ] Backend test altyapısı
- [ ] API endpoint tasarımı
- [ ] Veritabanı modelleri

**Frontend Developer:**
- [ ] UI/UX tasarım mockup'ları
- [ ] Kullanıcı akış diyagramları
- [ ] PyQt6 geliştirme ortamı kurulumu
- [ ] UI kütüphanesi seçimi
- [ ] Frontend test altyapısı
- [ ] UI komponenti tasarımı
- [ ] Ana pencere tasarımı

### HAFTA 2: Veritabanı ve Backend Altyapı
**Hedef:** Veri katmanı ve temel backend servislerinin geliştirilmesi

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] Proje ilerleme takibi
- [ ] Risk değerlendirmesi
- [ ] Müşteri iletişimi
- [ ] Test planı koordinasyonu
- [ ] Entegrasyon testleri
- [ ] Kalite kontrol
- [ ] MVP test kriterleri kontrolü

**Backend Developer:**
- [ ] SQLAlchemy modelleri oluşturma
- [ ] Veritabanı migration'ları
- [ ] Temel CRUD API'leri
- [ ] Döviz kuru servisi geliştirme
- [ ] Backend unit testler yazma
- [ ] API optimizasyonu

**Frontend Developer:**
- [ ] PyQt6 ana pencere tasarımı
- [ ] Menü yapısı geliştirme
- [ ] Temel UI komponentleri
- [ ] API entegrasyonu
- [ ] Frontend testleri
- [ ] UI optimizasyonu

### HAFTA 3: Fatura Yönetimi Modülü
**Hedef:** Fatura girişi ve düzenleme özelliklerinin geliştirilmesi

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] Fatura modülü ilerleme takibi
- [ ] Kullanıcı geri bildirimi toplama
- [ ] Test planı koordinasyonu
- [ ] Fatura modülü entegrasyon testleri
- [ ] MVP kriterleri kontrolü
- [ ] Kalite kontrol
- [ ] Test dokümantasyonu

**Backend Developer:**
- [ ] Fatura CRUD API'leri
- [ ] Pydantic validasyon modelleri
- [ ] Veri bütünlüğü kontrolleri
- [ ] KDV hesaplama servisi
- [ ] API optimizasyonu
- [ ] Backend API testleri

**Frontend Developer:**
- [ ] PyQt6 fatura giriş formu
- [ ] Fatura listesi görünümü
- [ ] Arama ve filtreleme UI
- [ ] Excel benzeri tablo komponenti
- [ ] Frontend validasyon testleri
- [ ] UI/UX iyileştirmeleri

### HAFTA 4: 🚀 MVP SÜRÜMÜ TESLİMİ
**Hedef:** Çalışır durumda MVP sürümü teslimi

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] MVP test koordinasyonu
- [ ] Müşteri demo hazırlığı
- [ ] MVP dokümantasyonu
- [ ] Teslim paketi hazırlama
- [ ] MVP sonrası planlama
- [ ] MVP end-to-end testleri
- [ ] Sistem entegrasyonu testleri
- [ ] MVP kriterleri final kontrolü
- [ ] Kalite kontrol

**Backend Developer:**
- [ ] Temel para birimi dönüşüm API'leri (manuel kur)
- [ ] KDV hesaplama servisi optimizasyonu
- [ ] Temel Excel export servisi
- [ ] MVP backend testleri
- [ ] API dokümantasyonu
- [ ] Performance optimization

**Frontend Developer:**
- [ ] PyQt6 para birimi seçici komponenti
- [ ] Basit döviz kuru girişi
- [ ] Temel Excel export UI
- [ ] MVP UI testleri
- [ ] Kullanıcı kılavuzu hazırlama
- [ ] UI/UX polish

**🎯 MVP TESLİM KRİTERLERİ:**
- ✅ Fatura girişi ve listeleme çalışır
- ✅ KDV hesaplaması doğru
- ✅ Temel para birimi dönüşümü
- ✅ Excel export çalışır
- ✅ Uygulama çökmeden çalışır
- ✅ Temel UI responsive

### HAFTA 5: Gelişmiş Raporlama ve PDF Export
**Hedef:** MVP sonrası gelişmiş raporlama özellikleri

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] MVP geri bildirimi değerlendirme
- [ ] Gelişmiş özellikler planlama
- [ ] Müşteri beklentileri analizi
- [ ] Raporlama entegrasyon testleri
- [ ] End-to-end testler
- [ ] Kalite kontrol
- [ ] Test dokümantasyonu

**Backend Developer:**
- [ ] ReportLab PDF oluşturma servisi
- [ ] Pandas gelişmiş veri analizi
- [ ] Kar-zarar hesaplama algoritması
- [ ] Yıllık rapor servisleri
- [ ] Gelişmiş Excel export
- [ ] PDF/Excel API testleri

**Frontend Developer:**
- [ ] PyQt6 gelişmiş rapor görünümleri
- [ ] PDF preview widget'ı
- [ ] Matplotlib grafik komponentleri
- [ ] Rapor filtreleri UI
- [ ] Gelişmiş export arayüzü

### HAFTA 6: Otomatik Döviz Kuru ve Gelişmiş Özellikler
**Hedef:** Otomatik döviz kuru entegrasyonu ve gelişmiş özellikler

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] Döviz kuru API araştırması
- [ ] Gelişmiş özellikler koordinasyonu
- [ ] Performans kriterleri belirleme
- [ ] Beta test planı
- [ ] Döviz kuru entegrasyon testleri
- [ ] End-to-end testler
- [ ] Kalite kontrol

**Backend Developer:**
- [ ] Otomatik döviz kuru güncelleme servisi (Celery)
- [ ] Redis cache mekanizması
- [ ] Kurumlar vergisi hesaplama servisi
- [ ] Performans optimizasyonu (NumPy/Pandas)
- [ ] Asenkron görev testleri

**Frontend Developer:**
- [ ] PyQt6 otomatik kur güncelleme UI
- [ ] Gelişmiş filtreleme komponentleri
- [ ] Kullanıcı deneyimi iyileştirmeleri
- [ ] Hata yönetimi arayüzü
- [ ] UI performance tuning

### HAFTA 7: Entegrasyon ve Sistem Testleri
**Hedef:** Tüm özelliklerin entegrasyonu ve kapsamlı testler

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] Entegrasyon test koordinasyonu
- [ ] Hata takip sistemi
- [ ] Kullanıcı kabul testleri
- [ ] Proje dokümantasyonu
- [ ] Sistem entegrasyon testleri
- [ ] PyQt6 entegrasyon testleri
- [ ] End-to-end testler
- [ ] Teknik dokümantasyon

**Backend Developer:**
- [ ] API hata düzeltmeleri
- [ ] Performans iyileştirmeleri
- [ ] Güvenlik kontrolleri
- [ ] Backend dokümantasyonu
- [ ] Backend optimization

**Frontend Developer:**
- [ ] Kullanılabilirlik testleri
- [ ] Frontend hata düzeltmeleri
- [ ] UI dokümantasyonu
- [ ] Cross-platform testleri
- [ ] Frontend optimization

### HAFTA 8: Final Optimizasyon ve Teslim
**Hedef:** Final optimizasyonlar, dokümantasyon ve teslim hazırlıkları

**Proje Yöneticisi / Test Koordinatörü:**
- [ ] Final test koordinasyonu
- [ ] Teslim paketi hazırlama
- [ ] Müşteri demo planı
- [ ] Proje kapanış raporu
- [ ] Ekip değerlendirmesi
- [ ] Gelecek projeler planlama
- [ ] Final end-to-end testler
- [ ] Teknik dokümantasyon
- [ ] Sistem deployment testleri
- [ ] Kalite kontrol

**Backend Developer:**
- [ ] Final performans optimizasyonları
- [ ] Python paket kurulumu
- [ ] API dokümantasyonu
- [ ] Deployment rehberi
- [ ] Kod temizliği ve refactoring
- [ ] Backend final optimization

**Frontend Developer:**
- [ ] Final UI optimizasyonları
- [ ] Kullanıcı kılavuzu
- [ ] Demo hazırlıkları
- [ ] UI dokümantasyonu
- [ ] Kurulum rehberi
- [ ] Son kullanıcı testleri

**🎯 FINAL TESLİM KRİTERLERİ:**
- ✅ Tüm MVP özellikleri çalışır
- ✅ Gelişmiş raporlama özellikleri
- ✅ Otomatik döviz kuru entegrasyonu
- ✅ PDF export çalışır
- ✅ Performans optimizasyonları
- ✅ Kapsamlı dokümantasyon

## Risk Yönetimi

### 🚨 MVP İçin Yüksek Risk Faktörleri
1. **4. Hafta MVP Teslim Riski**
   - Risk: MVP tesliminde gecikme
   - Çözüm: Günlük ilerleme takibi, erken test, buffer süreler
   - Kontrol: Her gün MVP kriterleri kontrolü

2. **Temel Özelliklerin Eksik Kalma Riski**
   - Risk: MVP'de temel özellikler eksik
   - Çözüm: Öncelik matrisi, haftalık milestone kontrolleri
   - Kontrol: Haftalık MVP kriterleri değerlendirmesi

3. **Backend-Frontend Entegrasyon Riski**
   - Risk: API entegrasyonu gecikmeleri
   - Çözüm: Erken prototip, mock API'ler
   - Kontrol: 2. hafta sonunda entegrasyon testi

### Orta Risk Faktörleri
1. **PyQt6 Öğrenme Eğrisi**
   - Risk: UI geliştirme gecikmeleri
   - Çözüm: Erken UI prototipi, hazır komponentler
   - Kontrol: 1. hafta sonunda UI mockup'ları

2. **Veritabanı Performansı**
   - Risk: SQLite performans sorunları
   - Çözüm: Erken performans testleri, optimizasyon
   - Kontrol: 3. hafta sonunda performans testi

### MVP Sonrası Risk Faktörleri
1. **Döviz Kuru API Bağımlılığı**
   - Risk: API erişim sorunları (5-6. hafta)
   - Çözüm: Alternatif API'ler ve fallback mekanizması

2. **Gelişmiş Özellikler Karmaşıklığı**
   - Risk: PDF export ve grafikler gecikmeleri
   - Çözüm: Hazır kütüphane kullanımı, basitleştirme

## İletişim ve Toplantılar

### MVP Odaklı Haftalık Toplantılar
- **Pazartesi:** Haftalık planlama + MVP milestone kontrolü
- **Çarşamba:** İlerleme kontrolü + MVP risk değerlendirmesi
- **Cuma:** Haftalık değerlendirme + MVP kriterleri kontrolü

### MVP İçin Günlük Scrum
- Her gün 15 dakikalık kısa toplantılar
- **MVP İlerleme Paylaşımı:**
  - MVP kriterlerinden hangileri tamamlandı?
  - Hangi MVP görevleri bugün yapılacak?
  - MVP teslimi için risk var mı?
- Blokaj tespiti ve çözümü
- MVP test sonuçları paylaşımı

### MVP Özel Toplantıları
- **2. Hafta:** MVP backend API prototipi demo
- **3. Hafta:** MVP frontend prototipi demo
- **4. Hafta:** MVP teslim öncesi final kontrol
- **4. Hafta Cuma:** 🚀 MVP TESLİMİ ve demo

### Ara Teslimler
- **2. Hafta:** Veritabanı şeması ve temel backend API'leri
- **4. Hafta:** 🚀 **MVP SÜRÜMÜ TESLİMİ** (Çalışır durumda temel özellikler)
- **6. Hafta:** Gelişmiş özellikler ve raporlama
- **8. Hafta:** Final teslim (Tam özellikli versiyon)

## 🛠️ Geliştirme Ortamı ve Proje Yapısı

### Geliştirme Ortamı Kurulumu
```bash
# Python 3.11+ kurulumu
python --version

# Virtual environment oluşturma
python -m venv insaat_finansal_env
insaat_finansal_env\Scripts\activate  # Windows
# source insaat_finansal_env/bin/activate  # Linux/Mac

# Gerekli paketlerin kurulumu
pip install -r requirements.txt
```

### Proje Yapısı
```
insaat_finansal/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI uygulaması
│   │   ├── config.py               # Konfigürasyon
│   │   ├── database.py             # Veritabanı bağlantısı
│   │   └── models/                 # SQLAlchemy modelleri
│   │       ├── __init__.py
│   │       ├── fatura.py
│   │       ├── para_birimi.py
│   │       └── rapor.py
│   ├── api/                        # API endpoint'leri
│   │   ├── __init__.py
│   │   ├── fatura.py
│   │   ├── para_birimi.py
│   │   └── rapor.py
│   ├── services/                   # İş mantığı servisleri
│   │   ├── __init__.py
│   │   ├── fatura_service.py
│   │   ├── doviz_service.py
│   │   └── rapor_service.py
│   ├── utils/                      # Yardımcı fonksiyonlar
│   │   ├── __init__.py
│   │   ├── hesaplamalar.py
│   │   └── validasyon.py
│   └── tests/                      # Backend testleri
│       ├── __init__.py
│       ├── test_api.py
│       └── test_services.py
├── frontend/
│   ├── main.py                     # PyQt6 ana uygulama
│   ├── ui/                         # UI sınıfları
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── fatura_form.py
│   │   ├── rapor_view.py
│   │   └── components/             # Yeniden kullanılabilir komponentler
│   │       ├── __init__.py
│   │       ├── excel_table.py
│   │       ├── para_birimi_selector.py
│   │       └── chart_widget.py
│   ├── controllers/                # UI kontrolcüleri
│   │   ├── __init__.py
│   │   ├── fatura_controller.py
│   │   └── rapor_controller.py
│   └── tests/                      # Frontend testleri
│       ├── __init__.py
│       └── test_ui.py
├── shared/                         # Ortak modüller
│   ├── __init__.py
│   ├── constants.py                # Sabitler
│   ├── exceptions.py               # Özel exception'lar
│   └── types.py                    # Tip tanımları
├── data/                           # Veritabanı dosyaları
│   ├── migrations/                 # Alembic migration'ları
│   └── insaat_finansal.db          # SQLite veritabanı
├── docs/                           # Dokümantasyon
│   ├── api.md
│   ├── user_guide.md
│   └── development.md
├── scripts/                        # Yardımcı scriptler
│   ├── setup_db.py
│   ├── seed_data.py
│   └── backup.py
├── requirements.txt                # Python bağımlılıkları
├── requirements-dev.txt            # Geliştirme bağımlılıkları
├── .env.example                    # Çevre değişkenleri örneği
├── .gitignore
├── README.md
└── pyproject.toml                  # Proje konfigürasyonu
```

### requirements.txt
```
# Backend
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0

# Frontend
PyQt6==6.6.1
PyQt6-Qt6==6.6.1
PyQt6-sip==13.6.0

# Veri İşleme
pandas==2.1.3
numpy==1.25.2
openpyxl==3.1.2

# Raporlama
matplotlib==3.8.2
plotly==5.17.0
reportlab==4.0.7

# API ve HTTP
requests==2.31.0
aiohttp==3.9.1
httpx==0.25.2

# Asenkron İşlemler
celery==5.3.4
redis==5.0.1

# Konfigürasyon
python-decouple==3.8
python-dotenv==1.0.0

# Test
pytest==7.4.3
pytest-qt==4.2.0
pytest-asyncio==0.21.1
factory-boy==3.3.0

# Veritabanı
psycopg2-binary==2.9.9  # PostgreSQL için
```

### requirements-dev.txt
```
# Geliştirme araçları
black==23.11.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.6.0

# Debugging
ipdb==0.13.13
pdb++==0.10.3

# Profiling
memory-profiler==0.61.0
line-profiler==4.1.1
```

### Konfigürasyon Dosyaları

#### .env.example
```env
# Veritabanı
DATABASE_URL=sqlite:///./data/insaat_finansal.db
# DATABASE_URL=postgresql://user:password@localhost/insaat_finansal

# API Ayarları
API_HOST=127.0.0.1
API_PORT=8000
API_DEBUG=True

# Döviz Kuru API
DOVIZ_API_URL=https://api.exchangerate-api.com/v4/latest
DOVIZ_API_KEY=your_api_key_here

# Redis (Celery için)
REDIS_URL=redis://localhost:6379/0

# Uygulama Ayarları
APP_NAME=İnşaat Finansal Yönetim
APP_VERSION=1.0.0
LOG_LEVEL=INFO
```

#### pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "insaat-finansal"
version = "1.0.0"
description = "İnşaat şirketi finansal yönetim masaüstü uygulaması"
authors = [{name = "Development Team", email = "dev@example.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.23",
    "PyQt6>=6.6.1",
    "pandas>=2.1.3",
    "openpyxl>=3.1.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-qt>=4.2.0",
    "black>=23.11.0",
    "flake8>=6.1.0",
    "mypy>=1.7.1",
]

[tool.black]
line-length = 88
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Geliştirme Komutları
```bash
# Backend başlatma
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend başlatma
python frontend/main.py

# Test çalıştırma
pytest backend/tests/
pytest frontend/tests/

# Veritabanı migration
alembic upgrade head

# Kod formatı
black .
flake8 .

# Paket kurulumu
pip install -e .
```
