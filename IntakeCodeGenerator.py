import json
import os
import random
import re

SEED = 42
SAMPLESIZE = 600


class IntakeCodeGenerator:
    def __init__(
        self,
        output_path="data/intake_outputs_ML.json",
        input_path="CMIP JSONs/CMIP6_CV.json",
        system_prompt="""You are the ESGF Assistant, a domain-specific LLM that helps users discover and access Earth System Grid Federation (ESGF) data. Generate accurate and runnable Python code using the intake-esgf library when appropriate. Carefully interpret key facets mentioned in the prompt such as variable_id, experiment_id, source_id, institution_id, and frequency and ensure your code reflects them correctly. Keep outputs clear, factual, and focused on the requested task.""",
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.conversations = []
        self.system_prompt = system_prompt
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    ####################
    # Helper Functions #
    ####################

    def snippets_to_chatML(self, snippets: list[tuple[str, str]]):
        for instruction, output in snippets:
            conversation = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": instruction},
                {"role": "assistant", "content": output},
            ]
            self.conversations.append(conversation)

    def sub_sampler(
        self, snippets: list[tuple[str, str]], limit: int, seed: int = SEED
    ) -> list[tuple[str, str]]:
        if seed != 0:
            random.seed(seed)
        # cap snippets by limit
        if len(snippets) <= limit:
            return snippets
        # otherwise subsample to the limit
        return random.sample(snippets, limit)

    def get_source_ids(self):
        with open(self.input_path, "r") as f:
            data = json.load(f)
            source_ids = data["CV"]["source_id"].keys()
        return list(source_ids)

    def plural_label(self, items, singular, plural):
        return singular if len(items) == 1 else plural

    def snippets_to_file(self, snippets: list[tuple[str, str]]):
        """
        Takes a list of tuples with instructions and outputs and writes them to a jsonl file

        Parameters:
        snippets (list of tuples): A list of tuples where each tuple contains an instruction and its corresponding output.
        """
        with open(self.output_path, "a", encoding="utf-8") as jsonl_file:
            for instruction, output in snippets:
                entry = {"Instruction": instruction, "Input": "", "Output": output}
                jsonl_file.write(json.dumps(entry) + "\n")

    def snippets_to_file_ML(self):
        """
        Takes a list of conversations and writes them to a jsonl file in chatML format
        """
        chatml_data = {"conversations": self.conversations}
        with open(self.output_path, "w", encoding="utf-8") as jsonl_file:
            jsonl_file.write(json.dumps(chatml_data, indent=2, ensure_ascii=False))
        print("Snippets written to data/intake_outputs_ML.json")

    def normalize_freq(self, user_input: str) -> str:
        user_input = user_input.lower().strip()
        freq_map = {
            "1hr": ["1hr", "1 hour", "1-hour", "hourly", "hour", "one hour"],
            "3hr": ["3hr", "3 hour", "3-hour", "3 hourly", "3 hour mean", "three hour"],
            "6hr": ["6hr", "6 hour", "6-hour", "6 hourly", "6 hour mean", "six hour"],
            "day": ["day", "daily", "day mean"],
            "dec": ["dec", "decadal", "decadal mean"],
            "fx": ["fx", "fixed", "time invariant"],
            "mon": ["mon", "monthly", "month", "monthly mean"],
            "yr": ["yr", "yearly", "annual", "year", "annual mean"],
            "yrPt": ["yrPt", "year point", "yearly point"],
        }

        for key, synonyms in freq_map.items():
            if user_input in synonyms:
                return key
        return user_input  # Return as is if no match found

    def add_multiturn(self, ratio: float = 0.3):
        multiturn_conversations = []

        # going to try out adding multiturn conversations to a random sampling of the dataset
        # hopefully this means I can add to the core instructions easily first
        num_multiturn = int(len(self.conversations) * ratio)
        conversation_indeces = random.sample(
            range(len(self.conversations)), num_multiturn
        )
        for convo_index in conversation_indeces:
            multi_convo = self.conversations[convo_index].copy()
            last_code = multi_convo[-1]["content"]
            last_code = re.search(r"```python\n(.*?)```", last_code, re.DOTALL)

            # if the snippet has no code
            if not last_code:
                continue

            last_code = last_code.group(1)

            follow_up = self._add_facet_followup(last_code)

            if follow_up:
                multi_convo.extend(follow_up)
                print(multi_convo)
                multiturn_conversations.append(multi_convo)

        self.conversations.extend(multiturn_conversations)

    def _add_facet_to_code(self, code, facet_value, facet_list, search_param):
        # going to use regex to find the search( line and add the facet there

        pattern = rf"{facet_list}\s*=\s*\[(.*?)\]"

        match = re.search(pattern, code, re.DOTALL)

        if match:
            existing_values = match.group(1).strip()

            if existing_values:
                new_list = f'{facet_list} = [{existing_values}, "{facet_value}"]'

            else:
                new_list = f'{facet_list} = ["{facet_value}"]'

            code = code.replace(match.group(0), new_list, 1)
            return code

        search_match = re.search(
            r"search_results\s*=\s*cat\.search\((.*?)\)", code, re.DOTALL
        )
        if not search_match:
            return code  # if no search line found, return original code

        comment_match = re.search(r"(# search the catalog.*?\n)", code, re.IGNORECASE)

        if comment_match:
            insert_pos = comment_match.start()
        else:
            # Insert the new list before the search
            insert_pos = search_match.start()

        new_var_line = f'# specify the {facet_list} to search for\n{facet_list} = ["{facet_value}"]\n\n'
        code = code[:insert_pos] + new_var_line + code[insert_pos:]

        # Add parameter to search call
        existing_params = search_match.group(1).strip()
        if existing_params and not existing_params.endswith(","):
            existing_params += ","
        new_params = f"{existing_params}\n    {search_param}={facet_list}"

        code = re.sub(
            r"search_results\s*=\s*cat\.search\((.*?)\)",
            f"search_results = cat.search({new_params}\n)",
            code,
            flags=re.DOTALL,
            count=1,
        )
        return code

    # add facet followups like "add variable gpp" for example
    def _add_facet_followup(self, code: str) -> str:
        facet_options = [
            ("gpp", "variable_id gpp", "variables", "variable_id"),
            ("pr", "variable_id pr", "variables", "variable_id"),
            ("rsds", "variable rsds", "variables", "variable_id"),
            ("ssp585", "experiment_id ssp585", "experiments", "experiment_id"),
            ("mon", "monthly frequency", "frequencies", "frequency"),
            ("CESM2", "model CESM2", "sources", "source_id"),
            (
                "NASA-GISS",
                "institution NASA-GISS",
                "institutions",
                "institution_id",
            ),
            ("day", "daily frequency", "frequencies", "frequency"),
            ("CanESM5", "model CanESM5", "sources", "source_id"),
            ("historical", "experiment_id historical", "experiments", "experiment_id"),
        ]

        random.shuffle(facet_options)
        for facet_value, facet_prompt, facet_list, search_param in facet_options:
            if f"{facet_value}" in code:
                continue  # skip if facet already in code

            new_code = self._add_facet_to_code(
                code, facet_value, facet_list, search_param
            )
            if new_code != code:
                # wrap it back in python ```
                new_code = f"```python\n{new_code}```"
                user_prompts = [
                    f"Can you also add {facet_prompt}?",
                    f"Please include {facet_prompt} as well.",
                    f"Add {facet_prompt} to the search?",
                    f"Could you also include {facet_prompt} in the code?",
                ]

                assistant_responses = [
                    f"Sure! I'll add {facet_prompt}. Here is the updated Python code:",
                    f"Of course! I'll include {facet_prompt}. Here is the revised Python code:",
                    f"Certainly! I'll add {facet_prompt} to the search. Here is the modified Python code:",
                    f"Alright! I'll include {facet_prompt}. Here is the updated Python code:",
                ]
                return [
                    {"role": "user", "content": random.choice(user_prompts)},
                    {
                        "role": "assistant",
                        "content": random.choice(assistant_responses) + f"\n{new_code}",
                    },
                ]
        return []  # return empty if no facet added

    ################################################################
    # Code Generation Functions grouped by facets and combinations #
    ################################################################

    def generate_experiment_list_by_source(
        self, source_id: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on listing experiments from a specific source/model.

        Parameters
        ----------
        source_id (str): The source ID to search for experiments.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        code_template = f"""
```python
# Task: Generate list of experiments for the given source/models

# import necessary libraries
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify the source/model(s) to search for
sources = ["{source_id}"]

# search the catalog with the specified facets
search_results = cat.search(
    source_id=sources
)

# get a list of unique experiments
experiments = sorted(search_results.df["experiment_id"].unique())

# print out our results
print(f"{source_id} Experiements({{len(experiments)}} results):")

for i, experiment in enumerate(experiments):
    print(f"{{i+1}}. {{experiment}}")
```
"""
        prompts = [
            f"Show me what experiments the {source_id} model offers using intake-esgf.",
            f"Using intake-esgf, how can I list all experiments provided by the model {source_id}?",
            f"I want to find out which experiments are available for the {source_id} model using intake-esgf. Can you help?",
            f"Can you provide intake-esgf code to retrieve all experiments associated with the {source_id} model?",
            f"I need a python snippet using intake-esgf to list experiments for the {source_id} model.",
        ]
        responses = [
            f"Sure! Here is how we can show what experiments the {source_id} model offers using intake-esgf:",
            f"Here is how we can list all experiments provided by the model {source_id} using intake-esgf:",
            f"Of course! Here is how we can find out which experiments are available for the {source_id} model using intake-esgf:",
            f"Certainly! Here is how we can retrieve all experiments associated with the {source_id} model using intake-esgf:",
            f"Sure! Here is a python snippet using intake-esgf to list experiments for the {source_id} model:",
        ]

        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_list_all_variables(self) -> list[tuple[str, str]]:
        """Generate intake code snippets that focus on listing all variables available in the catalog.
        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        code_template = """
```python
# Task: Generate list of all variables available in the ESGF catalog

# import necessary libraries
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# search the catalog for all variables
search_results = cat.search()

# get a list of unique variables
variables = sorted(search_results.df["variable_id"].unique())

# print out our results
print(f"Variables({len(variables)} results):")
for i, variable in enumerate(variables):
    print(f"{i+1}. {variable}")
```
"""
        prompts = [
            "Write Python code using intake-esgf to list all available variables in the ESGF catalog.",
            "Can you show me Python code using intake-esgf to retrieve all variables available in the ESGF catalog?",
            "I want intake-esgf Python code that lists every variable found in the ESGF catalog.",
            "Using intake-esgf, write Python code to get a complete list of all variables available in ESGF.",
            "How do I write Python code using intake-esgf to display all variables in the ESGF catalog?",
            "Show me a Python snippet using intake-esgf to enumerate all variables available in ESGF.",
            "I'm trying to find a Python example with intake-esgf that lists all variables in ESGF. Can you help?",
            "Provide Python code using intake-esgf to print all variables available in the ESGF catalog.",
            "Give me intake-esgf Python code that fetches every variable listed in the ESGF catalog.",
            "I need Python code with intake-esgf to explore all the variables in the ESGF catalog.",
            "Using Python and intake-esgf, how can I query the ESGF catalog for all available variables?",
            "What's the Python code for scanning all ESGF variables with intake-esgf?",
            "Create a Python script that utilizes intake-esgf to extract every variable listed in ESGF.",
            "How would I use Python and the intake-esgf library to find all variable options in ESGF?",
            "Can you help me generate Python + intake-esgf code to browse every ESGF variable?",
        ]

        responses = [
            "Sure! Here is how we can list all available variables in the ESGF catalog using intake-esgf in Python:",
            "Absolutely! Here is how we can retrieve all available variables in the ESGF catalog using intake-esgf in Python:",
            "Of course! Here is how to list every variable found in the ESGF catalog using intake-esgf in Python:",
            "Sure! Here is how we can get a complete list of all variables available in ESGF using intake-esgf in Python:",
            "Here is a way to display all variables in the ESGF catalog using intake-esgf in Python:",
            "Certainly! Here is a snippet that enumerates all variables available in ESGF using intake-esgf in Python:",
            "Yes! Here is how to list all variables in ESGF using intake-esgf in Python:",
            "Here you go! Here is how we can print all variables available in the ESGF catalog using intake-esgf in Python:",
            "Sure thing! Here is how to fetch every variable listed in the ESGF catalog using intake-esgf in Python:",
            "Absolutely! Here is how we can explore all variables in the ESGF catalog using intake-esgf in Python:",
            "Here's how to query the ESGF catalog for all available variables using intake-esgf in Python:",
            "Here's the Python code for scanning all ESGF variables using intake-esgf:",
            "Sure! Here's how to create a Python script using intake-esgf to extract every variable listed in ESGF:",
            "Here's how to use Python and the intake-esgf library to find all variable options in ESGF:",
            "Definitely! Here's how to browse every ESGF variable using intake-esgf in Python:",
        ]
        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_list_all_models(self) -> list[tuple[str, str]]:
        """Generate intake code snippets that focus on listing all models available in the catalog.
        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        code_template = """
```python
# Task: Generate list of all models available in the ESGF catalog
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# search the catalog for all variables
search_results = cat.search()

# get a list of unique variables
models = sorted(search_results.df["source_id"].unique())

# print out our results
print(f"Models({len(models)} results):")
for i, model in enumerate(models):
    print(f"{i+1}. {model}")
```
"""
        prompts = [
            "Write Python code using intake-esgf to list all available models in the ESGF catalog.",
            "Can you show me Python code using intake-esgf to retrieve all models available in the ESGF catalog?",
            "I want intake-esgf Python code that lists every model found in the ESGF catalog.",
            "Using intake-esgf, write Python code to get a complete list of all models available in ESGF.",
            "How do I write Python code using intake-esgf to display all models in the ESGF catalog?",
            "Show me a Python snippet using intake-esgf to enumerate all models available in ESGF.",
            "I'm trying to find a Python example with intake-esgf that lists all models in ESGF. Can you help?",
            "Provide Python code using intake-esgf to print all models available in the ESGF catalog.",
            "Give me intake-esgf Python code that fetches every model listed in the ESGF catalog.",
            "I need Python code with intake-esgf to explore all the models in the ESGF catalog.",
        ]
        responses = [
            "Sure! Here is how we can list all available models in the ESGF catalog using intake-esgf in Python:",
            "Absolutely! Here is how we can retrieve all available models in the ESGF catalog using intake-esgf in Python:",
            "Of course! Here is how to list every model found in the ESGF catalog using intake-esgf in Python:",
            "Sure! Here is how we can get a complete list of all models available in ESGF using intake-esgf in Python:",
            "Here is a way to display all models in the ESGF catalog using intake-esgf in Python:",
            "Certainly! Here is a snippet that enumerates all models available in ESGF using intake-esgf in Python:",
            "Yes! Here is how to list all models in ESGF using intake-esgf in Python:",
            "Here you go! Here is how we can print all models available in the ESGF catalog using intake-esgf in Python:",
            "Sure thing! Here is how to fetch every model listed in the ESGF catalog using intake-esgf in Python:",
            "Absolutely! Here is how we can explore all models in the ESGF catalog using intake-esgf in Python:",
        ]
        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_dataset_list_by_institution(
        self, institution: str, institution_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on institution and returning as list of tuples representing instructions and output code.
        Will use a combination of single and multiple institutions for prompts to teach the model to generalize appropriately.

        Parameters
        ----------
        institution: The institution or institutions to search for, formatted as a string.
        institution_label: The label for the institution, singular or plural.
        return: A list of tuples containing the instruction and output code snippet.
        """
        # Institution in prompt does not need quotes
        prompt_institution = institution.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets from the given institution(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the institutions to search for
institutions = [{institution}]

# search the catalog with the specified facets
search_results = cat.search(
    institution_id=institutions,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""
        dl_code_template = f"""
```python
# Task: Search for and download all datasets from the given institution(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the institutions to search for
institutions = [{institution}]

# search the catalog with the specified facets
search_results = cat.search(
    institution_id=institutions,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting datasets to a dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain data from {institution_label} {prompt_institution} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include data from {institution_label} {prompt_institution}?",
            f"I'm looking for datasets with data from {institution_label} {prompt_institution}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing data from {institution_label} {prompt_institution}?",
            f"I need a python snippet using intake-esgf to get datasets that have data from {institution_label} {prompt_institution}.",
        ]

        list_responses = [
            f"Sure! Here is how we can list all datasets that contain data from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Here is how we can find datasets that include data from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with data from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing data from {institution_label} {prompt_institution}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have data from {institution_label} {prompt_institution}:",
        ]

        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Show me code to download all datasets that contain data from {institution_label} {prompt_institution} using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include data from {institution_label} {prompt_institution}?",
            f"I'm looking to download datasets with data from {institution_label} {prompt_institution}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing data from {institution_label} {prompt_institution}?",
            f"I need a python snippet using intake-esgf to download datasets that have data from {institution_label} {prompt_institution}.",
        ]

        dl_responses = [
            f"Sure! Here is how we can download all datasets that contain data from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Here is how we can find and download datasets that include data from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with data from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing data from {institution_label} {prompt_institution}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have data from {institution_label} {prompt_institution}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        # Return both listing and downloading snippets
        return list_snippets + dl_snippets

    def generate_dataset_list_by_freq(self, freq: str) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on frequency and returning as list of tuples representing instructions and output code.
        Will use a combination of single and multiple frequencies for prompts to teach the model to generalize appropriately.

        Parameters
        ----------
        freq: The frequency or frequencies to search for, formatted as a string.
        return: A list of tuples containing the instruction and output code snippet.
        """
        prompt_freq = freq.replace('"', "")
        code_freq = f'"{self.normalize_freq(freq)}"'
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given frequency

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the frequency to search for
frequencies = [{code_freq}]

search_results = cat.search(
    frequency=frequencies,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""

        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given frequency

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the frequency to search for
frequencies = [{code_freq}]

# search the catalog with the specified facets 
search_results = cat.search(
    frequency=frequencies,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting datasets to a dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {prompt_freq} frequency using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {prompt_freq} frequency?",
            f"I'm looking for datasets with {prompt_freq} frequency. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {prompt_freq} frequency?",
            f"I need a python snippet using intake-esgf to get datasets that have {prompt_freq} frequency.",
        ]
        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {prompt_freq} frequency using intake-esgf in python:",
            f"Here is how we can find datasets that include {prompt_freq} frequency using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {prompt_freq} frequency using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {prompt_freq} frequency:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {prompt_freq} frequency:",
        ]
        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Search for all datasets that contain {prompt_freq} frequency and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {prompt_freq} frequency?",
            f"I'm looking to download datasets with {prompt_freq} frequency. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {prompt_freq} frequency?",
            f"I need a python snippet using intake-esgf to download datasets that have {prompt_freq} frequency.",
        ]
        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {prompt_freq} frequency using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {prompt_freq} frequency using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {prompt_freq} frequency using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {prompt_freq} frequency:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {prompt_freq} frequency:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_model_list_by_variable_scenario(
        self, scenario: str, variable: str, scenario_label: str, variable_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for models based on variables and scenarios/experiments.

        Parameters
        ----------
        scenario: The scenario or scenarios to search for.
        variable: The variable or variables to search for.
        scenario_label: The label for the scenario, singular or plural.
        variable_label: The label for the variable, singular or plural.

        Returns
        -------
        list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
        """
        prompt_scenario = scenario.replace('"', "")
        prompt_variable = variable.replace('"', "")
        code_template = f"""
```python
# Task: Generate list of all source/models for the given variable(s) and scenario(s)

# import necessary libraries
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify the scenario/experiments and variables to search for
experiments = [{scenario}]
variables = [{variable}]

# search the catalog with the specified facets
search_results = cat.search(
    experiment_id=experiments,
    variable_id=variables
)

# get a list of unique models
models = sorted(search_results.df["source_id"].unique())

# print out our results
print(f"Models({{len(models)}} results):")
for i, model in enumerate(models):
    print(f"{{i+1}}. {{model}}")
```
"""
        prompts = [
            f"Name the models that have {prompt_scenario} {scenario_label} for {variable_label} {prompt_variable} using intake-esgf in python.",
            f"Using the help of intake-esgf, which models contain {prompt_variable} data under {prompt_scenario} {scenario_label}?",
            f"Can you list the models that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} with intake-esgf?",
            f"Retrieve all models for {prompt_scenario} {scenario_label} for {variable_label} {prompt_variable} with the help of intake-esgf.",
            f"I would like to generate some intake-esgf code. Can you show me how to find what models support {prompt_variable} across {prompt_scenario} {scenario_label}?",
        ]

        responses = [
            f"Sure, here is how we can name the models that have {prompt_scenario} {scenario_label} and {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Alright! Here is how we can find which models contain {prompt_variable} data under {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Sure! Here is how we can list the models that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Ok! Here is how we can retrieve all models for {prompt_scenario} {scenario_label} and {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Of course! Here is how we can find what models support {prompt_variable} across {prompt_scenario} {scenario_label} using intake-esgf in python:",
        ]

        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_dataset_list_by_variable_scenario(
        self, scenario: str, variable: str, scenario_label: str, variable_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based on variables and scenarios/experiments.

        Parameters
        ----------
        scenario: The scenario or scenarios to search for.
        variable: The variable or variables to search for.
        scenario_label: The label for the scenario, singular or plural.
        variable_label: The label for the variable, singular or plural.

        Returns
        -------
        list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
        """
        prompt_scenario = scenario.replace('"', "")
        prompt_variable = variable.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given variable(s) and scenario(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the scenarios/experiments and variables to search for
experiments = [{scenario}]
variables = [{variable}]

# search the catalog with the specified facets
search_results = cat.search(
    experiment_id=experiments,
    variable_id=variables
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""

        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given variable(s) and scenario(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the scenarios/experiments and variables to search for
experiments = [{scenario}]
variables = [{variable}]

# search the catalog with the specified facets
search_results = cat.search(
    experiment_id=experiments,
    variable_id=variables
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting data into dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}?",
            f"I'm looking for datasets with {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}?",
            f"I need a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}.",
        ]
        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Absolutely! Here is how we can find datasets that include {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}:",
        ]

        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]
        dl_prompts = [
            f"Show me code to download all datasets that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}?",
            f"I'm looking to download datasets with {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}?",
            f"I need a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}.",
        ]

        dl_responses = [
            f"Sure! Here is how we can download all datasets that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Absolutely! Here is how we can find and download datasets that include {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        # Return both listing and downloading snippets
        return list_snippets + dl_snippets

    def generate_model_list_by_variable(
        self, variable: str, variable_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for models based only on variables and returning as list of tuples representing instructions and output code.
        Will use a combination of single and multiple variables for prompts to teach the model to generalize appropriately.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        return: A list of tuples containing the instruction and output code snippet.
        """

        prompt_variable = variable.replace('"', "")
        code_template = f"""
```python
# Task: Generate list of all source/model(s) for the given variable(s)

# import necessary libraries
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify variables to search for
variables = [{variable}]

# search the catalog for models with the specified facets
search_results = cat.search(
    variable_id=variables
)

# get a list of unique models
models = sorted(search_results.df["source_id"].unique())

# print out our results
print(f"Models({{len(models)}} results):")
for i, model in enumerate(models):
    print(f"{{i+1}}. {{model}}")
```
"""
        prompts = [
            f"Name the models that have {variable_label} {prompt_variable} using intake-esgf in python.",
            f"List all models that contain data for {variable_label} {prompt_variable} using intake-esgf in python.",
            f"I'm trying to search for models that have data on {variable_label} {prompt_variable} using the intake-esgf library in python. Can you help?",
            f"I want python code that lists all the models containing {variable_label} {prompt_variable}.",
            f"I need help writing intake-esgf code that shows me what models include the {variable_label} {prompt_variable}.",
            f"Could you provide python code to find models that include {variable_label} {prompt_variable} using intake-esgf?",
            f"How do I list all the models with {variable_label} {prompt_variable} data via intake-esgf in python?",
            f"Show me a python example that retrieves models containing {variable_label} {prompt_variable} from intake-esgf.",
            f"Write a python script using intake-esgf to get all models that have {variable_label} {prompt_variable}.",
            f"I need a python snippet that searches intake-esgf for models containing {variable_label} {prompt_variable}.",
            f"Which climate models provide data for {variable_label} {prompt_variable} using intake-esgf in Python?",
            f"Show me all CMIP6 models that include {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"How can I find models with {variable_label} {prompt_variable} using intake-esgf in Python?",
            f"I'm looking for models that contain data on {prompt_variable}. Can you give me Python intake-esgf code?",
            f"Retrieve all models associated with {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"Can you help me get the model names that include {variable_label} {prompt_variable} using intake-esgf in Python?",
            f"Write intake-esgf code in Python to identify models supporting {variable_label} {prompt_variable}.",
            f"Give me an example of Python code that lists models for {variable_label} {prompt_variable} using intake-esgf.",
            f"How to check which models have {variable_label} {prompt_variable} data using intake-esgf in Python?",
            f"Find all models that include the variable {prompt_variable} using intake-esgf in Python.",
        ]

        responses = [
            f"Right! Here is how we can name the models that have {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Here is how we can list the models that contain data for {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Yes! I can help you with that. Here is how we can search for models that have data on {variable_label} {prompt_variable} using the intake-esgf library in python:",
            f"Here is a way we can list all the models containing {variable_label} {prompt_variable} using intake-esgf in python:",
            f"I can help you with that! Here is how we can write intake-esgf code that shows you what models include the {variable_label} {prompt_variable} in python:",
            f"Certainly! Here's python code to find models that include {variable_label} {prompt_variable} using intake-esgf:",
            f"To list all the models with {variable_label} {prompt_variable} data via intake-esgf in python, you can use the following code:",
            f"Here's a python example that retrieves models containing {variable_label} {prompt_variable} from intake-esgf:",
            f"Sure! Here's a python script using intake-esgf to get all models that have {variable_label} {prompt_variable}:",
            f"No problem! Here is a python snippet that searches intake-esgf for models containing {variable_label} {prompt_variable}:",
            f"Here's how you can check which climate models provide data for {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's Python code to show all CMIP6 models that include {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"You can find models with {variable_label} {prompt_variable} using intake-esgf in Python like this:",
            f"Sure! Here's Python code to list models that contain data on {prompt_variable} using intake-esgf:",
            f"Here's how to retrieve all models associated with {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Of course! Here's how to get the model names that include {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's Python code to identify models supporting {variable_label} {prompt_variable} using intake-esgf:",
            f"Here's an example of Python code that lists models for {variable_label} {prompt_variable} using intake-esgf:",
            f"You can check which models have {variable_label} {prompt_variable} data using intake-esgf in Python like this:",
            f"Here's how to find all models that include the variable {prompt_variable} using intake-esgf in Python:",
        ]

        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_dataset_list_by_variable(
        self, variable: str, variable_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on variables and returning as list of tuples representing instructions and output code.
        Will use a combination of single and multiple variables for prompts to teach the model to generalize appropriately.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        return: A list of tuples containing the instruction and output code snippet.
        """
        prompt_variable = variable.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given variable(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the variable(s) to search for
variables = [{variable}]

# search the catalog with the specified facets
search_results = cat.search(
    variable_id= variables
)

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""
        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given variable(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the variable(s) to search for
variables = [{variable}]

# search the catalog with the specified facets
search_results = cat.search(
    variable_id= variables
)

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting datasets to a dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {variable_label} {prompt_variable} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {variable_label} {prompt_variable}?",
            f"I'm looking for datasets with {variable_label} {prompt_variable}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable}?",
            f"I need a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable}.",
            f"Show me how to use intake-esgf in python to list datasets with {variable_label} {prompt_variable}.",
            f"How can I retrieve datasets that include {variable_label} {prompt_variable} using intake-esgf in python?",
            f"Provide a python example using intake-esgf to find datasets containing {variable_label} {prompt_variable}.",
            f"Write a python script with intake-esgf to search for datasets that have {variable_label} {prompt_variable}.",
            f"I want to explore datasets with {variable_label} {prompt_variable} using intake-esgf in python. Can you assist?",
        ]

        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Here is how we can find datasets that include {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable}:",
            f"Here you go! Here is how we can use intake-esgf in python to list datasets with {variable_label} {prompt_variable}:",
            f"Absolutely! Here is how we can retrieve datasets that include {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Certainly! Here is a python example using intake-esgf to find datasets containing {variable_label} {prompt_variable}:",
            f"Sure! Here is a python script with intake-esgf to search for datasets that have {variable_label} {prompt_variable}:",
            f"Of course! Here is how we can explore datasets with {variable_label} {prompt_variable} using intake-esgf in python:",
        ]
        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Search for all datasets that contain {variable_label} {prompt_variable} and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {variable_label} {prompt_variable}?",
            f"I'm looking to download datasets with {variable_label} {prompt_variable}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable}?",
            f"I need a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable}.",
        ]

        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_model_list_by_variable_freq(
        self, variable: str, variable_label: str, freq: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for models based on variables and frequency.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        freq: The frequency to search for, formatted as a string.

        Returns
        -------
        list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
        """

        prompt_variable = variable.replace('"', "")
        code_freq = f'"{self.normalize_freq(freq)}"'

        code_template = f"""
```python
# Task: Generate list of all source/models for the given variable(s) and frequency

# import necessary libraries
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify variables and frequencies to search for
variables = [{variable}]
frequencies = [{code_freq}]

# search the catalog with the specified facets
search_results = cat.search(
    variable_id=variables,
    frequency=frequencies
)

# get a list of unique models
models = sorted(search_results.df["source_id"].unique())

# print out our results
print(f"Models({{len(models)}} results):")
for i, model in enumerate(models):
    print(f"{{i+1}}. {{model}}")
```
"""
        prompts = [
            f"Name the models that have {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python.",
            f"List all models that contain data for {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python.",
            f"I'm trying to search for models that have data on {variable_label} {prompt_variable} at {freq} frequency using the intake-esgf library in python. Can you help?",
            f"I want python code that lists all the models containing {variable_label} {prompt_variable} at {freq} frequency.",
            f"I need help writing intake-esgf code that shows me what models include the {variable_label} {prompt_variable} at {freq} frequency.",
        ]
        responses = [
            f"Right! Here is how we can name the models that have {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Here is how we can list the models that contain data for {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Yes! I can help you with that. Here is how we can search for models that have data on {variable_label} {prompt_variable} at {freq} frequency using the intake-esgf library in python:",
            f"Here is a way we can list all the models containing {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"I can help you with that! Here is how we can write intake-esgf code that shows you what models include the {variable_label} {prompt_variable} at {freq} frequency in python:",
        ]

        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_dataset_list_by_variable_freq(
        self, variable: str, variable_label: str, freq: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based on variables and frequency.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        freq: The frequency to search for, formatted as a string.

        Returns
        -------
        list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
        """

        prompt_variable = variable.replace('"', "")
        code_freq = f'"{self.normalize_freq(freq)}"'

        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given variable(s) and frequency

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables and frequencies to search for
variables = [{variable}]
frequencies = [{code_freq}]

# search the catalog with the specified facets
search_results = cat.search(
    variable_id=variables,
    frequency=frequencies
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```"""

        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given variable(s) and frequency

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables and frequency to search for
variables = [{variable}]
frequencies = [{code_freq}]

# search the catalog for models with the specified variable
search_results = cat.search(
    variable_id=variables,
    frequency=frequencies
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting datasets to a dictionary
dsd = search_results.to_dataset_dict()
```"""

        list_prompts = [
            f"List all datasets that contain {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {variable_label} {prompt_variable} at {freq} frequency?",
            f"I'm looking for datasets with {variable_label} {prompt_variable} at {freq} frequency. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} at {freq} frequency?",
            f"I need a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} at {freq} frequency.",
        ]
        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Here is how we can find datasets that include {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} at {freq} frequency:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} at {freq} frequency:",
        ]

        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]
        dl_prompts = [
            f"Search for all datasets that contain {variable_label} {prompt_variable} at {freq} frequency and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {variable_label} {prompt_variable} at {freq} frequency?",
            f"I'm looking to download datasets with {variable_label} {prompt_variable} at {freq} frequency. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} at {freq} frequency?",
            f"I need a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} at {freq} frequency.",
        ]
        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {variable_label} {prompt_variable} at {freq} frequency using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} at {freq} frequency:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} at {freq} frequency:",
        ]
        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_dataset_by_variable_model_scenario(
        self,
        variable: str,
        variable_label: str,
        source: str,
        source_label: str,
        scenario: str,
        scenario_label: str,
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based on variables, source/model, and scenario/experiment.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        source: The source/model or sources/models to search for, formatted as a string.
        source_label: The label for the source/model, singular or plural.
        scenario: The scenario or scenarios to search for, formatted as a string.
        scenario_label: The label for the scenario, singular or plural.

        Returns
        -------
        list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
        """

        prompt_variable = variable.replace('"', "")
        prompt_source = source.replace('"', "")
        prompt_scenario = scenario.replace('"', "")

        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given variable(s), source/model(s), and scenario/experiment(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables, source/model(s) and scenario/experiment(s) to search for
variables = [{variable}]
sources = [{source}]
experiments = [{scenario}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    variable_id=variables,
    source_id=sources,
    experiment_id=experiments
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""
        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given variable(s), source/model(s), and scenario/experiment(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables, source/model(s) and scenario/experiment(s) to search for
variables = [{variable}]
sources = [{source}]
experiments = [{scenario}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    variable_id=variables,
    source_id=sources,
    experiment_id=experiments
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting datasets to a dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario}?",
            f"I'm looking for datasets with {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}?",
            f"I need a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}.",
        ]
        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Here is how we can find datasets that include {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}:",
        ]
        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]
        dl_prompts = [
            f"Search for all datasets that contain {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario}?",
            f"I'm looking to download datasets with {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}?",
            f"I need a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}.",
        ]
        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {variable_label} {prompt_variable} from {source_label} {prompt_source} for {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} from {source_label} {prompt_source} under {scenario_label} {prompt_scenario}:",
        ]
        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_dataset_list_by_variable_freq_institution(
        self,
        variable: str,
        variable_label: str,
        freq: str,
        institution: str,
        institution_label: str,
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based on variables, frequency, and institution.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        freq: The frequency to search for, formatted as a string.
        institution: The institution or institutions to search for, formatted as a string.
        institution_label: The label for the institution, singular or plural.

        Returns
        -------
        list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
        """

        prompt_variable = variable.replace('"', "")
        prompt_institution = institution.replace('"', "")
        code_freq = f'"{self.normalize_freq(freq)}"'
        list_code_template = f"""


```python
# Task: Generate list of all datasets for the given variable(s), frequency, and institution(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables, institutions and frequency to search for
variables = [{variable}]
institutions = [{institution}]
frequencies = [{code_freq}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    variable_id=variables,
    institution_id=institutions,
    frequency=frequencies
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""

        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given variable(s), frequency, and institution(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables, institutions and frequency to search for
variables = [{variable}]
institutions = [{institution}]
frequencies = [{code_freq}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    variable_id=variables,
    institution_id=institutions,
    frequency=frequencies
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the resulting datasets to a dictionary
dsd = search_results.to_dataset_dict()
```
"""

        list_prompts = [
            f"List all datasets that contain {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}?",
            f"I'm looking for datasets with {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}?",
            f"I need a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}.",
        ]
        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Here is how we can find datasets that include {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}:",
        ]
        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Search for all datasets that contain {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}?",
            f"I'm looking to download datasets with {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}?",
            f"I need a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}.",
        ]

        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {variable_label} {prompt_variable} at {freq} frequency from {institution_label} {prompt_institution}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_dataset_list_by_scenario(
        self, scenario: str, scenario_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on scenarios/experiments and returning as list of tuples representing instructions and output code.

        Parameters
        ----------
        scenario: The scenario or scenarios to search for, formatted as a string.
        scenario_label: The label for the scenario, singular or plural.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        prompt_scenario = scenario.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given scenario/experiment(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the scenarios/experiments to search for
experiments = [{scenario}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    experiment_id=experiments,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""
        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given scenario/experiment(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the scenarios/experiments to search for
experiments = [{scenario}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    experiment_id=experiments,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the datasets found to dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {scenario_label} {prompt_scenario} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {prompt_scenario} {scenario_label}?",
            f"I'm looking for datasets with {prompt_scenario} {scenario_label}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {scenario_label} {prompt_scenario}?",
            f"I need a python snippet using intake-esgf to get datasets that have  {scenario_label} {prompt_scenario}.",
        ]

        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Absolutely! Here is how we can find datasets that include {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {scenario_label} {prompt_scenario}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have  {scenario_label} {prompt_scenario}:",
        ]
        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Show me code to download all datasets that contain {scenario_label} {prompt_scenario} using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {prompt_scenario} {scenario_label}?",
            f"I'm looking to download datasets with {prompt_scenario} {scenario_label}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {scenario_label} {prompt_scenario}?",
            f"I need a python snippet using intake-esgf to download datasets that have  {scenario_label} {prompt_scenario}.",
        ]
        dl_responses = [
            f"Sure! Here is how we can download all datasets that contain {scenario_label} {prompt_scenario} using intake-esgf in python:",
            f"Absolutely! Here is how we can find and download datasets that include {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {scenario_label} {prompt_scenario}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have  {scenario_label} {prompt_scenario}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_dataset_list_by_source(
        self, source: str, source_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on source_id and returning as list of tuples representing instructions and output code.

        Parameters
        ----------
        source: The source_id to search for, formatted as a string.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        # The source name does not need quotes in the actual prompt so we save a different version for the prompt and code snippet
        prompt_source = source.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given source/model(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the sources to search for
sources = [{source}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    source_id=sources,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""
        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given source/model(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the sources to search for
sources = [{source}]

search_results = cat.search(
    source_id=sources,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the datasets found to dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {source_label} {prompt_source} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {source_label} {prompt_source}?",
            f"I'm looking for datasets with {source_label} {prompt_source}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {source_label} {prompt_source}?",
            f"I need a python snippet using intake-esgf to get datasets that have {source_label} {prompt_source}.",
        ]

        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {source_label} {prompt_source} using intake-esgf in python:",
            f"Absolutely! Here is how we can find datasets that include {source_label} {prompt_source} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {source_label} {prompt_source} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {source_label} {prompt_source}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {source_label} {prompt_source}:",
        ]
        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]
        dl_prompts = [
            f"Show me code to download all datasets that contain {source_label} {prompt_source} using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {source_label} {prompt_source}?",
            f"I'm looking to download datasets with {source_label} {prompt_source}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {source_label} {prompt_source}?",
            f"I need a python snippet using intake-esgf to download datasets that have {source_label} {prompt_source}.",
        ]
        dl_responses = [
            f"Sure! Here is how we can download all datasets that contain {source_label} {prompt_source} using intake-esgf in python:",
            f"Absolutely! Here is how we can find and download datasets that include {source_label} {prompt_source} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {source_label} {prompt_source} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {source_label} {prompt_source}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {source_label} {prompt_source}:",
        ]
        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_dataset_list_by_activity(
        self, activity: str, activity_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on activity_id and returning as list of tuples representing instructions and output code.

        Parameters
        ----------
        activity: The activity_id to search for, formatted as a string.
        activity_label: The label for the activity, singular or plural.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        prompt_activity = activity.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given activity/activities

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the activities to search for
activities = [{activity}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    activity_id=activities,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""
        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given activity/activities

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the activities to search for
activities = [{activity}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    activity_id=activities,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the datasets found to dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {activity_label} {prompt_activity} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {activity_label} {prompt_activity}?",
            f"I'm looking for datasets with {activity_label} {prompt_activity}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {activity_label} {prompt_activity}?",
            f"I need a python snippet using intake-esgf to get datasets that have {activity_label} {prompt_activity}.",
        ]

        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Absolutely! Here is how we can find datasets that include {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {activity_label} {prompt_activity}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {activity_label} {prompt_activity}:",
        ]

        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Search for all datasets that contain {activity_label} {prompt_activity} and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {activity_label} {prompt_activity}?",
            f"I'm looking to download datasets with {activity_label} {prompt_activity}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {activity_label} {prompt_activity}?",
            f"I need a python snippet using intake-esgf to download datasets that have {activity_label} {prompt_activity}.",
        ]

        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {activity_label} {prompt_activity}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {activity_label} {prompt_activity}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    def generate_model_list_by_activity(
        self, activity: str, activity_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for models based only on activity_id and returning as list of tuples representing instructions and output code.

        Parameters
        ----------
        activity: The activity_id to search for, formatted as a string.
        activity_label: The label for the activity, singular or plural.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        prompt_activity = activity.replace('"', "")
        code_template = f"""
```python
# Task: Generate list of all source/models for the given activity/activities

# import necessary libraries
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify the activities to search for
activities = [{activity}]

# search the catalog for datasets with the specified facets 
search_results = cat.search(
    activity_id=activities,
)

# get a list of unique models
models = sorted(search_results.df["source_id"].unique())

# print out our results
print(f"Models({{len(models)}} results):")
for i, model in enumerate(models):
    print(f"{{i+1}}. {{model}}")
```
"""
        prompts = [
            f"List all models that contain {activity_label} {prompt_activity} using intake-esgf in python.",
            f"Using intake-esgf, how do I find models that include {activity_label} {prompt_activity}?",
            f"I'm looking for models with {activity_label} {prompt_activity}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for models containing {activity_label} {prompt_activity}?",
            f"I need a python snippet using intake-esgf to get models that have {activity_label} {prompt_activity}.",
        ]

        responses = [
            f"Sure! Here is how we can list all models that contain {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Absolutely! Here is how we can find models that include {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Of course! Here is how we can search for models with {activity_label} {prompt_activity} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for models containing {activity_label} {prompt_activity}:",
            f"Sure! Here is a python snippet using intake-esgf to get models that have {activity_label} {prompt_activity}:",
        ]

        return [
            (prompt, f"{response}{code_template}")
            for prompt, response in zip(prompts, responses)
        ]

    def generate_dataset_list_by_realm(
        self, realm: str, realm_label: str
    ) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for datasets based only on realm and returning as list of tuples representing instructions and output code.

        Parameters
        ----------
        realm: The realm to search for, formatted as a string.
        realm_label: The label for the realm, singular or plural.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        prompt_realm = realm.replace('"', "")
        list_code_template = f"""
```python
# Task: Generate list of all datasets for the given realm(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the realms to search for
realms = [{realm}]

# search the catalog for datasets with the specified facets
search_results = cat.search(
    realm=realms,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
```
"""

        dl_code_template = f"""
```python
# Task: Search for and download all datasets for the given realm(s)

# import necessary libraries
from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify the realms to search for
realms = [{realm}]

# search the catalog
search_results = cat.search(
    realm=realms,
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)

# download the datasets found to dictionary
dsd = search_results.to_dataset_dict()
```
"""
        list_prompts = [
            f"List all datasets that contain {realm_label} {prompt_realm} using intake-esgf in python.",
            f"Using intake-esgf, how do I find datasets that include {realm_label} {prompt_realm}?",
            f"I'm looking for datasets with {realm_label} {prompt_realm}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to search for datasets containing {realm_label} {prompt_realm}?",
            f"I need a python snippet using intake-esgf to get datasets that have {realm_label} {prompt_realm}.",
        ]

        list_responses = [
            f"Sure! Here is how we can list all datasets that contain {realm_label} {prompt_realm} using intake-esgf in python:",
            f"Absolutely! Here is how we can find datasets that include {realm_label} {prompt_realm} using intake-esgf in python:",
            f"Of course! Here is how we can search for datasets with {realm_label} {prompt_realm} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to search for datasets containing {realm_label} {prompt_realm}:",
            f"Sure! Here is a python snippet using intake-esgf to get datasets that have {realm_label} {prompt_realm}:",
        ]

        list_snippets = [
            (prompt, f"{response}{list_code_template}")
            for prompt, response in zip(list_prompts, list_responses)
        ]

        dl_prompts = [
            f"Search for all datasets that contain {realm_label} {prompt_realm} and download them using intake-esgf in python.",
            f"Using intake-esgf, how do I download datasets that include {realm_label} {prompt_realm}?",
            f"I'm looking to download datasets with {realm_label} {prompt_realm}. Can you provide intake-esgf code in python?",
            f"Can you help me write intake-esgf code in python to download datasets containing {realm_label} {prompt_realm}?",
            f"I need a python snippet using intake-esgf to download datasets that have {realm_label} {prompt_realm}.",
        ]

        dl_responses = [
            f"Sure! Here is how we can search for and download all datasets that contain {realm_label} {prompt_realm} using intake-esgf in python:",
            f"Here is how we can find and download datasets that include {realm_label} {prompt_realm} using intake-esgf in python:",
            f"Of course! Here is how we can search for and download datasets with {realm_label} {prompt_realm} using intake-esgf in python:",
            f"Certainly! Here is how we can write intake-esgf code in python to download datasets containing {realm_label} {prompt_realm}:",
            f"Sure! Here is a python snippet using intake-esgf to download datasets that have {realm_label} {prompt_realm}:",
        ]

        dl_snippets = [
            (prompt, f"{response}{dl_code_template}")
            for prompt, response in zip(dl_prompts, dl_responses)
        ]

        return list_snippets + dl_snippets

    # TODO: Complete this function

    # def generate_dataset_list_by_gridlabel(self, gridlabel: str, gridlabel_label: str) -> list[tuple[str, str]]:
    #     """
    #     Generate intake code snippets that focus on searching for datasets based only on grid_label and returning as list of tuples representing instructions and output code.

    #     Parameters
    #     ----------
    #     gridlabel: The grid_label to search for, formatted as a string.
    #     gridlabel_label: The label for the grid_label, singular or plural.

    #     Returns
    #     -------
    #     list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
    #     """
    #     prompt_gridlabel = gridlabel.replace('"', '')
    #     code_template = f""""""
    #     return []

    # # TODO: Must add call to function in run function and create prompts and responses
    # def generate_dataset_list_by_source_variable(self, source: str, variable: str, source_label: str, variable_label: str) -> list[tuple[str, str]]:
    #     """
    #     Generate intake code snippets that focus on searching for datasets based on source_id and variables.

    #     Parameters
    #     ----------
    #     source: The source_id to search for, formatted as a string.
    #     variable: The variable or variables to search for, formatted as a string.
    #     source_label: The label for the source, singular or plural.
    #     variable_label: The label for the variable, singular or plural.

    #     Returns
    #     -------
    #     list[tuples(str)]: A list of tuples containing the instruction and output code snippet.
    #     """
    #     prompt_source = source.replace('"', '')
    #     prompt_variable = variable.replace('"', '')

    #     code_template = f""""""
    #     return []

    # Main Run Function
    def run(self):
        # Hold all snippets in this list
        all_snippets = []

        # Define sets of scenarios, variables, and frequencies to generate combinations
        institution_sets = [
            ["NCAR"],
            ["NCC"],
            ["MIROC"],
            ["DOE"],
            ["IPSL"],
            ["E3SM-Project"],
            ["E3SM-Project", "MOHC"],
            ["UCI", "MRI", "CAS"],
            ["NASA-GISS", "CCCma", "CSIRO"],
            ["NIMS-KMA", "CCCma", "CSIRO", "DOE", "MIROC", "IPSL"],
        ]
        source_sets = [
            ["CESM2"],
            ["CanESM5"],
            ["ACCESS-CM2"],
            ["E3SM-1-0"],
            ["MIROC6"],
            ["IPSL-CM6A-LR"],
            ["CESM2", "CanESM5"],
            ["CESM2", "CanESM5", "ACCESS-CM2"],
            ["NorCPM1", "CanESM5", "ACCESS-CM2", "E3SM-1-0", "MIROC6", "IPSL-CM6A-LR"],
        ]
        scenario_sets = [
            ["ssp126", "ssp245", "ssp370", "ssp585", "historical"],
            ["ssp126", "ssp245", "ssp370", "ssp585"],
            ["ssp245", "ssp370", "ssp585"],
            ["ssp245", "ssp585"],
            ["ssp126"],
            ["ssp245"],
            ["ssp585"],
            ["historical"],
        ]
        variable_sets = [
            ["gpp"],  # single
            ["tas"],  # single
            ["pr"],  # single
            ["pr", "tas"],  # pair
            ["rsds", "tas"],  # pair
            ["pr", "rsds"],  # pair
            ["gpp", "pr", "tas"],  # triple
            ["mrso", "rsds", "ua8"],  # triple (includes rare ua8)
            ["tos", "evspsbl"],  # pair (rare evspsbl)
            ["tas", "mrso"],  # pair
            ["gpp", "pr", "tas", "mrso"],  # quadruple
            ["psl", "ps", "sfcWind"],  # triple (includes rare sfcWind)
            ["gpp", "rsds", "evspsbl"],  # triple (mixed common + rare)
            ["tos", "evspsbl"],  # pair (ocean + rare)
            ["tas", "pr", "gpp", "rsds", "evspsbl"],  # quintuple
        ]
        freq_sets = [
            "hourly",  # sampled hourly #not the actual key word but will be mapped to 1hr in the code snippet
            "1hr",
            "3hr",  # 3 hour mean sample
            "6hr",  # 6 hour mean sample
            "day",
            "daily",  # daily mean samples
            "dec",
            "decadal",  # decadal mean samples
            "fx",  # fixed (time invariant) field
            "mon",
            "monthly",  # monthly mean samples
            "yr",
            "yearly",
            "annual",  # annual mean samples
            "yrPt",  # sampled yearly, at specified time point within the time period
        ]

        activity_sets = [
            ["CMIP"],
            ["DCPP"],
            ["PAMIP"],
            ["ScenarioMIP"],
            ["CMIP", "ScenarioMIP"],
            ["ScenarioMIP", "C4MIP"],
            ["C4MIP", "DAMIP", "VolMIP"],
            ["LUMIP", "AerChemMIP", "DCPP"],
            ["CMIP", "ScenarioMIP", "DAMIP", "C4MIP"],
            ["AerChemMIP", "DCPP", "VolMIP", "PAMIP", "DAMIP"],
        ]

        realm_sets = [
            ["atmos"],
            ["land"],
            ["ocean"],
            ["ocnBgchem"],
            ["seaIce", "ocean"],
            ["land", "landIce"],
            ["aerosol", "landIce", "atmosChem"],
            ["seaIce", "ocean", "ocnBgchem"],
            ["ocnBgchem", "atmos", "land", "landIce"],
            ["ocean", "atmos", "land", "seaIce", "ocnBgchem"],
        ]

        # Single variables
        # activity only
        for activity in activity_sets:
            activity_label = self.plural_label(activity, "activity", "activities")
            all_snippets += self.generate_dataset_list_by_activity(
                '"{0}"'.format('", "'.join(activity)), activity_label
            )
            all_snippets += self.generate_model_list_by_activity(
                '"{0}"'.format('", "'.join(activity)), activity_label
            )

        # realm only
        for realm in realm_sets:
            realm_label = self.plural_label(realm, "realm", "realms")
            all_snippets += self.generate_dataset_list_by_realm(
                '"{0}"'.format('", "'.join(realm)), realm_label
            )

        # freq only
        for freq in freq_sets:
            all_snippets += self.generate_dataset_list_by_freq(freq)

        # Institution only
        for institution in institution_sets:
            institution_label = self.plural_label(
                institution, "institution", "institutions"
            )
            all_snippets += self.generate_dataset_list_by_institution(
                '"{0}"'.format('", "'.join(institution)), institution_label
            )

        # Variable only
        for variable in variable_sets:
            # To see if we need plural or singular labels
            variable_label = self.plural_label(variable, "variable", "variables")
            all_snippets += self.generate_model_list_by_variable(
                '"{0}"'.format('", "'.join(variable)), variable_label
            )
            # generate dataset snippets
            all_snippets += self.generate_dataset_list_by_variable(
                '"{0}"'.format('", "'.join(variable)), variable_label
            )

        # Source ID
        # FIXME: - Still need to just move everything to the bottom but have implemented a cap for now --> uncomment with the rest
        temp_snippets = []
        sources = self.get_source_ids()
        for source in sources:
            source_id = f"{source}"
            temp_snippets += self.generate_experiment_list_by_source(source_id)
        all_snippets += self.sub_sampler(temp_snippets, SAMPLESIZE)

        # alternate source ID from list instead of pulling from CVs
        for source in source_sets:
            source_label = self.plural_label(source, "source", "sources")
            all_snippets += self.generate_dataset_list_by_source(
                '"{0}"'.format('", "'.join(source)), source_label
            )

        # Scenario/Experiment only
        for scenario in scenario_sets:
            scenario_label = self.plural_label(scenario, "scenario", "scenarios")
            all_snippets += self.generate_dataset_list_by_scenario(
                '"{0}"'.format('", "'.join(scenario)), scenario_label
            )

        # Scenario + Variable
        temp1 = []
        temp2 = []
        for scenario in scenario_sets:
            for variable in variable_sets:
                # To see if we need plural or singular labels
                scenario_label = self.plural_label(scenario, "scenario", "scenarios")
                variable_label = self.plural_label(variable, "variable", "variables")
                # call functions to generate snippets
                temp1 += self.generate_model_list_by_variable_scenario(
                    '"{0}"'.format('", "'.join(scenario)),
                    '"{0}"'.format('", "'.join(variable)),
                    scenario_label,
                    variable_label,
                )
                temp2 += self.generate_dataset_list_by_variable_scenario(
                    '"{0}"'.format('", "'.join(scenario)),
                    '"{0}"'.format('", "'.join(variable)),
                    scenario_label,
                    variable_label,
                )
        all_snippets += self.sub_sampler(temp1, SAMPLESIZE)
        all_snippets += self.sub_sampler(temp2, SAMPLESIZE)

        # Generating frequency bsed snippets
        # 1. Freq + variable:
        # generate model list by variable + freq, dataset list by variable + freq
        temp1, temp2 = [], []
        for freq in freq_sets:
            for variable in variable_sets:
                # To see if we need plural or singular labels
                variable_label = self.plural_label(variable, "variable", "variables")
                # call functions to generate snippets
                temp1 += self.generate_model_list_by_variable_freq(
                    '"{0}"'.format('", "'.join(variable)), variable_label, freq
                )
                temp2 += self.generate_dataset_list_by_variable_freq(
                    '"{0}"'.format('", "'.join(variable)), variable_label, freq
                )
        all_snippets += self.sub_sampler(temp1, 600)
        all_snippets += self.sub_sampler(temp2, 600)

        # 2. Freq + variable + institution:
        temp_snippets = []
        for freq in freq_sets:
            for variable in variable_sets:
                for institution in institution_sets:
                    # To see if we need plural or singular labels
                    variable_label = self.plural_label(
                        variable, "variable", "variables"
                    )
                    institution_label = self.plural_label(
                        institution, "institution", "institutions"
                    )
                    # call functions to generate snippets
                    temp_snippets += (
                        self.generate_dataset_list_by_variable_freq_institution(
                            '"{0}"'.format('", "'.join(variable)),
                            variable_label,
                            freq,
                            '"{0}"'.format('", "'.join(institution)),
                            institution_label,
                        )
                    )
        all_snippets += self.sub_sampler(temp_snippets, limit=SAMPLESIZE)

        # variable + scenario + source:
        temp_snippets = []
        for scenario in scenario_sets:
            for variable in variable_sets:
                for source in source_sets:
                    # To see if we need plural or singular labels
                    scenario_label = self.plural_label(
                        scenario, "scenario", "scenarios"
                    )
                    variable_label = self.plural_label(
                        variable, "variable", "variables"
                    )
                    source_label = self.plural_label(source, "source", "sources")
                    # call functions to generate snippets
                    temp_snippets += self.generate_dataset_by_variable_model_scenario(
                        '"{0}"'.format('", "'.join(variable)),
                        variable_label,
                        '"{0}"'.format('", "'.join(source)),
                        source_label,
                        '"{0}"'.format('", "'.join(scenario)),
                        scenario_label,
                    )
        all_snippets += self.sub_sampler(temp_snippets, limit=SAMPLESIZE)

        # List all category - Note: not practically useful but necessary for training
        # List of all variables
        all_snippets += self.generate_list_all_variables()
        # List of all models
        all_snippets += self.generate_list_all_models()
        print(f"Total snippets generated: {len(all_snippets)}")

        # convert to chatML
        self.snippets_to_chatML(all_snippets)

        # function to take chatML snippets and add multi-turn examples
        self.add_multiturn()

        # Write all snippets to file
        # self.snippets_to_file(all_snippets)
        self.snippets_to_file_ML()


################################################
# Main function to run the IntakeCodeGenerator #
################################################


def main():
    generator = IntakeCodeGenerator()
    generator.run()


if __name__ == "__main__":
    main()

# USED FOR TESTING ONLY
# Test prints
# count = 0
# for snippet in all_snippets:
#     print("Prompt:")
#     print(snippet[0])
#     print("\nCode Snippet:")
#     print(snippet[1])
#     print("\n" + "="*80 + "\n")
#     count += 1
# print(f"Total snippets generated: {count}")
