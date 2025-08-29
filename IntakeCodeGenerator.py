import json
import os


class IntakeCodeGenerator:
    def __init__(self, output_path="data/intake_outputs.jsonl", input_path="CMIP JSONs/CMIP6_CV.json"):
        self.input_path = input_path
        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def get_source_ids(self):
        with open(self.input_path, "r") as f:
            data = json.load(f)
            source_ids = data['CV']['source_id'].keys()
        return list(source_ids)

    def plural_label(self, items, singular, plural):
        return singular if len(items) == 1 else plural

    def snippets_to_file(self, snippets: list[tuple[str, str]]):
        """
        Takes a list of tuples with instructions and outputs and writes them to a jsonl file

        Parameters:
        snippets (list of tuples): A list of tuples where each tuple contains an instruction and its corresponding output.
        """
        with open(self.output_path, 'a', encoding='utf-8') as jsonl_file:

            for instruction, output in snippets:
                entry = {
                    'Instruction': instruction,
                    'Input': "",
                    'Output': output
                }
                jsonl_file.write(json.dumps(entry) + "\n")

    def generate_list_all_variables(self) -> list[tuple[str, str]]:
        """ Generate intake code snippets that focus on listing all variables available in the catalog.
        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        code_template = f"""
```python
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# search the catalog for all variables
search_results = cat.search()

# get a list of unique variables
variables = sorted(search_results.df["variable_id"].unique())

# print out our results
print(f"Variables({{len(variables)}} results):")
for i, variable in enumerate(variables):
    print(f"{{i+1}}. {{variable}}")
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
            "Can you help me generate Python + intake-esgf code to browse every ESGF variable?"
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
            "Definitely! Here's how to browse every ESGF variable using intake-esgf in Python:"
        ]
        return [(prompt, f"{response}{code_template}") for prompt, response in zip(prompts, responses)]

    def generate_experiment_list_by_source(self, source_id: str) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on listing experiments from a specific source.

        Parameters
        ----------
        source_id (str): The source ID to search for experiments.

        Returns
        -------
        list[tuple[str, str]]: A list of tuples containing the instruction and output code snippet.
        """
        code_template = f"""
```python
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify the source ID to search for
sources = ["{source_id}"]

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
            f"Show me what experiments {source_id} offers using intake-esgf.",
            f"Using intake-esgf, how do I list all the experiments of {source_id}?",
            f"List all the experiments of {source_id} using intake-esgf.",
            f"List all the experiments {source_id} offers using intake-esgf."
        ]
        responses = [
            f"Sure! Here is a way we can generate a list of all the experiments {source_id} offers using python and intake-esgf:",
            f"Here is how we can show all the experiments {source_id} offers using python and intake-esgf:",
            f"Alright! Here is how we can list the experiments of {source_id} using python and intake-esgf:",
            f"Alright! Here is how we can list the experiments of {source_id} using python and intake-esgf:"
        ]

        return [(prompt, f"{response}{code_template}") for prompt, response in zip(prompts, responses)]

    def generate_model_list_by_variables_scenarios(self, scenario: str, variable: str, scenario_label: str, variable_label: str) -> list[tuple[str, str]]:
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
        prompt_scenario = scenario.replace('"', '')
        prompt_variable = variable.replace('"', '')
        code_template = f"""
```python
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify the scenarios and variables to search for
experiments = [{scenario}]
variables = [{variable}]

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
            f"I would like to generate some intake-esgf code. Can you show me how to find what models support {prompt_variable} across {prompt_scenario} {scenario_label}?"
        ]

        responses = [
            f"Sure, here is how we can name the models that have {prompt_scenario} {scenario_label} and {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Alright! Here is how we can find which models contain {prompt_variable} data under {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Sure! Here is how we can list the models that contain {variable_label} {prompt_variable} for {prompt_scenario} {scenario_label} using intake-esgf in python:",
            f"Ok! Here is how we can retrieve all models for {prompt_scenario} {scenario_label} and {variable_label} {prompt_variable} using intake-esgf in python:",
            f"Of course! Here is how we can find what models support {prompt_variable} across {prompt_scenario} {scenario_label} using intake-esgf in python:"
        ]

        return [(prompt, f"{response}{code_template}") for prompt, response in zip(prompts, responses)]

    def generate_model_list_by_variable(self, variable: str, variable_label: str) -> list[tuple[str, str]]:
        """
        Generate intake code snippets that focus on searching for models based only on variables and returning as list of tuples representing instructions and output code.
        Will use a combination of single and multiple variables for prompts to teach the model to generalize appropriately.

        Parameters
        ----------
        variable: The variable or variables to search for, formatted as a string.
        variable_label: The label for the variable, singular or plural.
        return: A list of tuples containing the instruction and output code snippet.
        """

        prompt_variable = variable.replace('"', '')
        code_template = f"""
