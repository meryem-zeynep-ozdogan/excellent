# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_dynamic_libs

# --- PLATFORM KONTROLÜ ---
IS_WINDOWS = sys.platform.startswith('win')
IS_MAC = sys.platform.startswith('darwin')
IS_LINUX = sys.platform.startswith('linux')

block_cipher = None

# --- DOSYA YOLLARI (Assets) ---
# Resimlerin ve fontların ANA DİZİNDE olduğunu varsayıyoruz.
# Eğer onları da PythonFiles içine taşıdıysanız burayı güncellemelisiniz.
datas = [
    ('fonts', 'fonts'), 
    ('app_icon.ico', '.'), 
    ('logo.png', '.')
]

# --- WINDOWS DLL AYARLARI ---
binaries = []

# --- ANALİZ ---
a = Analysis(
    # ANA DOSYANIZIN YOLU: PythonFiles klasörü içinde
    [os.path.join('PythonFiles', 'frontend-sidebar.py')],
    
    # ARAMA YOLU: PythonFiles klasörünü ekliyoruz ki diğer modülleri bulsun
    pathex=['PythonFiles'], 
    
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'rust_db', 'rust_qr', 
        'topdf', 'toexcel', 'fromqr', 'invoices', 'imports',
        'backend', 'backup', 'locales',
        'flet', 'xlsxwriter', 'reportlab', 'sqlite3',
        'json', 'datetime', 'os', 'sys', 'shutil', 'logging', 
        'threading', 'concurrent.futures', 'fitz', 'requests', 
        'xml.etree.ElementTree'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- EXE OLUŞTURMA ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Excellent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Excellent',
)

# --- MAC BUNDLE ---
if IS_MAC:
    app = BUNDLE(
        coll,
        name='Excellent.app',
        icon='app_icon.ico',
        bundle_identifier='com.excellent.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'CFBundleDisplayName': 'Excellent',
        },
    )