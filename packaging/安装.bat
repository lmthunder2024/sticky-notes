@echo off
chcp 65001 >nul
setlocal
title 轻便签 安装

set "SRC=%~dp0"
set "DST=%LOCALAPPDATA%\StickyNotes"

echo.
echo   轻便签 · 安装
echo   ----------------------------
echo   安装到：%DST%
echo.

if not exist "%DST%" mkdir "%DST%" >nul 2>&1

echo   [1/4] 复制程序文件...
xcopy "%SRC%轻便签.exe" "%DST%\" /Y /Q >nul
if exist "%SRC%使用说明.txt" xcopy "%SRC%使用说明.txt" "%DST%\" /Y /Q >nul
if exist "%SRC%_internal" xcopy "%SRC%_internal" "%DST%\_internal\" /E /I /Y /Q >nul

echo   [2/4] 创建桌面快捷方式...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $p = Join-Path ([Environment]::GetFolderPath('Desktop')) '轻便签.lnk'; $s = $ws.CreateShortcut($p); $s.TargetPath = '%DST%\轻便签.exe'; $s.WorkingDirectory = '%DST%'; $s.IconLocation = '%DST%\轻便签.exe,0'; $s.Description = '桌面悬浮便签'; $s.Save()"

echo   [3/4] 设置开机自动启动...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v StickyNotesLite /t REG_SZ /d "\"%DST%\轻便签.exe\"" /f >nul

echo   [4/4] 启动...
start "" "%DST%\轻便签.exe"

echo.
echo   装好了。桌面和任务栏上都能找到它。
echo   不想要了就跑同目录下的「卸载.bat」。
echo.
pause
