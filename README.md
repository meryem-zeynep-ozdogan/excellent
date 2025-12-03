# Excellent - Detaylı Kullanım ve İşleyiş Kılavuzu

Bu kılavuz, Excellent Muhasebe ve Fatura Yönetim programının tüm özelliklerini, püf noktalarını ve çalışma mantığını en ince ayrıntısına kadar anlatmak için hazırlanmıştır.

---

## 1. 🏠 Ana Ekran (Dashboard) ve Genel Bakış

Programı açtığınızda sizi karşılayan **Genel Durum Paneli**, işletmenizin finansal sağlığını tek bakışta görmeniz için tasarlanmıştır.

### Burası Nasıl Çalışır?
* **Otomatik Döviz Kurları:** Sağ üst köşede göreceğiniz USD ve EUR kurları, program her açıldığında **TCMB (Merkez Bankası)** sunucularından otomatik olarak çekilir. İnternetiniz yoksa, en son hafızaya alınan kurları kullanır.
* **Para Birimi Değiştirici:** "₺ TRY", "$ USD", "€ EUR" butonlarına tıkladığınızda; tüm grafikler, toplam kâr ve gelir-gider rakamları anlık olarak o para birimine çevrilerek gösterilir.
* **Akıllı Grafikler:**
    * **Halkalar (Donut):** Net kâr, gelir, gider ve aylık ortalamayı gösterir.
    * **Yılan Grafik (Çizgi):** Yılın 12 ayı boyunca gelir ve gider dengenizi karşılaştırmalı olarak çizer. "Yıl" kutucuğundan geçmiş yılları seçerek eski performansınızı inceleyebilirsiniz.
* **Son İşlemler:** En altta, sisteme en son kimin hangi faturayı girdiğini veya sildiğini (tarih ve saat ile) görebilirsiniz. Güvenlik ve takip içindir.

---

## 2. 🧾 Fatura Yönetimi (En Önemli Bölüm)

Burası programın kalbidir. Fatura girişleri, düzenlemeleri ve akıllı tarama işlemleri buradan yapılır.

### A. Fatura Tipi Seçimi
Sol üstteki **"Giden Faturalar (Gelir)"** veya **"Gelen Faturalar (Gider)"** butonuna tıklayarak çalışma modunuzu değiştirin. Buton **Mor** ise gelir (satış), **Turuncu** ise gider (alış) modundasınız demektir.

### B. Manuel Fatura Ekleme
Elinizdeki faturayı sisteme elle girmek isterseniz:

1.  **Fatura No:** Faturanın üzerindeki numarayı girin.
2.  **Tarih:** Tarihi esnek girebilirsiniz. Örneğin `121223` yazıp geçerseniz, sistem bunu akıllıca `12.12.2023` yapar.
3.  **Firma & Malzeme:** İlgili bilgileri doldurun.
4.  **Tutar ve Para Birimi:** Tutar kısmına sadece rakam girin. Eğer fatura **Dövizli (USD/EUR)** ise, yanındaki kutudan para birimini seçin.
    * *Önemli:* Dövizli fatura girerseniz, sistem o günkü kur üzerinden **TL karşılığını** otomatik hesaplar ve raporlara TL olarak da işler.
5.  **KDV:** Varsayılan %20 gelir, isterseniz değiştirebilirsiniz.
6.  **Ekle** butonuna basın.

### C. Toplu Akıllı Tarama (QR ve PDF) ✨
Klasörünüzde birikmiş yüzlerce e-fatura PDF'i veya fotoğrafı mı var? Tek tek girmenize gerek yok.

