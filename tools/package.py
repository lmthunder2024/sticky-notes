# -*- coding: utf-8 -*-
"""把 PyInstaller 产物 + 安装脚本打成一个 zip。
构建全程用英文路径（避免 Windows runner 中文编码问题），
只有 zip 内部的最终文件名是中文，并显式写入 UTF-8 标记。"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "StickyNotes")
PACKAGING = os.path.join(ROOT, "packaging")
OUT_DIR = os.path.join(ROOT, "release")

BUILD_NAME = "StickyNotes"
APP_NAME = "轻便签"

version = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
zip_path = os.path.join(OUT_DIR, "%s-%s-win64.zip" % (BUILD_NAME, version))

os.makedirs(OUT_DIR, exist_ok=True)
if os.path.exists(zip_path):
    os.remove(zip_path)

total = 0
count = 0
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, _dirs, files in os.walk(DIST):
        for name in files:
            src = os.path.join(root, name)
            rel = os.path.relpath(src, DIST)
            # 只把主程序改成中文名，其余（_internal 里的 dll/pyd）保持原样
            if rel == BUILD_NAME + ".exe":
                rel = APP_NAME + ".exe"
            z.write(src, APP_NAME + "/" + rel.replace("\\", "/"))
            total += os.path.getsize(src)
            count += 1
    for name in sorted(os.listdir(PACKAGING)):
        src = os.path.join(PACKAGING, name)
        if os.path.isfile(src):
            z.write(src, APP_NAME + "/" + name)
            total += os.path.getsize(src)
            count += 1

print("zip: %s" % zip_path)
print("%d files, raw %.1f MB -> zip %.1f MB"
      % (count, total / 1048576.0, os.path.getsize(zip_path) / 1048576.0))
