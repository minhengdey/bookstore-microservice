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

$dbs = @(
    'customer_db', 'catalog_db', 'book_db', 'staff_db', 'cart_db',
    'order_db', 'pay_db', 'ship_db', 'manager_db', 'comment_rate_db', 'recommender_db'
)

$i = 1
foreach ($db in $dbs) {
    $pattern = Join-Path $SqlDir ("{0:D2}_*_seed.sql" -f $i)
    $file = Get-ChildItem $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($file) {
        Write-Host "[$db] $($file.Name)"
        & $psql -U postgres -d $db -f $file.FullName
        if ($LASTEXITCODE -ne 0) { Write-Host "Loi khi chay $($file.Name)"; exit $LASTEXITCODE }
    }
    $i++
}

Write-Host "Xong. Da chay seed cho $($dbs.Count) database."
