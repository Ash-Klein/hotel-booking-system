@echo off
chcp 65001 >nul
setlocal
set "PYTHONPATH=%~dp0pylibs"
for %%f in ("%~dp0..\UML\*.puml") do (
  echo [render] %%~nxf
  call "%~dp0plantuml.cmd" -charset UTF-8 -tpng "%%f"
  if exist "%~dp0pylibs\PIL" (
    python "%~dp0trim_png.py" "%%~dpnf.png"
  )
)
endlocal
