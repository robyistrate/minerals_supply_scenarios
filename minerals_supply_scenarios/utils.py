"""
This module contains functions of general utility 
which could be used in multiplace places.
"""

import pandas as pd
import yaml
from functools import reduce


def import_yaml_file(file_path):
    with open(file_path, "r") as stream:
        data = yaml.safe_load(stream)
    return data


def merge_dfs_by_index(dfs):
    """
    Function to merge a list of dataframes based on the index.
    Duplicated columns are removed

    :param dfs: list of dataframes to be merged
    :return: dataframe
    """
    merged_df = reduce(lambda left, right: pd.merge(left, right, left_index=True, right_index=True), dfs)

    # Drop duplicated columns
    columns_duplicated = [i for i in merged_df.columns if "_y" in i]
    merged_df.drop(columns=columns_duplicated, inplace=True)

    # Rename remaining columns
    merged_df.columns = merged_df.columns.str.replace("_x", '')
    
    # Ensure that duplicated columns are removed
    merged_df = merged_df.loc[:,~merged_df.columns.duplicated()].copy()

    return merged_df


def update_df_from_dict(df, update_dict):
    """
    Function to update df based on dictionary.
    """
    for index, updates in update_dict.items():
        for col, value in updates.items():
            df.at[index, col] = value


def add_cutoff_to_df(df, cutoff, NEW_ROW_NAME):
    df_cutoff = df[df.lt(cutoff).all(axis=1)].sum()
    df_cutoff = pd.DataFrame(df_cutoff, columns=[NEW_ROW_NAME]).T

    df = df[~(df < cutoff).all(axis=1)]
    df = pd.concat([df, df_cutoff])
    return df

def count_projects_by_attribute(dataset, ATTRIBUTE, cutoff, NEW_ROW_NAME):
    projects_by_attribute = dataset[ATTRIBUTE].value_counts().reset_index()
    projects_by_attribute.columns = [ATTRIBUTE, 'Number of projects']
    projects_by_attribute.set_index(ATTRIBUTE, inplace=True)
    
    if cutoff > 0:
        projects_by_attribute = add_cutoff_to_df(projects_by_attribute, cutoff, NEW_ROW_NAME)

    return projects_by_attribute


def group_production_by_attribute(dataset, ATTRIBUTE, PROD_COLS):
    production_by_attribute = dataset.groupby(ATTRIBUTE)[PROD_COLS].sum().div(1e3).reset_index().set_index(ATTRIBUTE)
    production_by_attribute = production_by_attribute[~(production_by_attribute == 0).all(axis=1)].round(0)
    return production_by_attribute


def group_production_by_two_attributes(dataset, ATTRIBUTE_1, ATTRIBUTE_2, values):
    production_by_two_attributes = dataset.pivot_table(index=ATTRIBUTE_1,
                                                       columns=ATTRIBUTE_2,
                                                       values=[values], aggfunc='sum', dropna=False)
    production_by_two_attributes = production_by_two_attributes.replace(0, np.nan).dropna(how='all').fillna(0)
    production_by_two_attributes = production_by_two_attributes.replace(0, np.nan).dropna(how='all', axis=1).fillna(0)
    return production_by_two_attributes