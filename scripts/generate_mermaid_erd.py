import os
import ast
from pathlib import Path

def extract_models(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    models = {}
    relationships = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from models.Model or similar
            is_model = any(
                (isinstance(b, ast.Attribute) and b.attr == "Model") or
                (isinstance(b, ast.Name) and b.id in ["Model", "AbstractBaseUser"])
                for b in node.bases
            )
            
            if not is_model and not any("Model" in getattr(b, "id", "") for b in node.bases):
                # Try to include it if it looks like a model (has fields)
                pass

            fields = []
            for item in node.body:
                if isinstance(item, ast.Assign) and len(item.targets) == 1:
                    target = item.targets[0]
                    if isinstance(target, ast.Name):
                        field_name = target.id
                        field_type = "TYPE"
                        
                        if isinstance(item.value, ast.Call):
                            func = item.value.func
                            if isinstance(func, ast.Attribute):
                                field_type = func.attr
                                if field_type in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                                    if item.value.args:
                                        rel_arg = item.value.args[0]
                                        rel_type = "||--o{" if field_type == "ForeignKey" else "||--||" if field_type == "OneToOneField" else "}o--o{"
                                        if isinstance(rel_arg, ast.Constant):
                                            rel_model = rel_arg.value.split(".")[-1]
                                            relationships.append(f"{node.name} {rel_type} {rel_model} : {field_name}")
                                        elif isinstance(rel_arg, ast.Name):
                                            relationships.append(f"{node.name} {rel_type} {rel_arg.id} : {field_name}")

                        fields.append(f"{field_type} {field_name}")

            models[node.name] = fields

    return models, relationships

def main():
    base_dir = Path(__file__).resolve().parent.parent
    services = [d for d in os.listdir(base_dir) if d.endswith("-service")]
    
    docs_dir = base_dir / "docs"
    os.makedirs(docs_dir, exist_ok=True)
    
    mermaid_code = ["erDiagram"]

    for service in services:
        service_path = base_dir / service
        models_paths = list(service_path.rglob("models.py"))
        
        if not models_paths:
            continue
            
        mermaid_code.append(f"    %% ========================")
        mermaid_code.append(f"    %% Service: {service}")
        mermaid_code.append(f"    %% ========================")
        
        prefix = service.replace("-service", "").capitalize()
        
        for model_path in models_paths:
            try:
                models, relationships = extract_models(model_path)
                
                for model_name, fields in models.items():
                    if not fields:
                        continue
                    prefixed_model = f"{prefix}_{model_name}"
                    mermaid_code.append(f"    {prefixed_model} {{")
                    for field in fields:
                        mermaid_code.append(f"        {field}")
                    mermaid_code.append("    }")
                
                for rel in relationships:
                    # rel is in format: ModelA ||--o{ ModelB : field
                    parts = rel.split(" ")
                    if len(parts) >= 5:
                        model_a, rel_type, model_b, colon, field_name = parts[0], parts[1], parts[2], parts[3], parts[4]
                        mermaid_code.append(f"    {prefix}_{model_a} {rel_type} {prefix}_{model_b} : {field_name}")
            except Exception as e:
                print(f"Error parsing {model_path}: {e}")

    output_path = docs_dir / "system_erd.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# System Database ERD\n\n")
        f.write("```mermaid\n")
        f.write("\n".join(mermaid_code))
        f.write("\n```\n")
        
    print(f"ERD successfully generated at: {output_path}")

if __name__ == "__main__":
    main()
