import subprocess

services_to_rebuild = [
    "inventory-service",
    "inventory-outbox-worker",
    "inventory-order-consumer",
    "payment-consumer",
    "payment-outbox-worker",
    "interaction-outbox-worker"
]

print("Applying fixes by rebuilding and restarting affected services...")
subprocess.run(["docker", "compose", "up", "-d", "--build"] + services_to_rebuild)
print("Done.")
