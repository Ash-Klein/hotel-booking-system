"""下载 GraphViz 便携 zip 到 tools/graphviz（供 PlantUML 使用 dot 布局）。"""
import os, time, zipfile, requests

TOOLS = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(TOOLS, "downloads")
os.makedirs(DL, exist_ok=True)
URL = "https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/12.2.1/windows_10_cmake_Release_Graphviz-12.2.1-win64.zip"
zip_path = os.path.join(DL, "graphviz-12.2.1-win64.zip")
dest = os.path.join(TOOLS, "graphviz")

if not os.path.exists(zip_path):
    t0 = time.time()
    with requests.get(URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(zip_path + ".part", "wb") as f:
            for chunk in r.iter_content(1024 * 128):
                f.write(chunk)
    os.replace(zip_path + ".part", zip_path)
    print(f"downloaded {os.path.getsize(zip_path)/1024/1024:.1f} MB in {time.time()-t0:.1f}s")

with zipfile.ZipFile(zip_path) as z:
    names = z.namelist()
    root = names[0].split("/")[0]
    print("root:", root)
    z.extractall(DL)

src = os.path.join(DL, root)
if os.path.isdir(src) and not os.path.isdir(dest):
    os.replace(src, dest)
print("dest:", dest, "exists:", os.path.isdir(dest))
for dirpath, dirnames, filenames in os.walk(dest):
    if "dot.exe" in filenames:
        print("dot.exe:", os.path.join(dirpath, "dot.exe"))