1.  Sağ üstteki **Mavi QR/Klasör İkonuna** tıklayın.
2.  Bilgisayarınızdan faturaların olduğu klasörü seçin.
3.  Karşınıza çıkan soruda bu faturaların **GELİR** mi **GİDER** mi olduğunu seçin.
4.  **Sistem Çalışmaya Başlar:**
    * Önce dosyalarda **QR Kod** arar. Varsa saniyeler içinde tüm veriyi (Firma, Tarih, Tutar, KDV) çeker.
    * QR yoksa, gelişmiş **Yapay Zeka (OCR)** devreye girer; PDF'i okur, "Ödenecek Tutar", "Matrah", "Firma Adı" gibi alanları metin içinden bulup çıkarır.
    * **Mükerrer Kontrolü:** Aynı faturayı yanlışlıkla iki kez yüklediyseniz, sistem bunu fark eder ve ikincisini kaydetmez.
5.  İşlem bitince rapor verir. Başarısız veya bozuk dosyalar olursa, bunları ana klasördeki `BasarisizQRlar` isimli yeni bir klasöre taşır ki sonradan manuel kontrol edebilesiniz.

### D. Düzenleme ve Silme
* **Düzenleme:** Tablodaki bir faturanın kutucuğunu işaretleyin. Bilgiler yukarı dolacaktır. Değişikliği yapıp **Mavi (Güncelle)** butona basın.
* **Silme:** İster tek, ister 10 faturayı aynı anda seçip **Kırmızı (Sil)** butona basabilirsiniz.

---

## 3. 📉 Gider Takibi (Faturasız Giderler)

Her harcamanın faturası olmayabilir (Personel maaşı, ofis kirası, elden ödemeler vb.). Bunları takip etmek için:

1.  Fatura sayfasında **"Gelen Faturalar (Gider)"** moduna geçin.
2.  Sayfanın en altına inin. **"Yıllık Genel Giderler"** tablosunu göreceksiniz.
3.  İlgili yıl ve ayı seçin.
4.  Harcamayı yazın (Örn: `25000`). Para birimini seçebilirsiniz.
5.  **Yeşil Kaydet** butonuna basın.
    * *Not:* Bu giderler, fatura giderlerine eklenerek toplam giderinizi ve net kârınızı etkiler.

---

## 4. 📊 Raporlar ve Vergi Analizi

Muhasebecinize göndereceğiniz veya kendi durumunuzu göreceğiniz yerdir.

* **Dönemsel Tablo:** Yılın her ayı için;
    * Ne kadar fatura kestiğinizi (Gelir),
    * Ne kadar harcadığınızı (Fatura + Genel Gider),
    * **KDV Farkını:** (Devletten alacaklı mısınız, borçlu musunuz?)
    * **Tahmini Kurumlar Vergisini:** (Kârınız üzerinden hesaplanan) otomatik gösterir.
* **3 Aylık Özet:** Tablo aynı zamanda vergi dönemleri olan 3'er aylık periyotlarda (Geçici Vergi Dönemleri) ne kadar ödeme çıkacağını da özetler.
* **Dışa Aktarma:** Sağ üstteki butonlarla bu raporu **Excel** veya **PDF** olarak alıp yazdırabilirsiniz.

---

## 5. 💾 Yedekleme (Hayat Kurtarır)

Bilgisayarınıza bir şey olma ihtimaline karşı verilerinizi koruyun.
* Faturalar sayfasındaki **"Veritabanını Yedekle"** (Mor Buton) tuşuna basın.
* Sistem tüm kayıtlarınızı, ayarlarınızı ve geçmişinizi içeren bir `.zip` dosyası oluşturur.
* Bu dosyayı bir USB belleğe veya buluta (Google Drive vb.) yüklemeniz önerilir.

---

## 💡 İpuçları

* **Sıralama:** Fatura tablosunun üzerindeki "Sıralama" menüsünden "En Yeni", "Tarihe Göre" gibi seçeneklerle listeyi düzenleyebilirsiniz.
* **Arama:** Çok fazla faturanız varsa, Excel'e aktarıp orada detaylı filtreleme yapabilirsiniz.
* **Tarih Formatı:** Tarihleri `12122025`, `12.12.2025` veya `12/12/25` şeklinde girebilirsiniz; sistem hepsini anlar.


