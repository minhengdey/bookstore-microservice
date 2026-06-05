import subprocess
def get_logs():
    try:
        r = subprocess.run(["docker", "logs", "--tail", "100", "e-commerce-order-service-1"], capture_output=True, text=True)
        print("STDOUT:", r.stdout)
        print("STDERR:", r.stderr)
    except Exception as e:
        print("Error:", e)

    print("====================")
    try:
        r2 = subprocess.run(["docker", "logs", "--tail", "100", "e-commerce-product-service-1"], capture_output=True, text=True)
        print("PROD STDOUT:", r2.stdout)
        print("PROD STDERR:", r2.stderr)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    get_logs()
