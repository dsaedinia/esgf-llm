# Convert our data into alpaca JSON file for fine-tuning LLAMA3 from CSV file
import json
import csv

# has been adjusted for particular node CSV file
# May be remade for other CSV files


def make_json(csvPath, jsonPath):
    data = []

    with open(csvPath, encoding='utf-8') as csvf, open(jsonPath, 'a', encoding='utf-8') as jsonl_file:
        csvReader = csv.DictReader(csvf)
        out = ""
        for i, row in enumerate(csvReader):
            out += f'{i + 1}. {row["\ufeffNode address"]}: {row['CMIP Activity']}\n'

        entry = {
            'Instruction': 'What activities or MIPs are each ESGF node associated with?',
            'Input': "",
            'Output': out
        }
        jsonl_file.write(json.dumps(entry) + "\n")


csvPath = "CMIP CSVs/CMIP ESGF Nodes.csv"
jsonPath = 'data/nodes.jsonl'
make_json(csvPath, jsonPath)
