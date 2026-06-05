import os
import glob

base_dir = r"c:\AnhDLM\e-commerce"
entrypoints = glob.glob(os.path.join(base_dir, "*", "entrypoint.sh"))

target_text = """echo "Starting server..."
python manage.py runserver 0.0.0.0:8000"""

target_text_dos = "echo \"Starting server...\"\r\npython manage.py runserver 0.0.0.0:8000"

replacement_text = """if [ $# -eq 0 ]; then
  echo "Starting server..."
  exec python manage.py runserver 0.0.0.0:8000
else
  echo "Executing command: $@"
  exec "$@"
fi"""

for ep in entrypoints:
    with open(ep, "r", encoding="utf-8") as f:
        content = f.read()
    
    if target_text in content or target_text_dos in content:
        content = content.replace(target_text, replacement_text)
        content = content.replace(target_text_dos, replacement_text)
        
        with open(ep, "w", encoding="utf-8", newline='\n') as f:
            f.write(content)
        print(f"Updated {ep}")
    else:
        print(f"Skipped {ep} (target text not found)")
