from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don't overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# specify variables, institutions and frequency to search for
variables = ["pr"]
institutions = ["NCAR"]
frequency = ["1hr"]

# search the catalog for models with the specified variable
search_results = cat.search(
    variable_id=variables,
    institution_id=institutions,
    frequency=frequency
)

# remove ensemble members to view first entry per dataset and reduce clutter
search_results.remove_ensembles()

# print the resulting dataframe to show list of datasets found
print(search_results.df)
