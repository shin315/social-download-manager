import json; data = json.load(open("version.json")); data["version"] = "1.1.0"; data["release_date"] = "2025-03-15"; json.dump(data, open("version.json", "w"), indent=2)
