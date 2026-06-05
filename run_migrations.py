import subprocess

try:
    print("Running makemigrations...")
    result = subprocess.run(
        ["docker", "exec", "e-commerce-user-service-1", "python", "manage.py", "makemigrations", "user", "--noinput"],
        capture_output=True,
        text=True
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    
    if "Did you rename" in result.stdout or "Did you rename" in result.stderr:
        print("Interactive prompt detected. Using yes | ...")
        # try piping
        result = subprocess.run(
            'echo "1" | docker exec -i e-commerce-user-service-1 python manage.py makemigrations user',
            shell=True, capture_output=True, text=True
        )
        print("STDOUT2:", result.stdout)
        print("STDERR2:", result.stderr)
except Exception as e:
    print("Exception:", str(e))
