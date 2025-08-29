import json

with open("CMIP JSONs/CMIP6_experiment_id.json", "r", encoding='utf-8') as f, open("data/experiments.jsonl", 'a', encoding='utf-8') as jsonl_file:
    data = json.load(f)
    count = 0
    for experiment, details in data["experiment_id"].items():
        count += 1
        description = details["experiment"]
        instructions_outputs = [
            (f"What is {experiment}?", f"{experiment} is an experiment ID representing an experiment within the ESGF system described as follows: {description}."),
            (f"Describe the experiment {experiment}.",
             f"{experiment} is described within the ESGF databse as: {description}."),
            (f"What do you know about {experiment}?",
             f"Here is what I know about {experiment}. It is an experiment ID representing an experiemnt with the following description: {description}."),
            (f"Please explain {experiment} as described within ESGF.",
             f"Sure! Here is how the experiment {experiment} is described within ESGF: {description}."),
            (f"Can you define {experiment}?",
             f"Of course! {experiment} is an experiment ID representing an experiment within the ESGF system. Here is how it is described: {description}."),
        ]
        print(count, experiment)
        for instruction, output in instructions_outputs:

            entry = {
                'Instruction': instruction,
                'Input': "",
                'Output': output
            }
            jsonl_file.write(json.dumps(entry) + "\n")
