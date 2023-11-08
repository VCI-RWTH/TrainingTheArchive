# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

data = []
data += [('resources/bpe_simple_vocab_16e6.txt.gz', './clip')]
data += [('resources', 'resources')]
data += [('models/ViT-B-32.pt', 'models')]
data += [('dataset/example', 'dataset/example')]
data += [('dataset/config.json', './dataset/')]
data += copy_metadata('tqdm')
data += copy_metadata('regex')
data += copy_metadata('requests')
data += copy_metadata('packaging')
data += copy_metadata('filelock')
data += copy_metadata('numpy')
data += copy_metadata('tokenizers')
data += copy_metadata('torch')
data += [('gui/style.qss', 'gui')]
data += [('gui/icons', 'gui/icons')]

a = Analysis(
    ['TheCuratorsMachine.py'],
    pathex=[],
    binaries=[],
    datas=data,
    hiddenimports=['clip'],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="The Curator's Machine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='resources/AppIcon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="The Curator's Machine",
)

app = BUNDLE(coll,
             name="The Curator's Machine.app",
             icon='./resources/AppIcon.icns',
             bundle_identifier=None)