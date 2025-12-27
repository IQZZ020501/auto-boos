# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 格式: ('源文件路径', '目标文件夹')
        ('core', 'core'),          # 将 core 文件夹打包
        ('common', 'common'),      # 将 common 文件夹打包
        ('media', 'media'),        # 将资源文件夹打包
        # 如果你想把 msedgedriver 打包进去，也加在这里
        ('utils/edge/msedgedriver.exe', 'utils/edge'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BoosAutoPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['media\\windown_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BoosAutoPro',
)
