# Chay cac file SQL seed vao tung database.
# Can: PostgreSQL da cai tren may, user postgres, cac DB da tao.
# Neu khong co psql trong PATH, script tu tim psql.exe trong thu muc cai PostgreSQL.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$SqlDir = Join-Path $ProjectRoot "scripts\sql"

# Tim psql.exe
$psql = $null
if (Get-Command psql -ErrorAction SilentlyContinue) {
    $psql = "psql"
} else {
    $commonPaths = @(
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files\PostgreSQL\14\bin\psql.exe",
        "C:\Program Files\PostgreSQL\13\bin\psql.exe"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) { $psql = $p; break }
    }
}

if (-not $psql) {
    Write-Host "Khong tim thay psql. Ban co the:"
    Write-Host "  1. Them thu muc PostgreSQL\bin vao PATH (vd: C:\Program Files\PostgreSQL\15\bin), roi chay lai script."
    Write-Host "  2. Dung DBeaver: mo tung file .sql trong scripts\sql, chon dung database, Execute Script."
    Write-Host "Thu muc script: $SqlDir"
    exit 1
}

$seeds = @(
    @{ Db = 'customer_db';     File = '01_customer_db_seed.sql' },
    @{ Db = 'catalog_db';      File = '02_catalog_db_seed.sql' },
    @{ Db = 'product_db';      File = '12_product_db_seed.sql' },
    @{ Db = 'book_db';         File = '03_book_db_seed.sql' },
    @{ Db = 'staff_db';        File = '04_staff_db_seed.sql' },
    @{ Db = 'cart_db';         File = '05_cart_db_seed.sql' },
    @{ Db = 'order_db';        File = '06_order_db_seed.sql' },
    @{ Db = 'pay_db';          File = '07_pay_db_seed.sql' },
    @{ Db = 'ship_db';         File = '08_ship_db_seed.sql' },
    @{ Db = 'manager_db';      File = '09_manager_db_seed.sql' },
    @{ Db = 'comment_rate_db'; File = '10_comment_rate_db_seed.sql' },
    @{ Db = 'recommender_db';  File = '11_recommender_db_seed.sql' }
)

foreach ($seed in $seeds) {
    $file = Join-Path $SqlDir $seed.File
    if (Test-Path $file) {
        Write-Host "[$($seed.Db)] $($seed.File)"
        & $psql -U postgres -d $seed.Db -f $file
        if ($LASTEXITCODE -ne 0) { Write-Host "Loi khi chay $($seed.File)"; exit $LASTEXITCODE }
    }
}

Write-Host "Xong. Da chay seed cho $($seeds.Count) database."
