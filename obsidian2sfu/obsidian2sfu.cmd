@echo off
rem obsidian2sfu launcher for Windows.
rem Assumes layout:  <project>\obsidian2sfu\obsidian2sfu.py  and  <project>\.venv
setlocal
set "DIR=%~dp0"
for %%I in ("%DIR%..") do set "PROJECT=%%~fI"
"%PROJECT%\.venv\Scripts\python.exe" "%DIR%obsidian2sfu.py" %*
endlocal
