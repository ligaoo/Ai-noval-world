#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Novel Simulator V5.2 - 一键启动脚本
启动后端 API 服务器和前端开发服务器
"""

import io
import os
import sys

# Windows 编码修复：强制使用 UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

import time
import signal
import shutil
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

def run_checked(cmd, *, cwd=None, env=None, error_message=None):
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        if error_message:
            print(f"    {Colors.FAIL}[FAIL] {error_message}{Colors.ENDC}")
        print(f"    {Colors.FAIL}命令执行失败: {' '.join(str(part) for part in cmd)}{Colors.ENDC}")
        if result.stdout:
            print(f"\n{Colors.WARNING}[stdout]{Colors.ENDC}\n{result.stdout.rstrip()}")
        if result.stderr:
            print(f"\n{Colors.WARNING}[stderr]{Colors.ENDC}\n{result.stderr.rstrip()}")
        sys.exit(result.returncode)
    return result

def get_npm_cmd():
    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        print(f"    {Colors.FAIL}[FAIL] npm 未找到，请先安装 Node.js 16+{Colors.ENDC}")
        sys.exit(1)
    return npm_cmd

def service_popen_kwargs():
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}

def ensure_process_started(process, name, delay=3):
    time.sleep(delay)
    returncode = process.poll()
    if returncode is not None:
        raise RuntimeError(f"{name} 启动失败，进程已退出，退出码: {returncode}")

def stop_process(process, name):
    if not process or process.poll() is not None:
        return

    print(f"{Colors.WARNING}正在停止{name}...{Colors.ENDC}")
    try:
        if sys.platform == "win32":
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except Exception:
        try:
            if sys.platform == "win32":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        except Exception as e:
            print(f"{Colors.FAIL}{name} 停止失败: {e}{Colors.ENDC}")

def check_dependencies():
    """检查依赖"""
    print(f"{Colors.OKCYAN}[1/4] 检查 Python 环境...{Colors.ENDC}")
    result = run_checked(
        [sys.executable, "--version"],
        error_message="Python 检查失败，请先安装 Python 3.10+",
    )
    python_version = (result.stdout or result.stderr).strip()
    print(f"    {Colors.OKGREEN}[OK] Python 已安装: {python_version}{Colors.ENDC}")

    print(f"{Colors.OKCYAN}[2/4] 检查 Node.js 环境...{Colors.ENDC}")
    node_cmd = shutil.which("node")
    if not node_cmd:
        print(f"    {Colors.FAIL}[FAIL] Node.js 未找到，请先安装 Node.js 16+{Colors.ENDC}")
        sys.exit(1)
    result = run_checked(
        [node_cmd, "--version"],
        error_message="Node.js 检查失败，请先安装 Node.js 16+",
    )
    print(f"    {Colors.OKGREEN}[OK] Node.js 已安装: {result.stdout.strip()}{Colors.ENDC}")

    npm_cmd = get_npm_cmd()

    print(f"{Colors.OKCYAN}[3/4] 检查/安装 Python 依赖...{Colors.ENDC}")
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if requirements_file.exists():
        run_checked(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=PROJECT_ROOT,
            error_message="Python 依赖安装失败",
        )
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
        run_checked(
            [npm_cmd, "install"],
            cwd=web_dir,
            error_message="前端依赖安装失败",
        )
        print(f"    {Colors.OKGREEN}[OK] 前端依赖安装完成{Colors.ENDC}")

def start_backend():
    """启动后端 API"""
    print(f"\n{Colors.OKCYAN}启动后端 API 服务器 (端口: 8421)...{Colors.ENDC}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8421"],
        env=env,
        cwd=PROJECT_ROOT,
        **service_popen_kwargs(),
    )

def start_frontend():
    """启动前端开发服务器"""
    print(f"{Colors.OKCYAN}启动前端开发服务器 (端口: 4242)...{Colors.ENDC}")

    web_dir = PROJECT_ROOT / "web"
    return subprocess.Popen(
        [get_npm_cmd(), "run", "dev"],
        cwd=web_dir,
        **service_popen_kwargs(),
    )

def main():
    print_header()
    check_dependencies()

    print(f"\n{Colors.HEADER}{Colors.BOLD}═══════════════════════════════════════════════════════════════{Colors.ENDC}")
    print(f"{Colors.OKCYAN}正在启动服务...{Colors.ENDC}\n")

    backend_process = None
    frontend_process = None

    def cleanup():
        stop_process(frontend_process, "前端服务")
        stop_process(backend_process, "后端服务")

    def signal_handler(sig, frame):
        print(f"\n\n{Colors.WARNING}正在停止服务...{Colors.ENDC}")
        cleanup()
        print(f"{Colors.OKGREEN}所有服务已停止{Colors.ENDC}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        backend_process = start_backend()
        ensure_process_started(backend_process, "后端服务")
        frontend_process = start_frontend()
        ensure_process_started(frontend_process, "前端服务")

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
        print(f"   {Colors.WARNING}- 前端启动可能需要一些时间，请耐心等待{Colors.ENDC}")
        print(f"   {Colors.WARNING}- 按 Ctrl+C 停止所有服务{Colors.ENDC}")

        print(f"\n{Colors.HEADER}═══════════════════════════════════════════════════════════════{Colors.ENDC}")
        print(f"\n{Colors.OKBLUE}服务已启动 (按 Ctrl+C 退出):{Colors.ENDC}")
        print(f"\n{Colors.WARNING}注意：后端和前端日志将在当前终端显示{Colors.ENDC}\n")

        # 保持进程运行，直到用户中断或服务异常退出
        while True:
            time.sleep(1)
            backend_returncode = backend_process.poll()
            if backend_returncode is not None:
                print(f"{Colors.FAIL}后端服务已停止，退出码: {backend_returncode}{Colors.ENDC}")
                cleanup()
                sys.exit(backend_returncode or 1)

            frontend_returncode = frontend_process.poll()
            if frontend_returncode is not None:
                print(f"{Colors.FAIL}前端服务已停止，退出码: {frontend_returncode}{Colors.ENDC}")
                cleanup()
                sys.exit(frontend_returncode or 1)

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"\n{Colors.FAIL}错误: {e}{Colors.ENDC}")
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
