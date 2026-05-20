#!/bin/bash
# ============================================================================
# Novel Sandbox Engine - Cross-platform Startup Script
# macOS / Linux 启动脚本
# ============================================================================

set -e  # Exit on error

# Get project root
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Novel Sandbox Engine - 启动器                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 not found! Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}[OK] Python: $PYTHON_VERSION${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js not found! Please install Node.js 16+${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}[OK] Node.js: $NODE_VERSION${NC}"

# Virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}[!] Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install Python dependencies
echo -e "${BLUE}[*] Checking Python dependencies...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}[OK] Python dependencies installed${NC}"

# Install frontend dependencies
if [ ! -d "web/node_modules" ]; then
    echo -e "${BLUE}[*] Installing frontend dependencies...${NC}"
    cd web
    npm install
    cd ..
    echo -e "${GREEN}[OK] Frontend dependencies installed${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Starting services...${NC}"
echo ""

# Start backend
export PYTHONPATH="$PROJECT_ROOT"
echo -e "${GREEN}[OK] Backend API Server: Port 8421${NC}"
echo -e "${GREEN}[OK] Frontend Web Server: Port 4242${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[服务状态]${NC}"
echo -e "   - 后端 API: ${GREEN}运行中 ${CYAN}(端口 8421)${NC}"
echo -e "   - 前端 Web:  ${GREEN}启动中    ${CYAN}(端口 4242)${NC}"
echo ""
echo -e "${YELLOW}[访问地址]${NC}"
echo -e "   - 前端界面: ${BLUE}http://localhost:4242${NC}"
echo -e "   - API 文档:   ${BLUE}http://localhost:8421/docs${NC}"
echo ""
echo -e "${YELLOW}[提示]${NC}"
echo -e "   - 前端启动可能需要 5-10 秒，请耐心等待"
echo -e "   - 按 Ctrl+C 停止所有服务"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}日志输出 (按 Ctrl+C 退出):${NC}"
echo ""

# Start both services in background
cd "$PROJECT_ROOT"
python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8421 &
BACKEND_PID=$!

cd web
npm run dev &
FRONTEND_PID=$!

# Wait for Ctrl+C
trap "echo -e '\n${YELLOW}Stopping services...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep script running
wait
