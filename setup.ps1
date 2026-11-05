$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Không tạo được môi trường Python.' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Không cài được dependencies; kiểm tra quyền mạng và thông báo pip.' }
    Write-Output 'Sẵn sàng. Chạy: .\.venv\Scripts\python.exe scripts/run_phase1.py'
}
finally {
    Pop-Location
}
