import yaml

with open("semantic/glossary.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)

print(data.keys())