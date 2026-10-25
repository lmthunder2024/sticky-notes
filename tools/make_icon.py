# -*- coding: utf-8 -*-
"""生成便签图标（多尺寸 ico），构建时由 CI 调用，也可本地手动跑。"""
import os

from PIL import Image, ImageDraw

S = 1024
M = 48          # 外边距
R = 150         # 圆角
FOLD = 210      # 折角大小

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 便签纸主体
d.rounded_rectangle([M, M, S - M, S - M], radius=R, fill=(252, 233, 168, 255))
# 折角
d.polygon([(S - M - FOLD, M), (S - M, M), (S - M, M + FOLD)], fill=(232, 207, 122, 255))
d.line([(S - M - FOLD, M), (S - M, M + FOLD)], fill=(214, 188, 104, 255), width=6)

# 三行“文字”
for ratio, width_ratio in ((0.365, 0.50), (0.505, 0.60), (0.645, 0.40)):
    y = int(S * ratio)
    x1 = int(S * 0.20)
    x2 = x1 + int(S * width_ratio)
    d.rounded_rectangle([x1, y, x2, y + 46], radius=23, fill=(186, 156, 74, 255))

# 左上角小圆点（图钉感）
d.ellipse([S * 0.20 - 26, S * 0.175, S * 0.20 + 26, S * 0.175 + 52], fill=(214, 152, 60, 255))

out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
os.makedirs(out_dir, exist_ok=True)
png = os.path.join(out_dir, "note.png")
ico = os.path.join(out_dir, "note.ico")

img.resize((256, 256), Image.LANCZOS).save(png)
img.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon ->", ico, os.path.getsize(ico), "bytes")
