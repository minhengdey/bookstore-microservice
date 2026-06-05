$ErrorActionPreference = "Stop"

$seeds = @(
    @{ Db = 'auth_db';    Port = '5433';  File = '01_auth_db_seed.sql' },
    @{ Db = 'catalog_db'; Port = '55439'; File = '02_catalog_db_seed.sql' },
    @{ Db = 'user_db';    Port = '55437'; File = '13_user_db_seed.sql' },
    @{ Db = 'cart_db';    Port = '55433'; File = '05_cart_db_seed.sql' },
    @{ Db = 'order_db';   Port = '55441'; File = '06_order_db_seed.sql' },
    @{ Db = 'payment_db'; Port = '55442'; File = '07_pay_db_seed.sql' },
    @{ Db = 'ship_db';    Port = '55436'; File = '08_ship_db_seed.sql' },
    @{ Db = 'product_db'; Port = '55432'; File = '12_product_db_seed.sql' },
    @{ Db = 'recommender_db'; Port = '55438'; File = '11_recommender_db_seed.sql' }
)

foreach ($seed in $seeds) {
    $file = "scripts\sql\" + $seed.File
    Write-Host "Seeding $($seed.Db) with $($file) on port $($seed.Port)..."
    
    # We pipe the local file to the docker container executing psql
    $containerName = "e-commerce-postgres-temp"
    
    # Actually, we have the containers running, let's execute inside the respective container
    # Mappings from db to container name:
    # catalog_db -> e-commerce-catalog-db-1
    # user_db -> e-commerce-user-db-1
    # cart_db -> e-commerce-cart-db-1
    # order_db -> e-commerce-order-db-1
    # payment_db -> e-commerce-payment-db-1
    # ship_db -> e-commerce-shipping-db-1
    # product_db -> e-commerce-product-db-1
    # recommender_db -> e-commerce-recommender-db-1

    $cName = ""
    switch ($seed.Db) {
        "auth_db" { $cName = "e-commerce-auth-db-1" }
        "catalog_db" { $cName = "e-commerce-catalog-db-1" }
        "user_db" { $cName = "e-commerce-user-db-1" }
        "cart_db" { $cName = "e-commerce-cart-db-1" }
        "order_db" { $cName = "e-commerce-order-db-1" }
        "payment_db" { $cName = "e-commerce-payment-db-1" }
        "ship_db" { $cName = "e-commerce-shipping-db-1" }
        "product_db" { $cName = "e-commerce-product-db-1" }
        "recommender_db" { $cName = "e-commerce-recommender-db-1" }
    }

    if ($cName) {
        $cmd = "cmd.exe /c `"type $file | docker exec -i $cName psql -U postgres -d $($seed.Db)`""
        Write-Host "Running: $cmd"
        Invoke-Expression $cmd
    }
}

Write-Host "Flushing Redis cache..."
Invoke-Expression "cmd.exe /c `"docker exec -i e-commerce-redis-1 redis-cli flushall`""

Write-Host "Finished seeding SQL files."
