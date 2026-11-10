import requests, re, os, zipfile, io
from urllib.parse import urljoin

TOOLS = os.path.dirname(os.path.abspath(__file__))
lib = os.path.join(TOOLS, "pylibs")
os.makedirs(lib, exist_ok=True)
pkgs = ["pillow", "reportlab", "python-docx", "lxml", "typing-extensions"]
for p in pkgs:
    idx = f"https://mirrors.aliyun.com/pypi/simple/{p}/"
    html = requests.get(idx, timeout=20).text
    links = [l.split("#")[0] for l in re.findall(r'href="([^"]+)"', html)]
    cands = [l for l in links if ".whl" in l and (("cp312" in l and "win_amd64" in l) or "none-any" in l)]
    if not cands:
        print("NO WHEEL", p); continue
    if any("cp312" in l and "win_amd64" in l for l in cands):
        url = urljoin(idx, next(l for l in cands if "cp312" in l and "win_amd64" in l))
    else:
        url = urljoin(idx, cands[-1])
    r = requests.get(url, timeout=60)
    zipfile.ZipFile(io.BytesIO(r.content)).extractall(lib)
    print(p, r.status_code, len(r.content), url.split("/")[-1])
print("DONE", lib)
