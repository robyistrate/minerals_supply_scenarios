"""
data_collection.py contains functions to import raw datasets from different
sources and format them into the spcenarios format.

IMPORTANT: The flow could be improved if S&P database is accessed directly
"""

import os
import pandas as pd
import numpy as np

from . import DATA_DIR
from .utils import import_yaml_file

DATA_FORMATS_DIR = DATA_DIR / "metal_supply_data_format.yaml"

data_formats = import_yaml_file(DATA_FORMATS_DIR)


def get_sp_dataset(dataset_path, timeframe):
    """
    Import raw datasets from the S&P Capital IQ Pro database and
    convert into spcenarios data format.

    :param dataset_path: name of the Excel file containing the dataset
    :return: dataframe
    """
    SP_DATASETS_DIR = dataset_path
    df = pd.read_excel(SP_DATASETS_DIR, header=None).replace(0, np.nan)
    df.dropna(axis=0, how='all', inplace=True)
    df.reset_index(drop=True, inplace=True)

    sp_data_corresp = {i: data_formats[i]["S&P"] for i in data_formats if "S&P" in data_formats[i]}
    years_list = [f"{year}" for year in range(timeframe[0], timeframe[1]+1)]

    # Update column names based on the values in the first row if the column indicates a year
    updated_cols = []
    for col in df.columns:
        if df.at[1, col] in [y + "Y" for y in years_list]:
            updated_cols.append(f'{df.at[0, col]}_{df.at[1, col]}')
        else:
            updated_cols.append(df.at[0, col])

    df.columns = updated_cols
    df.drop(df.index[[0,1]], inplace=True)

    # Drop production columns for years not within the timeframe
    if sp_data_corresp["Production"] in df.columns:
       df.drop(columns=[sp_data_corresp["Production"]], inplace=True)

    # Check that the expected data columns are included
    # and label them according to spcenarios format
    for col in sp_data_corresp:

        # Not all production columns are mandatory:
        if col == "Production":
            for year in years_list:
                df_col_name = sp_data_corresp[col] + "_" + str(year) + "Y"
                prod_col_name = col + " " + str(year)

                df.rename(columns={df_col_name: prod_col_name}, inplace=True)
                if prod_col_name not in df.columns:
                    df[prod_col_name] = np.nan

                # Convert production to ktonne
                df[prod_col_name] /= 1000

        else:
            if sp_data_corresp[col] not in df.columns:
                raise ValueError(f"S&P dataset does not contain the {col}attribute")
            else:
                df.rename(columns={sp_data_corresp[col]: col}, inplace=True)

    # Convert production capacity to ktonne
    df["Production Capacity"] /= 1000
    df["Production Unit"] = "kt/year"

    df.set_index("Project ID", inplace=True)
    # Ensure the index remains as an integer
    df.index = df.index.astype(int)

    # Change order of columns
    production_cols = sorted([i for i in df.columns if any(year in i for year in years_list)])
    other_cols = [i for i in df.columns if i not in production_cols]
    df = df[other_cols + production_cols]
    
    return df