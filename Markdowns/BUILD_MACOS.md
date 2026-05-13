# macOS Build Kılavuzu

Bu döküman, Excellent uygulamasını macOS için derleme adımlarını içerir.

## Gereksinimler

1. **macOS Sistemi** (macOS 10.13 veya üzeri)
2. **Python 3.12** kurulu olmalı
3. **Homebrew** (paket yöneticisi)
4. **Rust** (Rust modüllerini derlemek için)

## Kurulum Adımları

### 1. Gerekli Sistem Paketlerini Yükleyin

```bash
# Homebrew ile zbar kütüphanesini yükleyin (QR kod tarama için)
brew install zbar

# Rust kurulumu (eğer kurulu değilse)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 2. Python Sanal Ortamını Oluşturun

```bash
cd /path/to/excellent-rusty-patches

# Virtual environment oluştur
python3 -m venv .venv

# Aktif et
source .venv/bin/activate
```

### 3. Python Bağımlılıklarını Yükleyin

```bash
# requirements.txt'deki paketleri yükle
pip install -r requirements.txt

# PyInstaller'ı yükle
pip install pyinstaller
```

### 4. Rust Modüllerini Derleyin

```bash
# rust_db modülünü derle
cd rust_db
maturin develop --release
cd ..

# rust_qr modülünü derle
cd rust_qr
maturin develop --release
cd ..
```

### 5. Uygulamayı Derleyin

**Sidebar versiyonu için:**
```bash
pyinstaller Excellent-sidebar-macos.spec --clean --noconfirm
```

**Topbar versiyonu için:**
```bash
pyinstaller Excellent-topbar-macos.spec --clean --noconfirm
```

### 6. Çıktı

Derleme başarılı olursa, `dist/` klasöründe `Excellent.app` bulunacaktır:

```
dist/Excellent.app/
```

## .app Bundle'ı Çalıştırma

```bash
# Uygulamayı çalıştır
open dist/Excellent.app

# veya Terminal'den
./dist/Excellent.app/Contents/MacOS/Excellent
```

## İkon Ekleme (Opsiyonel)

macOS .app'leri için `.icns` formatında ikon gerekir:

1. **app_icon.png** dosyanızı `.icns`'e dönüştürün:

```bash
# PNG'den ICNS oluşturma
mkdir app_icon.iconset
sips -z 16 16     logo.png --out app_icon.iconset/icon_16x16.png
sips -z 32 32     logo.png --out app_icon.iconset/icon_16x16@2x.png
sips -z 32 32     logo.png --out app_icon.iconset/icon_32x32.png
sips -z 64 64     logo.png --out app_icon.iconset/icon_32x32@2x.png
sips -z 128 128   logo.png --out app_icon.iconset/icon_128x128.png
sips -z 256 256   logo.png --out app_icon.iconset/icon_128x128@2x.png
sips -z 256 256   logo.png --out app_icon.iconset/icon_256x256.png
sips -z 512 512   logo.png --out app_icon.iconset/icon_256x256@2x.png
sips -z 512 512   logo.png --out app_icon.iconset/icon_512x512.png
sips -z 1024 1024 logo.png --out app_icon.iconset/icon_512x512@2x.png

iconutil -c icns app_icon.iconset
rm -rf app_icon.iconset
```

2. Spec dosyasındaki `icon=None` satırını şununla değiştirin:
```python
icon='app_icon.icns',
```

## Code Signing (İsteğe Bağlı)

Uygulamayı imzalamak için Apple Developer hesabınız olmalı:

```bash
# Sertifikalarınızı listeleyin
security find-identity -v -p codesigning

# İmzalayın
codesign --deep --force --sign "Developer ID Application: Your Name" dist/Excellent.app

# Doğrulayın
codesign --verify --deep --strict dist/Excellent.app
```

## DMG Oluşturma (Dağıtım İçin)

```bash
# create-dmg aracını yükleyin
brew install create-dmg

# DMG oluşturun
create-dmg \
  --volname "Excellent Installer" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Excellent.app" 175 120 \
  --hide-extension "Excellent.app" \
  --app-drop-link 425 120 \
  "Excellent-Installer.dmg" \
  "dist/"
```

## Sorun Giderme

### pyzbar bulunamıyor hatası:
```bash
# zbar'ın kurulu olduğundan emin olun
brew reinstall zbar

# DYLD kütüphane yolunu ayarlayın
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
```

### Rust modülleri bulunamıyor:
```bash
# Modülleri tekrar derleyin
cd rust_db && maturin develop --release && cd ..
cd rust_qr && maturin develop --release && cd ..
```

### Uygulama açılmıyor ("damaged" hatası):
```bash
# Karantinayı kaldırın
xattr -cr dist/Excellent.app
```

### M1/M2 Mac (Apple Silicon) için:
```bash
# Universal binary için
pyinstaller Excellent-sidebar-macos.spec --target-arch universal2 --clean --noconfirm
```

## Platform Farklılıkları

macOS versiyonunda Windows versiyonundan farklı olan özellikler:

1. **argv_emulation=True**: macOS'ta dosyaları sürükle-bırak desteği için
2. **BUNDLE**: .app bundle oluşturur
3. **info_plist**: macOS metadata bilgileri
4. **.dylib** dosyaları (.dll yerine)
5. **.icns** ikon formatı (.ico yerine)

## Build Sistemi

Otomatik build için GitHub Actions veya benzeri CI/CD kullanabilirsiniz:

```yaml
# .github/workflows/build-macos.yml
name: Build macOS

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          brew install zbar
          pip install -r requirements.txt
          pip install pyinstaller maturin
      - name: Build Rust modules
        run: |
          cd rust_db && maturin develop --release && cd ..
          cd rust_qr && maturin develop --release && cd ..
      - name: Build app
        run: pyinstaller Excellent-sidebar-macos.spec --clean --noconfirm
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: Excellent-macOS
          path: dist/Excellent.app
```
