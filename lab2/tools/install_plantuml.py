"""在 lab2/tools 下安装本地 PlantUML 环境（免管理员、免系统 PATH）。

- OpenJDK 21：华为镜像 zip，解压到 tools/jdk21
- PlantUML：阿里云 Maven 镜像取最新 jar，放到 tools/plantuml.jar
- 生成 tools/plantuml.cmd 与 tools/plantuml.ps1 包装脚本
"""
import os, re, sys, time, zipfile, io
import requests

TOOLS = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(TOOLS, "downloads")
os.makedirs(DL, exist_ok=True)

JDK_URL = "https://mirrors.huaweicloud.com/openjdk/21.0.2/openjdk-21.0.2_windows-x64_bin.zip"
JDK_ZIP = os.path.join(DL, "openjdk-21.0.2_windows-x64_bin.zip")
JDK_DIR = os.path.join(TOOLS, "jdk21")


def download(url, dest, label):
    if os.path.exists(dest) and os.path.getsize(dest) > 1024 * 1024:
        print(f"[skip] {label} already exists: {os.path.getsize(dest)/1024/1024:.1f} MB")
        return dest
    print(f"[get ] {label}")
    t0 = time.time()
    with requests.get(url, stream=True, timeout=60, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1024 * 256):
                f.write(chunk)
                done += len(chunk)
                if total and done % (1024 * 1024 * 20) < 1024 * 256:
                    pct = done * 100 // total
                    print(f"       {pct}%  {done/1024/1024:.0f}/{total/1024/1024:.0f} MB", flush=True)
        os.replace(tmp, dest)
    print(f"[ok  ] {label}: {os.path.getsize(dest)/1024/1024:.1f} MB in {time.time()-t0:.1f}s")
    return dest


def install_jdk():
    java_exe = os.path.join(JDK_DIR, "bin", "java.exe")
    if os.path.exists(java_exe):
        print("[skip] JDK already installed")
        return java_exe
    download(JDK_URL, JDK_ZIP, "OpenJDK 21 (Huawei mirror)")
    print("[unzip] JDK ...")
    with zipfile.ZipFile(JDK_ZIP) as z:
        names = z.namelist()
        root = names[0].split("/")[0]
        z.extractall(DL)
    os.makedirs(JDK_DIR, exist_ok=True)
    src = os.path.join(DL, root)
    for item in os.listdir(src):
        os.replace(os.path.join(src, item), os.path.join(JDK_DIR, item))
    os.rmdir(src)
    if not os.path.exists(java_exe):
        raise SystemExit("JDK install failed: java.exe not found")
    return java_exe


def latest_plantuml():
    meta = requests.get(
        "https://maven.aliyun.com/repository/public/net/sourceforge/plantuml/plantuml/maven-metadata.xml",
        timeout=30,
    ).text
    m = re.search(r"<latest>([^<]+)</latest>", meta)
    version = m.group(1) if m else "1.2025.10"
    jar = os.path.join(TOOLS, "plantuml.jar")
    if os.path.exists(jar) and os.path.getsize(jar) > 5 * 1024 * 1024:
        print(f"[skip] plantuml.jar already exists ({version})")
        return jar, version
    url = f"https://maven.aliyun.com/repository/public/net/sourceforge/plantuml/plantuml/{version}/plantuml-{version}.jar"
    download(url, jar, f"PlantUML {version}")
    return jar, version


def write_wrappers(java_exe, jar):
    # 用 %~dp0 / $PSScriptRoot 取相对路径，避免把含中文的绝对路径写死进脚本。
    # 另外把 java.io.tmpdir 指到 tools/tmp：本机系统临时目录不可写，ImageIO 会报错。
    os.makedirs(os.path.join(TOOLS, "tmp"), exist_ok=True)
    cmd = '''@echo off
set "JAVA_HOME=%~dp0jdk21"
set "PATH=%~dp0graphviz\\bin;%PATH%"
if not exist "%~dp0tmp" mkdir "%~dp0tmp"
if not exist "%~dp0tmp\\prefs" mkdir "%~dp0tmp\\prefs"
"%JAVA_HOME%\\bin\\java.exe" "-Djava.awt.headless=true" "-Djava.io.tmpdir=%~dp0tmp" "-Djava.util.prefs.userRoot=%~dp0tmp\\prefs" -jar "%~dp0plantuml.jar" %*
'''
    with open(os.path.join(TOOLS, "plantuml.cmd"), "w", encoding="gbk") as f:
        f.write(cmd)
    ps1 = '''$env:JAVA_HOME = Join-Path $PSScriptRoot "jdk21"
$env:PATH = "$(Join-Path $PSScriptRoot "graphviz\\bin");$env:PATH"
$tmp = Join-Path $PSScriptRoot "tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$prefs = Join-Path $tmp "prefs"
New-Item -ItemType Directory -Force -Path $prefs | Out-Null
& (Join-Path $env:JAVA_HOME "bin\\java.exe") "-Djava.awt.headless=true" "-Djava.io.tmpdir=$tmp" "-Djava.util.prefs.userRoot=$prefs" -jar (Join-Path $PSScriptRoot "plantuml.jar") @args
'''
    with open(os.path.join(TOOLS, "plantuml.ps1"), "w", encoding="utf-8") as f:
        f.write(ps1)


if __name__ == "__main__":
    java_exe = install_jdk()
    jar, version = latest_plantuml()
    write_wrappers(java_exe, jar)
    print("[done] java :", java_exe)
    print("[done] jar  :", jar, version)
