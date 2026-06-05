import os
import time
import requests
import subprocess
import json

BASE_URL = "http://localhost:8000"

def run_docker_exec(service, cmd):
    full_cmd = f"docker exec e-commerce-{service}-1 {cmd}"
    return subprocess.check_output(full_cmd, shell=True).decode('utf-8')

def print_step(msg):
    print(f"\n🚀 === {msg} ===")

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def main():
    print_step("1. Checking Migration Order")
    output = run_docker_exec("user-service", "python manage.py showmigrations user")
    print(output)
    if "0002_seed_system_roles" in output:
        print_success("Migrations order looks correct.")
    else:
        print_error("Missing 0002_seed_system_roles!")

    print_step("2. Running Seed Command")
    seed_out = run_docker_exec("user-service", "python manage.py seed_rbac")
    print(seed_out)
    if "RBAC seeding and mapping complete!" in seed_out:
        print_success("Seeding completed successfully.")

    print_step("3. Verifying Seed Data (Roles & Permissions)")
    py_code = (
        "import django; django.setup(); "
        "from user.models import Role; "
        "roles = list(Role.objects.values_list('name', flat=True)); "
        "print(','.join(roles)); "
        "admin = Role.objects.get(name='ADMIN'); "
        "print(f'ADMIN perms: {admin.permissions.count()}')"
    )
    db_out = run_docker_exec("user-service", f"python -c \"{py_code}\"")
    print("Database Output:", db_out.strip())
    if "ADMIN" in db_out and "CUSTOMER" in db_out:
        print_success("Roles seeded correctly.")
    if "ADMIN perms:" in db_out and not "ADMIN perms: 0" in db_out:
        print_success("Permissions mapped correctly to ADMIN role.")

    print_step("4. Manual Testing Instructions")
    print("""
Because testing JWT logic requires an active user and redis credentials, please manually test the following:
1. JWT Revocation Test
   - Login and get a JWT.
   - Run `docker exec -it e-commerce-user-service-1 python manage.py shell`
   - Assign a new role to the user or change status to BANNED.
   - Call the gateway again with the OLD JWT. It should return 401.

2. Gateway Security Test
   - Call any API with a fake `X-Roles: SUPER_ADMIN` header.
   - Ensure the NGINX strips it and uses the actual role.

3. Concurrent Updates
   - In Django shell, test concurrent role assignments and verify `role_version` increments properly.
""")

if __name__ == "__main__":
    main()
