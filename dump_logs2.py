import subprocess

def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.stdout + "\n" + r.stderr
    except Exception as e:
        return str(e)

print("--- NGINX LOGS ---")
print(run(["docker", "logs", "--tail", "50", "e-commerce-nginx-1"]))
print("\n--- API-GATEWAY LOGS ---")
print(run(["docker", "logs", "--tail", "50", "e-commerce-api-gateway-1"]))
print("\n--- MODEL-SERVING-SERVICE LOGS ---")
print(run(["docker", "logs", "--tail", "50", "e-commerce-model-serving-service-1"]))
print("\n--- DOCKER PS ---")
print(run(["docker", "ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Ports}}"]))
