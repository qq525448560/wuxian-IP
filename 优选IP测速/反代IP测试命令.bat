@echo off
chcp 65001 >nul
title CloudflareST 测速工具 (带 Proxy 版)
echo ===========================================
echo     Cloudflare IP测速工具 启动中...
echo ===========================================

:: 检查文件是否存在
if not exist CloudflareST_proxy_win_amd64.exe (
    echo ? 错误: 未找到 CloudflareST_proxy_win_amd64.exe
    pause
    exit
)
if not exist ips_ports.txt (
    echo ? 错误: 未找到 ips_ports.txt
    pause
    exit
)

:: 执行测速命令
echo ?? 正在测速，请稍候...
CloudflareST_proxy_win_amd64.exe -f ips_ports.txt -dn 1000 -sl 1 -tl 5000 -url https://speed.cloudflare.com/__down?bytes=50000000 -p 20

echo.
echo ? 测速完成！请查看生成的 result.csv 文件。
echo 按任意键退出...
pause >nul
