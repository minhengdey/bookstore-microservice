import subprocess

try:
    print("Running makemigrations for inventory...")
    res1 = subprocess.run(
        ["docker", "exec", "e-commerce-inventory-service-1", "python", "manage.py", "makemigrations", "inventory", "--noinput"],
        capture_output=True, text=True
    )
    print("MIGRATIONS STDOUT:", res1.stdout)
    print("MIGRATIONS STDERR:", res1.stderr)

    print("Running migrate for inventory...")
    res2 = subprocess.run(
        ["docker", "exec", "e-commerce-inventory-service-1", "python", "manage.py", "migrate", "--noinput"],
        capture_output=True, text=True
    )
    print("MIGRATE STDOUT:", res2.stdout)
    print("MIGRATE STDERR:", res2.stderr)

except Exception as e:
    print("Exception:", str(e))
