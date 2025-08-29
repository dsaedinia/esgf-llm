import json

with open("CMIP JSONs/MIP_variables.json", "r", encoding='utf-8') as f, open("glossary_data.md", 'a', encoding='utf-8') as out_file:
    data = json.load(f)
    variables = data.get("variables", {})
    sorted_items = sorted(
        variables.items(), key=lambda item: item[1]['long_name'].lower())
    for var_id, var_name in sorted_items:
        # Create a markdown entry for each variable
        entry = f"- **{var_name['long_name'].replace('_', ' ')}** → `{var_id}`\n"
        # Write the entry to the markdown file
        out_file.write(entry)
print(f"Successfully created glossary_data.md with {len(variables)} entries.")


# Finds variables with duplicate long names in the MIP_variables.json file
# and prints them out


# with open("/Users/l5s/Desktop/LLM/CMIP JSONs/MIP_variables.json", "r", encoding='utf-8') as f, open("variable_repeats.md", 'a', encoding='utf-8') as out_file:
#     data = json.load(f)
#     variables = data.get("variables", {})
#     repeat_long_names = dict()

#     for var_id, var_name in variables.items():
#         # add the long name to the dictionary
#         if var_name['long_name'] not in repeat_long_names:
#             repeat_long_names[var_name['long_name']] = []
#             repeat_long_names[var_name['long_name']].append(var_id)
#         else:
#             repeat_long_names[var_name['long_name']].append(var_id)

#     for repeats in repeat_long_names:
#         if len(repeat_long_names[repeats]) > 1:
#             # Create a markdown entry for each variable
#             entry = f"- **{repeats}** → {', '.join(repeat_long_names[repeats])}\n"
#             # Write the entry to the markdown file
#             out_file.write(entry)
