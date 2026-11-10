@echo off
set "JAVA_HOME=%~dp0jdk21"
set "PLANTUML_LIMIT_SIZE=8192"
set "PATH=%~dp0graphviz\bin;%PATH%"
if not exist "%~dp0tmp" mkdir "%~dp0tmp"
if not exist "%~dp0tmp\prefs" mkdir "%~dp0tmp\prefs"
"%JAVA_HOME%\bin\java.exe" "-Djava.awt.headless=true" "-Djava.io.tmpdir=%~dp0tmp" "-Djava.util.prefs.userRoot=%~dp0tmp\prefs" -jar "%~dp0plantuml.jar" %*
