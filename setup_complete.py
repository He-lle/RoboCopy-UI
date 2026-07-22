#!/usr/bin/env python3
"""GitHub 全套加速配置 - 状态查看 + 代理同步"""
import os, sys, subprocess, winreg

def get_system_proxy():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
        server = winreg.QueryValueEx(key, "ProxyServer")[0]
        return bool(enable), server
    except:
        return False, ""

def sync_git_proxy():
    enable, server = get_system_proxy()
    if enable and server:
        os.system(f'git config --global http.proxy http://{server}')
        os.system(f'git config --global https.proxy http://{server}')
        print(f"[OK] Git 代理已同步系统设置: {server}")
    else:
        os.system('git config --global --unset http.proxy 2>nul')
        os.system('git config --global --unset https.proxy 2>nul')
        print("[OK] 系统代理未开启, Git 代理已清除 (SSH 仍可用)")

def show():
    print("=" * 50)
    print("  GitHub 加速状态")
    print("=" * 50)
    ssh_key = os.path.expanduser("~/.ssh/github_he-lle")
    if os.path.exists(ssh_key):
        print("  SSH 密钥: 已配置 - git 可直连 (ssh.github.com:443)")
    else:
        print("  SSH 密钥: 未配置")
    try:
        r = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split("\n"):
            if "origin" in line:
                print(f"  远程地址: {line.split()[1]}")
                break
    except:
        pass
    enable, server = get_system_proxy()
    if enable:
        print(f"  系统代理: 开启 ({server})")
        print("  - 浏览器/下载/GitHub Desktop -> 走代理")
    else:
        print("  系统代理: 关闭")
        print("  - git push/pull -> 走 SSH (正常)")
        print("  - 浏览器访问 GitHub -> 需开启 VPN")
    print()
    print("  开启/关闭 VPN 或切换节点后, 运行:")
    print("    python setup_complete.py")

if __name__ == "__main__":
    sync_git_proxy()
    show()
