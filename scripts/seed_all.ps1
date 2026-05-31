# Chạy seed mock data cho tất cả microservices (theo thứ tự phụ thuộc).
# Yêu cầu: Docker Compose đang chạy (docker compose up -d).
# Cách chạy: .\scripts\seed_all.ps1
#            .\scripts\seed_all.ps1 -Clear   # xóa dữ liệu cũ rồi seed lại

param([switch]$Clear)
$ErrorActionPreference = "Stop"
$services = @(
    "auth-service",
    "user-service",
    "product-service",
    "cart-service",
    "order-service",
    "payment-service",
    "shipping-service",
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

    # After seeding, align serial sequences to prevent id collisions
    switch ($svc) {
        'auth-service' {
            Write-Host "[auth-service] Fixing sequence for auth_users..."
            docker run --rm -e PGPASSWORD=$env:PGPASSWORD postgres:15-alpine psql -h host.docker.internal -p 5433 -U postgres -d auth_db -c "SELECT setval(pg_get_serial_sequence('auth_users','id'), COALESCE((SELECT MAX(id) FROM auth_users),1));"
        }
        'user-service' {
            Write-Host "[user-service] Fixing sequence for users..."
            docker run --rm -e PGPASSWORD=$env:PGPASSWORD postgres:15-alpine psql -h host.docker.internal -p 55437 -U postgres -d user_db -c "SELECT setval(pg_get_serial_sequence('users','id'), COALESCE((SELECT MAX(id) FROM users),1));"
        }
        'product-service' {
            Write-Host "[product-service] Fixing sequence for products..."
            docker run --rm -e PGPASSWORD=$env:PGPASSWORD postgres:15-alpine psql -h host.docker.internal -p 55432 -U postgres -d product_db -c "SELECT setval(pg_get_serial_sequence('products','id'), COALESCE((SELECT MAX(id) FROM products),1));"
        }
        'order-service' {
            Write-Host "[order-service] Fixing sequence for orders..."
            docker run --rm -e PGPASSWORD=$env:PGPASSWORD postgres:15-alpine psql -h host.docker.internal -p 55434 -U postgres -d order_db -c "SELECT setval(pg_get_serial_sequence('orders','id'), COALESCE((SELECT MAX(id) FROM orders),1));"
        }
        'payment-service' {
            Write-Host "[payment-service] Fixing sequence for payments..."
            docker run --rm -e PGPASSWORD=$env:PGPASSWORD postgres:15-alpine psql -h host.docker.internal -p 55435 -U postgres -d pay_db -c "SELECT setval(pg_get_serial_sequence('payments','id'), COALESCE((SELECT MAX(id) FROM payments),1));"
        }
        'shipping-service' {
            Write-Host "[shipping-service] Fixing sequence for shippings..."
            docker run --rm -e PGPASSWORD=$env:PGPASSWORD postgres:15-alpine psql -h host.docker.internal -p 55436 -U postgres -d ship_db -c "SELECT setval(pg_get_serial_sequence('shippings','id'), COALESCE((SELECT MAX(id) FROM shippings),1));"
        }
        default { }
    }
}

Write-Host ""
Write-Host "=== Hoan thanh seed tat ca services ===" -ForegroundColor Cyan
