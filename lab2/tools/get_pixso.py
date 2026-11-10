import os, time, requests

TOOLS = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(TOOLS, "downloads")
URL = "https://pixso-pub-prod.obs.cn-east-3.myhuaweicloud.com/cms/download/package/app/bosyun/2.3.1/Pixso_win_v2_3_1.exe"
dest = os.path.join(DL, "Pixso_win_v2_3_1.exe")

r = requests.head(URL, timeout=30, allow_redirects=True)
print("HEAD", r.status_code, r.headers.get("content-length"), r.headers.get("content-type"), flush=True)

if not os.path.exists(dest) or os.path.getsize(dest) < 1024 * 1024:
    t0 = time.time()
    with requests.get(URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with open(dest + ".part", "wb") as f:
            for chunk in r.iter_content(1024 * 256):
                f.write(chunk); done += len(chunk)
                if total and done % (1024 * 1024 * 10) < 1024 * 256:
                    print(f"  {done*100//total}% {done/1024/1024:.0f}/{total/1024/1024:.0f} MB", flush=True)
    os.replace(dest + ".part", dest)
    print(f"downloaded {os.path.getsize(dest)/1024/1024:.1f} MB in {time.time()-t0:.1f}s", flush=True)

head = open(dest, "rb").read(2 * 1024 * 1024)
for marker in [b"Nullsoft", b"Squirrel", b"electron", b"Inno Setup", b"WiX"]:
    print(marker.decode(), marker in head, flush=True)
print("size", os.path.getsize(dest))
