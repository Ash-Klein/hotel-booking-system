"""裁掉 PlantUML 输出图四周的空白，避免嵌入报告时被整体缩小。"""
import sys
from PIL import Image, ImageChops

def trim(path, pad=24, threshold=12):
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L")
    # 与纯白差异超过阈值的像素视为内容
    mask = diff.point(lambda x: 255 if x > threshold else 0)
    bbox = mask.getbbox()
    if not bbox:
        return im.size
    l, t, r, b = bbox
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(im.width, r + pad); b = min(im.height, b + pad)
    im.crop((l, t, r, b)).save(path)
    return (r - l, b - t)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, trim(p))
