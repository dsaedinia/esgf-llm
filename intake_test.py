from intake_esgf import ESGFCatalog
import pandas as pd
# pd.set_option("display.max_rows", None)        # don't overwhelm terminal
# pd.set_option("display.max_columns", None)   # show all columns
# pd.set_option("display.width", None)         # wider view


cat = ESGFCatalog().search(data_node='esgf-node.ornl.gov', variable_id=['gpp', 'tas', 'pr'], experiment_id=["historical", "ssp585"], table_id=[
    'Amon', 'Lmon'], source_id=['CESM2', 'CanESM5', 'ACCESS-CM2'])

cat.remove_ensembles()
print(cat.df)
