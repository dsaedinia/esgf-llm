import os
import json

# Combine all JSONL files in the 'data' directory into a single JSONL file

filepath = 'data'
combined_data = []
for filename in os.listdir(filepath):
    if filename.endswith('.jsonl'):
        file_path = os.path.join(filepath, filename)
        with open(file_path, 'r') as f:
            for line in f:
                combined_data.append(json.loads(line))

with open('all_data.jsonl', 'w') as f:
    for data in combined_data:
        f.write(json.dumps(data) + '\n')
