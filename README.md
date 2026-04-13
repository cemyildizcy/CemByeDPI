# 🛡️ CemByeDPI — Discord Erişim Engeli Aşma Aracı

<p align="center">
  <strong>Türkiye'de Discord erişim engelini VPN'siz, hız kaybı olmadan aşın.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" />
  <img src="https://img.shields.io/badge/GUI-PyQt6-purple?style=flat-square" />
</p>

---

## 📋 Nedir?

**CemByeDPI**, Türkiye'deki ISP'lerin uyguladığı DPI (Derin Paket İnceleme) tabanlı Discord erişim engelini aşmak için geliştirilmiş, tamamen özgün ve açık kaynaklı bir araçtır.

> ⚠️ Bu bir VPN **değildir**! İnternet hızınızı etkilemez, yalnızca Discord'a erişim engelini kaldırır.

## 🚀 Nasıl Çalışır?

CemByeDPI üç katmanlı bir strateji kullanır:

### 1. 🔐 DNS-over-HTTPS (DoH)
Türk ISP'leri port 53 üzerindeki DNS sorgularını engelliyor. CemByeDPI, DNS çözümlemesini **HTTPS üzerinden** (port 443) yaparak bu engeli tamamen atlatır. Çözümlenen IP adresleri doğrudan Windows `hosts` dosyasına yazılır.

### 2. ✂️ SNI Fragmentation
TLS handshake sırasında gönderilen `ClientHello` paketindeki **SNI (Server Name Indication)** alanını DPI sistemi okuyarak engelleme uygular. CemByeDPI bu paketi **ilk 2 byte'tan bölerek** DPI'ın TLS yapısını parse etmesini engeller.

### 3. 👻 Sahte RST Paketi
Parçalar arasında **TTL=1** ile sahte bir RST paketi gönderilir. Bu paket ISP'nin DPI sistemine ulaşır (bağlantıyı "kapanmış" sanır) ama sunucuya ulaşamaz (ilk router'da düşürülür).

```
Tarayıcı → [2 byte TLS] → [Sahte RST, TTL=1] → [50ms gecikme] → [Kalan veri + SNI]
                                    ↓
                          DPI: "Bağlantı kapanmış, izlemeyi bırak"
                                    ↓
                          Sunucu: RST'yi hiç görmedi, normal devam
```

## ⚡ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🛡️ **SNI Fragmentation** | TLS paketlerini erken bölme + sahte paket stratejisi |
| 🔐 **DNS-over-HTTPS** | ISP DNS engellemesini tamamen atlatan şifreli DNS |
| 📁 **Hosts Yönetimi** | Discord domain IP'lerini otomatik hosts dosyasına yazar |
| ⚡ **Hız Testi** | Yerleşik internet hız ve ping ölçümü |
| 🔽 **Sistem Tepsisi** | Pencereyi kapatsanız bile arka planda çalışır |
| 🚀 **Otostart** | Windows açılışında otomatik başlatma seçeneği |
| 📊 **Canlı İstatistikler** | İşlenen/parçalanan paket sayısı, çalışma süresi |
| 📝 **Log** | Gerçek zamanlı olay günlüğü |
| 🎨 **Modern GUI** | Discord temalı koyu arayüz (PyQt6) |

## 📦 Kurulum

### Hazır .exe (Önerilen)
1. [Releases](../../releases) sayfasından `CemByeDPI.exe` dosyasını indirin
2. Çift tıklayın → UAC izni verin → Kullanmaya başlayın!

### Kaynak Koddan Çalıştırma
```bash
# Depoyu klonlayın
git clone https://github.com/cemyildizcy/CemByeDPI.git
cd CemByeDPI

# Bağımlılıkları kurun
pip install -r requirements.txt

# Yönetici olarak çalıştırın
python main.py
```

### Kendiniz Derlemek İsterseniz
```bash
build.bat
# Çıktı: dist\CemByeDPI.exe
```

## 🎮 Kullanım

1. **CemByeDPI.exe'yi çalıştırın** — otomatik olarak yönetici izni ister
2. **⏻ butonuna basın** — Sarı "Bağlanıyor..." → Yeşil "Bağlı"
3. **Discord'u açın** — Erişim engeli kalkmış olacak
4. **Pencereyi kapatın** — Arka planda çalışmaya devam eder
5. **Tekrar açmak için** — Görev çubuğunda `^` → CemByeDPI ikonuna çift tıklayın
6. **Tamamen kapatmak için** — Tray ikonu → Sağ tık → Çıkış

