import subprocess
r = subprocess.run(["docker", "logs", "--tail", "100", "e-commerce-order-service-1"], capture_output=True, text=True)
with open("c:\\AnhDLM\\e-commerce\\order_logs.txt", "w") as f:
    f.write(r.stdout)
    f.write(r.stderr)
