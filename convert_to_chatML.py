# Convert JSONL from instruction output files to ChatML format for fine-tuning

import json


def convert_jsonl_to_chatml(input_path, output_path, system_prompt="You are an expert assistant trained on ESGF (Earth System Grid Federation) data. "
                            "You help users navigate, access, and understand Earth system model datasets, metadata, and ESGF-related tools. "
                            "Provide accurate, concise, and context-aware answers tailored to scientific users."):
    conversations = []

    with open(input_path, "r", encoding="utf-8") as infile:
        for line in infile:

            item = json.loads(line)
            instruction = item['Instruction'].strip()
            # For now we don't have any input so I will fix this when we do
            input_text = item['Input'].strip()
            output = item['Output'].strip()

            conversation = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": instruction},
                {"role": "assistant", "content": output}
            ]

            conversations.append(conversation)
    chatml_data = {"conversations": conversations}
    # Save as a single JSON array
    with open(output_path, "w", encoding="utf-8") as outfile:
        json.dump(chatml_data, outfile, indent=2, ensure_ascii=False)

    print(f"✅ Conversion complete! Saved as: {output_path}")


# Function Call
convert_jsonl_to_chatml("all_data.jsonl", "chatml_data.json")
