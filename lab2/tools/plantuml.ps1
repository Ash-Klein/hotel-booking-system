$env:JAVA_HOME = Join-Path $PSScriptRoot "jdk21"
$env:PATH = "$(Join-Path $PSScriptRoot "graphviz\bin");$env:PATH"
$tmp = Join-Path $PSScriptRoot "tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$prefs = Join-Path $tmp "prefs"
New-Item -ItemType Directory -Force -Path $prefs | Out-Null
& (Join-Path $env:JAVA_HOME "bin\java.exe") "-Djava.awt.headless=true" "-Djava.io.tmpdir=$tmp" "-Djava.util.prefs.userRoot=$prefs" -jar (Join-Path $PSScriptRoot "plantuml.jar") @args
