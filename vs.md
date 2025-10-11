# Ürün Gereksinimleri Dokümanı: ProjeMaliyet

**Sürüm:** 1.0
**Tarih:** 9 Ekim 2025

## 1. Giriş ve Problem Tanımı

Küçük ve orta ölçekli inşaat firmaları, proje bazlı finansal takibi genellikle karmaşık ve hataya açık Excel dosyaları ile yapmaktadır. Bu durum, anlık kâr-zarar takibini zorlaştırmakta, finansal verilerin dağınık olmasına neden olmakta ve stratejik karar almayı yavaşlatmaktadır. "ProjeMaliyet", bu sorunu çözmek için geliştirilmiş, kullanımı kolay bir masaüstü finans yönetim uygulamasıdır.

## 2. Ürün Hedefleri ve Başarı Kriterleri

* **Hedef 1: Merkezi Veri Yönetimi:** Tüm proje finansallarını tek bir yerde toplamak.
    * **Başarı Kriteri:** Kullanıcılar, tüm gelir ve giderlerini 2 dakikadan daha kısa sürede sisteme girebilmelidir.
* **Hedef 2: Anlık Finansal Görünürlük:** Anlık kâr-zarar analizi sunmak.
    * **Başarı Kriteri:** Ana panelde gösterilen net kâr rakamı, yapılan son işlemden sonra 1 saniye içinde güncellenmelidir.
* **Hedef 3: Kolay Raporlama:** Karar almayı destekleyecek basit raporlar sunmak.
    * [cite_start]**Başarı Kriteri:** Kullanıcı, 3 tıklamadan daha az bir işlemle istediği tarih aralığındaki finansal dökümü Excel'e aktarabilmelidir[cite: 125].

## 3. Hedef Kitle (User Personas)

* **Firma Sahibi Zeynep (45):** Teknolojiyle arası iyi değil. Şirketinin genel finansal durumunu hızlıca görmek ve hangi projenin ne kadar kârlı olduğunu anlamak istiyor.
* **Şantiye Şefi Ahmet (35):** Sahada sürekli masraf yapıyor. Yaptığı harcamaları (malzeme, yakıt vb.) anlık olarak ve kolayca sisteme girmek istiyor.
* **Ön Muhasebeci Elif (28):** Gelen faturaları ve yapılan ödemeleri sisteme işlemekle sorumlu. Ay sonunda yöneticisine sunmak için kolayca Excel raporu almak istiyor.

## 4. Özellikler ve Gereksinimler (Features & Requirements)

### 4.1. Gelir/Gider Yönetimi
* **Kullanıcı Hikayesi:** Bir kullanıcı olarak, projelerime ait gelir ve gider kayıtlarını tarih, kategori, tutar ve açıklama gibi detaylarla sisteme ekleyebilmeliyim ki finansal akışımı doğru bir şekilde takip edebileyim.
* **Gereksinimler:**
    * Gelir Ekleme Formu (Tarih, Proje Adı, Müşteri, Tutar, Açıklama)
    * Gider Ekleme Formu (Tarih, Proje Adı, Gider Kategorisi [Malzeme, Personel, Diğer], Tutar, Açıklama)
    * Tüm kayıtların listelendiği bir tablo.
    * Tablodan seçilen bir kaydı düzenleme ve silme fonksiyonu.

### 4.2. Ana Gösterge Paneli (Dashboard)
* **Kullanıcı Hikayesi:** Bir yönetici olarak, uygulamayı açtığımda toplam gelir, toplam gider ve net kâr gibi kilit finansal metrikleri anında görebilmeliyim ki şirketimin genel durumunu hızla değerlendirebileyim.
* **Gereksinimler:**
    * Toplam Gelir Kartı
    * Toplam Gider Kartı
    * Net Kâr/Zarar Kartı
    * Bu verilerin filtrelenebilmesi (Tüm Zamanlar, Bu Ay, Bu Yıl).

### 4.3. Raporlama
* **Kullanıcı Hikayesi:** Bir muhasebeci olarak, belirli bir tarih aralığındaki tüm finansal hareketlerin dökümünü tek bir tuşla Excel dosyası olarak alabilmeliyim ki resmi raporlamalar için kullanabileyim.
* **Gereksinimler:**
    * Başlangıç ve bitiş tarihi seçme aracı.
    * Seçilen aralıktaki verileri tablo formatında listeleyen bir "Rapor Oluştur" butonu.
    * Görüntülenen raporu `.xlsx` formatında dışa aktaran bir "Excel'e Aktar" butonu.

## 5. Kapsam Dışı (Out of Scope)

[cite_start]Bu projenin ilk versiyonunda aşağıdaki özellikler **yer almayacaktır**[cite: 170]:
* Çoklu kullanıcı desteği ve rol bazlı yetkilendirme.
* Bulut senkronizasyonu veya mobil uygulama.
* Otomatik fatura okuma (OCR).
* Detaylı vergi hesaplama (KDV beyannamesi hazırlama vb.).
* Stok veya envanter takibi.

## 6. Teknik Özellikler

* **Programlama Dili:** Python 3.9+
* **Arayüz Kütüphanesi:** CustomTkinter veya PyQt6
* **Veri Tabanı:** SQLite 3
* **Paketleme:** PyInstaller

## [cite_start]7. Varsayımlar (Assumptions) [cite: 136]

* [cite_start]Uygulama öncelikli olarak Windows 10 ve üzeri sistemler için geliştirilecektir[cite: 154].
* Kullanıcılar temel bilgisayar okuryazarlığına sahiptir.
* Veri tabanı, uygulamanın kurulu olduğu bilgisayarda yerel olarak saklanacaktır, ağ erişimi gerekmeyecektir.