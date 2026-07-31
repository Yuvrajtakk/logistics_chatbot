import yaml

with open("semantic/schema_cards.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)

print(data.keys())
print(data["olist_orders_dataset"]["joins"])