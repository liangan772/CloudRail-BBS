# CloudRail Forum 后端开发启动脚本（PowerShell / Windows）
# 用法：.\run.ps1 [-Host 0.0.0.0] [-Port 8000]
# 说明：脚本将 .env 加载到进程环境后启动 uvicorn（UVICORN_* 才会生效）

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 首次运行提示
if (-not (Test-Path .env)) {
    Write-Host "[run.ps1] 未找到 .env，正在从 .env.example 复制..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "[run.ps1] 请编辑 .env 填写数据库/Redis/密钥配置后重新运行。" -ForegroundColor Yellow
    exit 1
}

# 选择 Python：优先 venv，缺失时给出指引而不是静默回退
if (Test-Path ".venv\Scripts\python.exe") {
    $Python = ".venv\Scripts\python.exe"
} else {
    Write-Host "[run.ps1] 未找到虚拟环境 .venv，请先执行：" -ForegroundColor Yellow
    Write-Host "    python -m venv .venv"
    Write-Host "    .\.venv\Scripts\python.exe -m pip install -e \".[dev]\""
    exit 1
}

Write-Host "[run.ps1] 加载 .env 并启动 uvicorn..." -ForegroundColor Cyan

# 加载 .env 到进程环境（跳过注释与空行；值中的 # 视为注释）
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        # 去除行内注释
        if ($value -match '^(.*?)\s+#.*$') { $value = $matches[1].Trim() }
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

& $Python -m uvicorn app.main:app @args
exit $LASTEXITCODE
