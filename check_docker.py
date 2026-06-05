import subprocess
r = subprocess.run(["docker", "ps"], capture_output=True, text=True)
print(r.stdout)
