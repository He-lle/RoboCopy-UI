@echo off
chcp 65001 >nul
title Git 代理助手

:: 从注册表读取 Windows 系统代理
for /f "tokens=3" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2^>nul') do set ENABLED=%%a
for /f "tokens=3" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2^>nul') do set SERVER=%%a

if "%ENABLED%"=="0x1" (
    echo 检测到系统代理：%SERVER%
    git config --global http.proxy http://%SERVER%
    git config --global https.proxy http://%SERVER%
    echo ✅ Git 全局代理已设置为 %SERVER%
) else (
    git config --global --unset http.proxy 2>nul
    git config --global --unset https.proxy 2>nul
    echo ℹ️ 系统代理未开启，已清除 Git 代理设置
)

echo.
echo 现在可以正常使用 git 命令了。
echo 之后每次 VPN 开关或换节点，重新运行本脚本即可。
pause
