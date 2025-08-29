import json

with open("CMIP JSONs/CMIP6_source_id.json", "r", encoding='utf-8') as f, open("data/sources.jsonl", 'a', encoding='utf-8') as jsonl_file:
    data = json.load(f)
    instruction = "List every source id or model in the ESGF database."
    out = ""
    for i, source in enumerate(data["source_id"]):
        if source == data["source_id"][source]['label_extended']:
            out += f'{i + 1}. {source}\n'
        else:
            out += f'{i + 1}. {source}: {data["source_id"][source]['label_extended']}\n'
    print(instruction)
    print(out)
    entry = {
        'Instruction': instruction,
        'Input': "",
        'Output': out
    }
    jsonl_file.write(json.dumps(entry) + "\n")
