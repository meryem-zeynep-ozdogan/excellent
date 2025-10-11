# Ürün Gereksinimleri Belgesi (PRD)
## İnşaat Şirketi Finansal Yönetim Masaüstü Uygulaması

### Proje Özeti
İnşaat şirketleri için özel olarak tasarlanmış, Excel benzeri masaüstü uygulaması. Uygulama, şirketin finansal işlemlerini takip etmek, faturaları yönetmek ve detaylı finansal raporlar oluşturmak için geliştirilmiştir.

### Hedef Kitle
- İnşaat şirketlerinin muhasebe departmanları
- Mali müşavirler
- İnşaat proje yöneticileri
- Şirket sahipleri ve yöneticiler

### Ana Özellikler

#### 1. Fatura Yönetimi
- **Kesilen Faturalar**
  - Müşterilere kesilen faturaların aylık takibi
  - Fatura numarası, tarih, müşteri bilgileri
  - Tutar ve KDV hesaplaması
  - Fatura durumu (ödenmiş/beklemede/gecikmiş)

- **Gelen Faturalar**
  - Tedarikçi faturalarının takibi
  - Tedarikçi bilgileri ve kategori
  - Ödeme tarihi ve durumu
  - KDV hesaplaması

#### 2. Finansal Hesaplamalar
- **KDV Hesaplaması**
  - Aylık KDV toplamları
  - Ödenecek KDV hesaplaması
  - İade edilecek KDV hesaplaması

- **Kurumlar Vergisi**
  - Dönemsel kurumlar vergisi hesaplaması
  - Yıllık kurumlar vergisi takibi

#### 3. Raporlama ve Analiz
- **Aylık Raporlar**
  - Gelir-gider tablosu
  - KDV özeti
  - Fatura durumu raporu

- **Yıllık Raporlar**
  - Yıllık gelir-gider analizi
  - Kar-zarar hesaplaması
  - Vergi yükümlülükleri özeti

#### 4. Çoklu Para Birimi Desteği
- **Para Birimleri**
  - TL (Türk Lirası)
  - USD (Amerikan Doları)
  - EUR (Euro)

- **Döviz Kurları**
  - Güncel döviz kurları entegrasyonu
  - Otomatik kur güncellemesi
  - Manuel kur girişi seçeneği

#### 5. Fatura Kayıt Sistemi
- **Detaylı Fatura Bilgileri**
  - Fatura numarası ve seri
  - Tarih bilgileri
  - Müşteri/Tedarikçi detayları
  - Ürün/hizmet detayları
  - Tutar ve KDV bilgileri

- **Çoklu Para Birimi Kayıtları**
  - Her faturanın TL, USD, EUR karşılığı
  - Otomatik döviz çevirimi
  - Manuel tutar girişi seçeneği

### Teknik Gereksinimler

#### Platform
- **Masaüstü Uygulaması**
  - Windows 10/11 uyumlu
  - Modern, kullanıcı dostu arayüz
  - Excel benzeri tablo yapısı

#### Veri Yönetimi
- **Veritabanı**
  - SQLite veya SQL Server Express
  - Yerel veri saklama
  - Otomatik yedekleme

- **Veri İçe/Dışa Aktarma**
  - Excel (.xlsx) formatında dışa aktarma
  - CSV formatında veri aktarımı
  - PDF rapor oluşturma

#### Performans
- **Hız**
  - Hızlı veri girişi
  - Anlık hesaplama
  - Büyük veri setleriyle çalışabilme

### Kullanıcı Deneyimi

#### Arayüz Tasarımı
- **Modern UI**
  - Temiz ve anlaşılır tasarım
  - Excel benzeri menü yapısı
  - Kısayol tuşları desteği

- **Navigasyon**
  - Sol panel menü yapısı
  - Tab sistemi ile kolay geçiş
  - Breadcrumb navigasyon

#### Kullanılabilirlik
- **Kolay Kullanım**
  - Minimum eğitim gereksinimi
  - Yardım sistemi
  - Hata mesajları ve uyarılar

