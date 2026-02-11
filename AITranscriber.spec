# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AITranscriber"""
import sys
import os

block_cipher = None

ROOT = os.path.dirname(os.path.abspath(SPEC))

# Collect non-.py data files from packages that need them
extra_datas = [
    (os.path.join(ROOT, 'static'), 'static'),
    (os.path.join(ROOT, 'app'), 'app'),
]

# funasr version.txt
try:
    import funasr as _funasr
    _funasr_dir = os.path.dirname(_funasr.__file__)
    _vt = os.path.join(_funasr_dir, 'version.txt')
    if os.path.isfile(_vt):
        extra_datas.append((_vt, 'funasr'))
except Exception:
    pass

a = Analysis(
    [os.path.join(ROOT, 'run.py')],
    pathex=[ROOT],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.responses',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.staticfiles',
        'starlette.responses',
        'multipart',
        'multipart.multipart',
        'pydub',
        'pydub.utils',
        'app',
        'app.main',
        'app.config',
        'app.audio_utils',
        'app.task_manager',
        'app.engines',
        'app.engines.base',
        'app.engines.whisper_engine',
        'app.engines.funasr_engine',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'notebook',
        'jupyter',
        'IPython',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AITranscriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AITranscriber',
)
