# Chạy seed mock data cho tất cả microservices (theo thứ tự phụ thuộc).
# Yêu cầu: Docker Compose đang chạy (docker compose up -d).
# Cách chạy: .\scripts\seed_all.ps1
#            .\scripts\seed_all.ps1 -Clear   # xóa dữ liệu cũ rồi seed lại

param([switch]$Clear)
$ErrorActionPreference = "Stop"
$services = @(
    "customer-service",
    "catalog-service",
    "book-service",
    "staff-service",
    "cart-service",
    "order-service",
    "pay-service",
    "ship-service",
    "manager-service",
    "comment-rate-service",
    "recommender-ai-service"
)

$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "docker-compose.yml"))) {
    $root = (Get-Location).Path
}

Set-Location $root
Write-Host "=== Seed mock data (thu muc: $root) ===" -ForegroundColor Cyan

foreach ($svc in $services) {
    Write-Host ""
    Write-Host "[$svc] Running seed_mock..." -ForegroundColor Yellow
    $cmd = @("compose", "exec", "-T", $svc, "python", "manage.py", "seed_mock")
    if ($Clear) { $cmd += "--clear" }
    docker @cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Loi tai $svc" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "[$svc] OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Hoan thanh seed tat ca services ===" -ForegroundColor Cyan
