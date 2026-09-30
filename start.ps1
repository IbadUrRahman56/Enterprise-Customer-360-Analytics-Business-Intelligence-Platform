$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements.txt first. See README.md.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'data/warehouse.duckdb'))) {
    & $pythonPath -m customer360 demo
    if ($LASTEXITCODE -ne 0) { throw 'Demo build failed.' }
}
& $pythonPath -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501