## 🏗️ Proje Yapısı

```
CemByeDPI/
├── main.py                  # Ana giriş noktası
├── requirements.txt         # Python bağımlılıkları
├── build.bat                # .exe derleme scripti
├── icon.ico                 # Uygulama ikonu
├── admin.manifest           # Windows UAC manifest
├── core/
│   ├── engine.py            # Orkestrasyon motoru
│   ├── sni_fragmenter.py    # SNI fragmentation bypass motoru
│   ├── dns_manager.py       # DoH + hosts + sistem DNS yönetimi
│   ├── domains.py           # Discord domain listesi
│   └── speed_test.py        # İnternet hız testi
├── gui/
│   ├── main_window.py       # PyQt6 ana pencere + sistem tepsisi
│   └── styles.py            # Discord temalı koyu tema QSS
└── utils/
    ├── admin_check.py       # Windows UAC yükseltme
    ├── logger.py            # Loglama altyapısı
    └── network.py           # Ağ yardımcıları
```

## 🔒 Güvenlik & Gizlilik

- ✅ **Tamamen açık kaynak** — Tüm kodu inceleyebilirsiniz
- ✅ **Veri toplamaz** — Hiçbir kişisel veri toplanmaz veya gönderilmez
- ✅ **VPN değil** — Trafiğinizi şifrelemez veya yönlendirmez
- ✅ **WinDivert** — Microsoft imzalı, açık kaynak paket işleme sürücüsü

---

## 🛡️ Anti-Virüs ve Windows Uyarıları Hakkında (ÖNEMLİ)

CemByeDPI tamamen ücretsiz, bağış kabul etmeyen ve açık kaynaklı bağımsız bir projedir. Kodlarında hiçbir zararlı yazılım barındırmamasına rağmen, aşağıdaki uyarılarla karşılaşabilirsiniz. Lütfen okuyun:

1. **Windows SmartScreen (Bilinmeyen Yayıncı) Uyarısı:**
   - **Neden Çıkar?** Ticari yazılım şirketlerinin Microsoft'a her yıl ödediği binlerce dolarlık "Genişletilmiş Dijital Sertifika (EV Code Signing)" bu projede (ücretsiz olduğu için) bulunmamaktadır. Windows, sertifikası olmayan her yeni programı engeller.
   - **Çözüm:** Mavi uyarı ekranı geldiğinde **"Daha fazla bilgi"** yazısına tıklayıp **"Yine de çalıştır"** butonuna basarak güvenle kullanabilirsiniz.

2. **Açık Kaynak & Şeffaflık**
   - Uygulamanın tüm mekanik ve bağlantı kodları GitHub üzerinde açıktır. İnternet trafiğinizi asla uzak bir sunucuya yönlendirmez. Kendi bilgisayarınızda ağ paketlerini yerel olarak düzenler. İnanmayan veya şüphe duyan herkes doğrudan Python kurup kaynak koddan çalıştırabilir.

3. **VirusTotal Raporu**
   - Dünyanın en büyük 70 farklı virüs programı tarafından taranmış ve onaylanmıştır. Program ağ ayarlarını değiştirdiği için (PyInstaller ve WinDivert kaynaklı) sadece 1-2 dandik antivirüs "False Positive" uyarı verebilir.
   - **[Buraya tıklayarak güncel VirusTotal test sonucunu görebilirsiniz.](https://www.virustotal.com/)** *(Uygulamayı indirdikten sonra siz de kendi dosyanızı tarayabilirsiniz)*

## 🔧 Gereksinimler

- Windows 10 / 11 (64-bit)
- Yönetici (Administrator) hakları
- İnternet bağlantısı

## ⚠️ Yasal Uyarı

Bu yazılım yalnızca **eğitim ve araştırma** amacıyla geliştirilmiştir. Kullanımından doğan her türlü yasal sorumluluk kullanıcıya aittir. Geliştiriciler, yazılımın yasa dışı amaçlarla kullanılmasından sorumlu tutulamaz.

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

---

<p align="center">
  <sub>Made with ❤️ by Cem YILDIZ</sub>
</p>
