@echo off
chcp 65001 >nul
setlocal
title 轻便签 卸载

set "DST=%LOCALAPPDATA%\StickyNotes"

echo.
echo   轻便签 · 卸载
echo   ----------------------------
echo.

echo   [1/3] 关闭正在运行的便签...
taskkill /IM 轻便签.exe /F >nul 2>&1

echo   [2/3] 删除开机自启和桌面快捷方式...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v StickyNotesLite /f >nul 2>&1
del "%USERPROFILE%\Desktop\轻便签.lnk" >nul 2>&1

echo   [3/3] 清理程序文件...
echo.
echo   你的便签内容存放在：%DST%\data
echo.
choice /C YN /N /M "   要连便签内容一起删掉吗？[Y=全删 / N=只删程序] "
if errorlevel 2 goto keepdata

rd /s /q "%DST%" >nul 2>&1
echo.
echo   已全部删除，干净了。
goto end

:keepdata
rd /s /q "%DST%\_internal" >nul 2>&1
del "%DST%\轻便签.exe" >nul 2>&1
del "%DST%\使用说明.txt" >nul 2>&1
echo.
echo   程序已删除，便签内容保留在 %DST%\data
echo   重新装回来还能接着用。

:end
echo.
pause
