#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Novel Simulator V5.2 - 一键启动脚本
启动后端 API 服务器和前端开发服务器
"""

import os
import sys

# Windows 编码修复：强制使用 UTF-8，避免替换 stdout/stderr 导致 logging 持有已关闭 stream
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

import time
import signal
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    print(f"\n{Colors.HEADER}{Colors.BOLD}╔═══════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}║         Novel Simulator V5.2 - 启动器                            ║{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}\n")

def check_dependencies():
    """检查依赖"""
    print(f"{Colors.OKCYAN}[1/4] 检查 Python 环境...{Colors.ENDC}")
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"    {Colors.OKGREEN}[OK] Python 已安装: {result.stdout.strip()}{Colors.ENDC}")
    except:
        print(f"    {Colors.FAIL}[FAIL] Python 未找到，请先安装 Python 3.10+{Colors.ENDC}")
        sys.exit(1)

    print(f"{Colors.OKCYAN}[2/4] 检查 Node.js 环境...{Colors.ENDC}")
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"    {Colors.OKGREEN}[OK] Node.js 已安装: {result.stdout.strip()}{Colors.ENDC}")
    except:
        print(f"    {Colors.FAIL}[FAIL] Node.js 未找到，请先安装 Node.js 16+{Colors.ENDC}")
        sys.exit(1)

    print(f"{Colors.OKCYAN}[3/4] 检查/安装 Python 依赖...{Colors.ENDC}")
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if requirements_file.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                      capture_output=True)
        print(f"    {Colors.OKGREEN}[OK] Python 依赖已就绪{Colors.ENDC}")
    else:
        print(f"    {Colors.WARNING}[!] requirements.txt 未找到，跳过依赖安装{Colors.ENDC}")

    print(f"{Colors.OKCYAN}[4/4] 检查/安装前端依赖...{Colors.ENDC}")
    web_dir = PROJECT_ROOT / "web"
    node_modules = web_dir / "node_modules"
    if node_modules.exists():
        print(f"    {Colors.OKGREEN}[OK] node_modules 已存在{Colors.ENDC}")
    else:
        print(f"    {Colors.WARNING}正在安装 npm 包...{Colors.ENDC}")
        subprocess.run(["npm", "install"], cwd=web_dir, capture_output=True)
        print(f"    {Colors.OKGREEN}[OK] 前端依赖安装完成{Colors.ENDC}")

def start_backend():
    """启动后端 API"""
    print(f"\n{Colors.OKCYAN}启动后端 API 服务器 (端口: 8421)...{Colors.ENDC}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.server:app",
         "--host", "0.0.0.0", "--port", "8421", "--reload"],
        env=env,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    return process

def start_frontend():
    """启动前端开发服务器"""
    print(f"{Colors.OKCYAN}启动前端开发服务器 (端口: 4242)...{Colors.ENDC}")

    web_dir = PROJECT_ROOT / "web"

    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    return process

def main():
    print_header()
    check_dependencies()

    print(f"\n{Colors.HEADER}{Colors.BOLD}═══════════════════════════════════════════════════════════════{Colors.ENDC}")
    print(f"{Colors.OKCYAN}正在启动服务...{Colors.ENDC}\n")

    backend_process = None
    frontend_process = None

    def signal_handler(sig, frame):
        print(f"\n\n{Colors.WARNING}正在停止服务...{Colors.ENDC}")
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except:
                backend_process.kill()
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except:
                frontend_process.kill()
        print(f"{Colors.OKGREEN}所有服务已停止{Colors.ENDC}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        backend_process = start_backend()
        time.sleep(3)
        frontend_process = start_frontend()

        print(f"\n{Colors.OKGREEN}[OK] 后端 API 服务器: 端口 8421{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[OK] 前端开发服务器: 端口 4242{Colors.ENDC}")

        print(f"\n{Colors.HEADER}═══════════════════════════════════════════════════════════════{Colors.ENDC}")
        print(f"\n{Colors.BOLD}[服务状态]{Colors.ENDC}")
        print(f"   {Colors.OKCYAN}- 后端 API: {Colors.OKGREEN}运行中 {Colors.OKCYAN}(端口 8421){Colors.ENDC}")
        print(f"   {Colors.OKCYAN}- 前端 Web:  {Colors.OKGREEN}启动中    {Colors.OKCYAN}(端口 4242){Colors.ENDC}")

        print(f"\n{Colors.BOLD}[访问地址]{Colors.ENDC}")
        print(f"   {Colors.OKCYAN}- 前端界面: {Colors.UNDERLINE}http://localhost:4242{Colors.ENDC}")
        print(f"   {Colors.OKCYAN}- API 文档:   {Colors.UNDERLINE}http://localhost:8421/docs{Colors.ENDC}")

        print(f"\n{Colors.WARNING}[提示]{Colors.ENDC}")
        print(f"   {Colors.WARNING}- 前端启动可能需要 5-10 秒，请耐心等待{Colors.ENDC}")
        print(f"   {Colors.WARNING}- 按 Ctrl+C 停止所有服务{Colors.ENDC}")

        print(f"\n{Colors.HEADER}═══════════════════════════════════════════════════════════════{Colors.ENDC}")
        print(f"\n{Colors.OKBLUE}日志输出 (按 Ctrl+C 退出):{Colors.ENDC}\n")

        import threading

        def read_backend_output():
            try:
                for line in iter(backend_process.stdout.readline, ''):
                    if line:
                        print(f"{Colors.OKCYAN}[API] {line.strip()}{Colors.ENDC}")
            except:
                pass

        def read_frontend_output():
            try:
                for line in iter(frontend_process.stdout.readline, ''):
                    if line:
                        print(f"{Colors.OKGREEN}[Web] {line.strip()}{Colors.ENDC}")
            except:
                pass

        backend_thread = threading.Thread(target=read_backend_output, daemon=True)
        frontend_thread = threading.Thread(target=read_frontend_output, daemon=True)

        backend_thread.start()
        frontend_thread.start()

        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print(f"{Colors.FAIL}后端服务已停止{Colors.ENDC}")
                break
            if frontend_process.poll() is not None:
                print(f"{Colors.FAIL}前端服务已停止{Colors.ENDC}")
                break

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"\n{Colors.FAIL}错误: {e}{Colors.ENDC}")
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
