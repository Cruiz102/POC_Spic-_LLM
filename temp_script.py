import json
with open("json.json") as f:
    print(type(json.load(f)[0]))