```python
from intake_esgf import ESGFCatalog

# initialize the catalog
cat = ESGFCatalog()

# specify variables to search for
variables = [{variable}]

# search the catalog for models with the specified variable
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
            f"List models providing {variable_label} {prompt_variable} datasets using intake-esgf in Python.",
            f"Generate a list of models that feature {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"What's the best way to get models with {variable_label} {prompt_variable} in intake-esgf using Python?",
            f"I only need the model names that have {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"Display all models containing {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"Which models can I query for {variable_label} {prompt_variable} data using intake-esgf in Python?",
            f"Is there intake-esgf code in Python to show models with {variable_label} {prompt_variable}?",
            f"Find the set of all models that have {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"Could you provide a quick Python snippet using intake-esgf to find models for {variable_label} {prompt_variable}?",
            f"Identify every model with data for {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"How do I discover all models that support {variable_label} {prompt_variable} using intake-esgf in Python?",
            f"Search intake-esgf for models including {variable_label} {prompt_variable} using Python.",
            f"Give me the Python intake-esgf command to list models with {variable_label} {prompt_variable}.",
            f"Which models can I find that hold {variable_label} {prompt_variable} using intake-esgf in Python?",
            f"I'd like a Python code sample using intake-esgf to extract models containing {variable_label} {prompt_variable}.",
            f"How can I quickly list models with {variable_label} {prompt_variable} using intake-esgf in Python?",
            f"Retrieve model names that have {variable_label} {prompt_variable} data using intake-esgf in Python.",
            f"Can you write intake-esgf code in Python for listing models with {variable_label} {prompt_variable}?",
            f"Help me figure out which models include {variable_label} {prompt_variable} using intake-esgf in Python.",
            f"Show Python intake-esgf code to get all models for {variable_label} {prompt_variable}."
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
            f"Here's Python code to list models providing {variable_label} {prompt_variable} datasets using intake-esgf:",
            f"Here's how to generate a list of models that feature {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's one way to get models with {variable_label} {prompt_variable} in intake-esgf using Python:",
            f"Here's Python code to get just the model names that have {variable_label} {prompt_variable} using intake-esgf:",
            f"Here's code to display all models containing {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"You can query these models for {variable_label} {prompt_variable} data using intake-esgf in Python:",
            f"Yes! Here's intake-esgf code in Python to show models with {variable_label} {prompt_variable}:",
            f"Here's how to find the set of all models that have {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Sure! Here's a quick Python snippet using intake-esgf to find models for {variable_label} {prompt_variable}:",
            f"Here's Python code to identify every model with data for {variable_label} {prompt_variable} using intake-esgf:",
            f"Here's Python code to discover all models that support {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's how to search intake-esgf for models including {variable_label} {prompt_variable} using Python:",
            f"Here's the Python intake-esgf command to list models with {variable_label} {prompt_variable}:",
            f"You can find these models that hold {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's a Python code sample using intake-esgf to extract models containing {variable_label} {prompt_variable}:",
            f"Here's how to quickly list models with {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's Python code to retrieve model names that have {variable_label} {prompt_variable} data using intake-esgf:",
            f"Sure! Here's intake-esgf code in Python for listing models with {variable_label} {prompt_variable}:",
            f"Here's how to figure out which models include {variable_label} {prompt_variable} using intake-esgf in Python:",
            f"Here's Python intake-esgf code to get all models for {variable_label} {prompt_variable}:"
        ]

        return [(prompt, f"{response}{code_template}") for prompt, response in zip(prompts, responses)]

    def run(self):
        all_snippets = []
        scenario_sets = [
            ["ssp126", "ssp245", "ssp370", "ssp585", "historical"],
            ["ssp126", "ssp245", "ssp370", "ssp585"],
            ["ssp245", "ssp370", "ssp585"],
            ["ssp245", "ssp585"],
            ["ssp126"],
            ["ssp245"],
            ["ssp585"],
            ["historical"]
        ]

        variable_sets = [
            ["gpp"],                       # single
            ["tas"],                       # single
            ["pr"],                        # single
            ["pr", "tas"],                 # pair
            ["rsds", "tas"],               # pair
            ["pr", "rsds"],                # pair
            ["gpp", "pr", "tas"],          # triple
            ["mrso", "rsds", "ua8"],       # triple (includes rare ua8)
            ["tos", "evspsbl"],            # pair (rare evspsbl)
            ["tas", "mrso"],               # pair
            ["gpp", "pr", "tas", "mrso"],  # quadruple
            ["psl", "ps", "sfcWind"],      # triple (includes rare sfcWind)
            ["gpp", "rsds", "evspsbl"],    # triple (mixed common + rare)
            ["tos", "evspsbl"],            # pair (ocean + rare)
            ["tas", "pr", "gpp", "rsds", "evspsbl"]  # quintuple
        ]

        for variable in variable_sets:
            # To see if we need plural or singular labels
            variable_label = self.plural_label(
                variable, "variable", "variables")
            all_snippets += (self.generate_model_list_by_variable(
                '"{0}"'.format('", "'.join(variable)), variable_label))

        for scenario in scenario_sets:
            for variable in variable_sets:
                # To see if we need plural or singular labels
                scenario_label = self.plural_label(
                    scenario, "scenario", "scenarios")
                variable_label = self.plural_label(
                    variable, "variable", "variables")
                all_snippets += (self.generate_model_list_by_variables_scenarios(
                    '"{0}"'.format('", "'.join(scenario)), '"{0}"'.format('", "'.join(variable)), scenario_label, variable_label))

        # # Generate intake code snippets for each source ID
        sources = self.get_source_ids()
        for source in sources:
            source_id = f"{source}"
            all_snippets += (
                self.generate_experiment_list_by_source(source_id))

        print(all_snippets[0][1])
        # List of all variables
        all_snippets += (self.generate_list_all_variables())

        # Write all snippets to file
        self.snippets_to_file(all_snippets)
        print(f"Snippets written to data/intake_outputs.jsonl")
        print(f"Total snippets generated: {len(all_snippets)}")
##########################################################################################################################################
# Main function to run the IntakeCodeGenerator
##########################################################################################################################################


def main():
    generator = IntakeCodeGenerator()
    generator.run()


if __name__ == "__main__":
    main()
