import json

with open("CMIP JSONs/CMIP6_institution_id.json", "r", encoding='utf-8') as f, open("data/institutions.jsonl", 'a', encoding='utf-8') as jsonl_file:
    data = json.load(f)
    for institution, description in data["institution_id"].items():
        print(institution)
        print(description)
        instructions_outputs = [
            (f"What is {institution}?", f"{institution} is an institution ID and abbreviation representing an insitution contributing data to the ESGF system described as follows: {description}."),
            (f"Describe the institution {institution}.",
             f"Of course! {institution} is an institution ID and abbreviation that is described within the ESGF databse as: {description}."),
            (f"What do you know about {institution}?",
             f"Here is what I know about {institution}. It is an institution ID representing an institution contributing data to ESGF with the following description: {description}."),
            (f"Please explain {institution} as described within ESGF.",
             f"Sure! Here is how the institution {institution} is described within ESGF: {description}."),
            (f"Can you define {institution}?",
             f"Of course! {institution} is an institution ID and abbreviation representing an insitution contributing data to the ESGF. Here is how it is described: {description}."),
        ]
        for instruction, output in instructions_outputs:
            entry = {
                'Instruction': instruction,
                'Input': "",
                'Output': output
            }
            jsonl_file.write(json.dumps(entry) + "\n")
