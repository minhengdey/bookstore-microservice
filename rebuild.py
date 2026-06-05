import subprocess
subprocess.run(["docker", "compose", "up", "-d", "--build", "order-service"])
