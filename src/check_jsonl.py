import json

with open("semantic/examples.jsonl", encoding="utf-8") as f:
    for line_num, line in enumerate(f, start=1):
        example = json.loads(line)
        print(line_num, example["question"])