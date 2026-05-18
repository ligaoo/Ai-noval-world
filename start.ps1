# Novel Simulator V5.2 - 一键启动脚本
# 启动后端 API 服务器和前端开发服务器

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Novel Simulator V5.2 - 一键启动                          ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 环境
Write-Host "[1/4] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "    ✓ Python 已安装: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "    ✗ Python 未找到，请先安装 Python 3.10+" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 检查 Node.js 环境
Write-Host "[2/4] 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "    ✓ Node.js 已安装: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "    ✗ Node.js 未找到，请先安装 Node.js 16+" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 安装 Python 依赖
Write-Host "[3/4] 检查并安装 Python 依赖..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    Write-Host "    正在安装/检查 Python 包..." -ForegroundColor Gray
    pip install -r requirements.txt --quiet 2>&1 | Out-Null
    Write-Host "    ✓ Python 依赖已就绪" -ForegroundColor Green
} else {
    Write-Host "    ⚠ requirements.txt 未找到，跳过依赖安装" -ForegroundColor Yellow
}

# 安装前端依赖
Write-Host "[4/4] 检查并安装前端依赖..." -ForegroundColor Yellow
Set-Location "web"
if (Test-Path "node_modules") {
    Write-Host "    ✓ node_modules 已存在" -ForegroundColor Green
} else {
    Write-Host "    正在安装 npm 包..." -ForegroundColor Gray
    npm install --silent 2>&1 | Out-Null
    Write-Host "    ✓ 前端依赖安装完成" -ForegroundColor Green
}
Set-Location $ScriptDir

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "启动服务中..." -ForegroundColor Yellow
Write-Host ""

# 在新窗口启动后端 API
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:ScriptDir
    $env:PYTHONPATH = $using:ScriptDir
    python -m uvicorn api.server:app --host 0.0.0.0 --port 8421 --reload
} -Name "NovelSim-API"

# 等待后端启动
Start-Sleep -Seconds 3

# 在新窗口启动前端
$frontendJob = Start-Job -ScriptBlock {
    Set-Location "$using:ScriptDir\web"
    npm run dev
} -Name "NovelSim-Frontend"

Write-Host ""
Write-Host "✓ 后端 API 服务器启动中 (端口: 8421)" -ForegroundColor Green
Write-Host "  API 文档: http://localhost:8421/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "✓ 前端开发服务器启动中..." -ForegroundColor Green
Write-Host "  请等待 5-10 秒后访问前端地址" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 服务状态:" -ForegroundColor White
Write-Host "   - 后端 API: 运行中 (端口 8421)" -ForegroundColor Green
Write-Host "   - 前端 Web:  启动中..." -ForegroundColor Yellow
Write-Host ""
Write-Host "🔗 访问地址:" -ForegroundColor White
Write-Host "   - 前端界面: http://localhost:4242" -ForegroundColor Cyan
Write-Host "   - API 文档: http://localhost:8421/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 提示:" -ForegroundColor Yellow
Write-Host "   - 两个服务将在独立窗口运行" -ForegroundColor Gray
Write-Host "   - 按 Ctrl+C 或关闭窗口可停止服务" -ForegroundColor Gray
Write-Host "   - 前端启动可能需要几秒钟，请耐心等待" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 等待用户输入，保持脚本运行
Write-Host "按 Q 键停止所有服务并退出..." -ForegroundColor Yellow
Write-Host ""

do {
    $key = [Console]::ReadKey($true)
} while ($key.Key -ne 'Q')

# 停止服务
Write-Host ""
Write-Host "正在停止服务..." -ForegroundColor Yellow
Stop-Job -Name "NovelSim-API" -ErrorAction SilentlyContinue
Stop-Job -Name "NovelSim-Frontend" -ErrorAction SilentlyContinue
Remove-Job -Name "NovelSim-API" -Force -ErrorAction SilentlyContinue
Remove-Job -Name "NovelSim-Frontend" -Force -ErrorAction SilentlyContinue

Write-Host "所有服务已停止" -ForegroundColor Green
