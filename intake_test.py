from intake_esgf import ESGFCatalog
import pandas as pd

# Set Pandas display options for better readability
pd.set_option("display.max_rows", None)        # don’t overwhelm terminal
pd.set_option("display.max_columns", None)   # show all columns
pd.set_option("display.width", None)         # wider view

# initialize the catalog
cat = ESGFCatalog()

# define the criteria to search for
variables = ["tas", "ta"]

# search the catalog with specified constraints
search_results = cat.search(
    variable_id="tas",
    experiment_id="historical",
    source_id="CanESM5",
    table_id="Amon"
)

# print the resulting dataframe to show list of datasets found
print(search_results.df)