### Güvenlik
- **Veri Güvenliği**
  - Yerel veri şifreleme
  - Kullanıcı yetkilendirme
  - Oturum yönetimi

### Gelecek Geliştirmeler
- **Versiyon 2.0**
  - Mobil uygulama entegrasyonu
  - Bulut tabanlı veri senkronizasyonu
  - Gelişmiş raporlama araçları
  - Otomatik e-posta bildirimleri

## 🚀 MVP (Minimum Viable Product) - 4. Hafta Teslimi

### MVP Hedefi
4. haftanın sonunda çalışır durumda temel özelliklerle MVP sürümü teslim edilecek.

### MVP Temel Özellikleri

#### ✅ MVP'de Olacak Özellikler
1. **Temel Fatura Yönetimi**
   - Fatura girişi (kesilen/gelen)
   - Fatura listesi görüntüleme
   - Basit arama ve filtreleme
   - KDV hesaplaması

2. **Temel Para Birimi Desteği**
   - TL, USD, EUR para birimleri
   - Manuel döviz kuru girişi
   - Basit para birimi dönüşümü

3. **Temel Raporlama**
   - Aylık fatura özeti
   - Basit Excel export
   - Temel gelir-gider raporu

4. **Temel UI/UX**
   - PyQt6 masaüstü uygulaması
   - Ana menü ve navigasyon
   - Fatura giriş formu
   - Basit tablo görünümü

#### ❌ MVP'de Olmayacak Özellikler (V2.0 için)
1. **Gelişmiş Raporlama**
   - Detaylı grafikler
   - PDF rapor oluşturma
   - Yıllık analizler

2. **Gelişmiş Özellikler**
   - Otomatik döviz kuru güncelleme
   - Kurumlar vergisi hesaplaması
   - Gelişmiş filtreleme

3. **Güvenlik ve Yetkilendirme**
   - Kullanıcı girişi
   - Veri şifreleme
   - Yetki yönetimi

### MVP Başarı Kriterleri
- ✅ Fatura girişi ve listeleme çalışır durumda
- ✅ KDV hesaplaması doğru çalışır
- ✅ Temel para birimi dönüşümü çalışır
- ✅ Excel export çalışır
- ✅ Uygulama çökmeden çalışır
- ✅ Temel UI responsive ve kullanıcı dostu

### MVP Test Senaryoları
1. **Fatura Girişi Testi**
   - Yeni fatura ekleme
   - Fatura düzenleme
   - Fatura silme

2. **Hesaplama Testi**
   - KDV hesaplama doğruluğu
   - Para birimi dönüşümü
   - Toplam hesaplamalar

3. **Raporlama Testi**
   - Excel export işlevselliği
   - Aylık özet doğruluğu

4. **UI Testi**
   - Menü navigasyonu
   - Form validasyonu
   - Hata yönetimi

### MVP Sonrası Geliştirme Planı
- **5-6. Hafta:** Gelişmiş raporlama ve PDF export
- **7. Hafta:** Otomatik döviz kuru entegrasyonu
- **8. Hafta:** Final testler ve optimizasyonlar

### Ekip Yapısı ve Roller
- **Proje Yöneticisi / Test Koordinatörü:** Hibrit rol - proje yönetimi, test koordinasyonu ve kalite kontrol
- **Backend Developer:** Python uzmanı - API geliştirme, veritabanı ve optimizasyon
- **Frontend Developer:** UI/UX uzmanı - PyQt6 masaüstü uygulaması geliştirme ve entegrasyon

## Başarı Kriterleri (Final Versiyon)
- Kullanıcılar 1 hafta içinde uygulamayı öğrenebilmeli
- Fatura giriş süresi %50 azalmalı
- Finansal raporlar otomatik oluşturulmalı
- Veri kaybı olmamalı
- Uygulama 1000+ fatura ile sorunsuz çalışmalı
