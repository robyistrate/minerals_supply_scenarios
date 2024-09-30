"""
data_collection.py contains the MetalSupplyScenarios class which creates the supply
scenarios based on the S&P dataset
"""

from pathlib import Path
import pandas as pd
import numpy as np
import re
import pycountry
import datetime

from . import DATA_DIR
from .data_collection import get_sp_dataset
from .utils import (
    import_yaml_file,
    update_df_from_dict
)

DATA_GAPS_PATH = DATA_DIR / "fill_data_gaps.yaml"
PRODUCTION_HARMONIZATION_DATA = DATA_DIR / "production_harmonization.yaml"

SUPPLY_SCENARIOS = DATA_DIR / "scenarios_by_development_stage.yaml"


class MetalSupplyScenarios:
    """
    Create metal supply scenarios and export as premise scenario data file

    :var commodity: name of the assessed commodity
    :var dataset_path: path to the Excel file containing the S&P dataset
    :var timeframe: tupple containing the first and last scenario's years (5-year timesteps will be applied)
    """

    def __init__(
            self,
            commodity: str,
            dataset_path: str,
            timeframe: tuple,
            **kwargs
    ):
        self.commodity = commodity
        self.dataset_path = dataset_path
        self.timeframe = timeframe
       
        self.scenarios = import_yaml_file(SUPPLY_SCENARIOS)
        
        # export directory is the current working / directory unless specified otherwise
        if kwargs.get("export_dir"):
            self.export_dir = Path(kwargs["export_dir"])
        else:
            self.export_dir = Path.cwd()

        # Define scope of scenarios
        if kwargs.get("specifics"):
            print("Considering only:", kwargs["specifics"])
            if "Activity Status" in kwargs["specifics"]:
                pattern_activity = '|'.join(map(re.escape, kwargs["specifics"]["Activity Status"]))

            if "Deposit Type" in kwargs["specifics"]:
                pattern_deposit = '|'.join(map(re.escape, kwargs["specifics"]["Deposit Type"]))

            if "Ore Minerals" in kwargs["specifics"]:
                pattern_ore = '|'.join(map(re.escape, kwargs["specifics"]["Ore Minerals"]))
        else:
            print("Considering all projects")
        
        if kwargs.get("exclude"):
            print("Excluding:", kwargs["exclude"])


        print("****************************************")
        print(f"Creating supply scenarios for {self.commodity.lower()}")
        
        # Import raw S&P dataset
        print("Importing raw dataset from S&P database...")
        self.sp_dataset_raw = get_sp_dataset(
            self.dataset_path,
            self.timeframe
            )
        
        # Dictionary with production columns and corresponding year
        self.production_years = self.get_production_years()
        self.production_time_steps = self.get_production_time_steps()

        # Applying strategies and creating updated dataset
        self.sp_dataset_updated = self.sp_dataset_raw.copy()

        # Filling data gaps in the raw dataset
        print("Applying strategy:", self.fill_data_gaps.__name__)
        self.fill_data_gaps()

        # Select subset of dataset based on specifics
        if kwargs.get("specifics"):
            self.sp_dataset_updated = self.sp_dataset_updated[(self.sp_dataset_updated["Deposit Type"].str.contains(pattern_deposit, na=False) if "Deposit Type" in kwargs["specifics"] else True) &
                                                              (self.sp_dataset_updated["Ore Minerals"].str.contains(pattern_ore, na=False) if "Ore Minerals" in kwargs["specifics"] else True) &
                                                              (self.sp_dataset_updated["Activity Status"].str.contains(pattern_activity, na=False) if "Activity Status" in kwargs["specifics"] else True) &
                                                              (self.sp_dataset_updated["Country"].isin(kwargs["specifics"]["Country"]) if "Country" in kwargs["specifics"] else True)]

        # Exclude accordingly:
        if kwargs.get("exclude"):
            for e in kwargs["exclude"]:
                self.sp_dataset_updated = self.sp_dataset_updated[~self.sp_dataset_updated[e].isin(kwargs["exclude"][e])]   

        # Estimating missing production forecasts
        print("Applying strategy:", self.estimate_future_production.__name__)
        self.estimate_future_production()

        # Create scenario dataset
        self.scenario_data = self.sp_dataset_updated.copy()
        print("Applying strategy:", self.create_scenarios_data.__name__) 
        self.scenario_data = self.create_scenarios_data()

        print("Applying strategy:", self.harmonize_production_data.__name__) 
        self.harmonize_production_data()        

        print("Exporting premise scenario data file")
        self.premise_scenario_data = self.export_to_premise_scenarios(self.scenario_data)

        print("*****************************")
        print("Processing report")
        self.processing_report = self.generate_processing_report()
        for key, value in self.processing_report.items():
            print(f"{key} : {value}")
        print("*****************************")


    def generate_processing_report(self):
        """
        Create processing report:
        """
        processing_report = {}

        total_number_projects = len(self.sp_dataset_updated)
        non_null_production_counts = self.sp_dataset_updated[self.production_time_steps.keys()].count()
        relative_counts = round((non_null_production_counts / total_number_projects) * 100,2)
        number_projects_scenarios = len(list(set(self.scenario_data["Project ID"])))
        discarded_projects_production = total_number_projects - number_projects_scenarios

        processing_report.update(
            {
                "Number projects in updated dataset": total_number_projects,
                'Number projects with production in updated dataset': non_null_production_counts,
                "Number projects in scenarios": number_projects_scenarios,
                "Number projects discarded due to lack of production": discarded_projects_production,

                "*******************************"

                'Share of all projects with production volume (%)': relative_counts,
                'Raw production volumes (kt/year)': self.sp_dataset_updated[self.production_time_steps.keys()].sum(),
                }
            )

        return processing_report


    def get_production_years(self):
        """
        Return a dictionary with the name of production columns and the corresponding year
        Selected timeframe may be different than available years in the dataset. Missing years
        are added
        """
        production_cols = [prod for prod in self.sp_dataset_raw.columns if "Production" in prod and "Capacity" not in prod and "Unit" not in prod]
        production_dict = {i: re.search(r'\d+', i).group() for i in production_cols}
        production_dict_sorted = dict(sorted(production_dict.items(), key=lambda item: item[1]))
        return production_dict_sorted


    def get_production_time_steps(self):
        """
        Return a dictionary with name of production columns and the corresponding year for
        the specified time steps.
        """
        steps = {key: value for key, value in self.production_years.items() if int(value) % self.timeframe[2] == 0}

        # Check if the first time step is equal to the first year of the timeframe
        first_year = list(steps.values())[0]

        if first_year != self.timeframe[0]:
            production_time_steps = {"Production " + str(self.timeframe[0]): str(self.timeframe[0])}
            production_time_steps.update(steps)
        else:
            production_time_steps = steps

        return production_time_steps


    def fill_data_gaps(self):
        """
        This function fills data gaps based on exogenous data sources
        """
        data_gaps = import_yaml_file(DATA_GAPS_PATH)

        if self.commodity in data_gaps:
            commodity_data_gaps = data_gaps[self.commodity]

            for index, value in commodity_data_gaps.items():

                if index in self.sp_dataset_updated.index:
                    for a in value:
                        col = list(a.keys())[0]
                        data = list(a.values())[0]      

                        self.sp_dataset_updated.at[index, col] = data


    def estimate_production_from_historical(self, production_dict):
        """
        If production forecast is available for the present but not for future, and
        the projected closure date of the project extends beyond the future year, 
        the current production values are assumed to the future
        """

        for project_index in production_dict:
            prev_value = None
            project_closure_year = self.sp_dataset_updated.loc[project_index]["Project Closure Year"]

            for prod_col in production_dict[project_index]:
                current_value = production_dict[project_index][prod_col]
                current_year = self.production_years[prod_col]

                if np.isnan(current_value):
                    if prev_value is not None:
                        if project_closure_year >= int(current_year):
                            production_dict[project_index][prod_col] = prev_value
                else:
                    prev_value = current_value

   
    def estimate_future_production(self):
        """
        This function applies a serie of strategies to estimate future production.

        :return data: in place modification of production capacities
        """

        production_columns = list(self.production_years.keys())
        production_dict = self.sp_dataset_updated[production_columns].T.to_dict()

        self.estimate_production_from_historical(production_dict)
        update_df_from_dict(self.sp_dataset_updated, production_dict)
      

    def create_scenarios_data(self):
        """
        Function to create supply scenarios based on the development stage of projects

        All projects for which current and future production
        capacities are not available are discarded
        """
        production_columns = list(self.production_time_steps.keys())

        # Drop projects without production data
        self.scenario_data.dropna(subset=production_columns, how='all', inplace=True)
        
        dfs = []
        for sc in self.scenarios:
            
            # Select projects if development stage within the scenario
            sc_data = self.scenario_data[self.scenario_data["Development Stage"].isin(self.scenarios[sc])].reset_index()
            sc_data[production_columns] = sc_data[production_columns].fillna(0)
            sc_data["Scenario"] = sc

            sc_data = sc_data[["Scenario", "Project ID", "Project Name", "Country", "Deposit Type", "Ore Minerals", "Product", "Production Unit"] + production_columns]

            sc_data = sc_data.rename(columns=self.production_time_steps)

            dfs.append(sc_data)

        data_all = pd.concat(dfs, ignore_index=True)

        # Ensure that the first year has same projects across scenarios
        projects_id_baseline = data_all[data_all["Scenario"] == "S&P-Baseline"]["Project ID"].values
            
        for index, row in data_all.iterrows():
            if row["Project ID"] not in projects_id_baseline:
                data_all.at[index, str(self.timeframe[0])] = 0
        
        return data_all  
    

    def harmonize_production_data(self):
        """
        This function harmonize production volumes to match the same product
        across projects
        """
        harmonize_data = import_yaml_file(PRODUCTION_HARMONIZATION_DATA)
        years = list(self.production_time_steps.values())

        if self.commodity in harmonize_data:
            com_harmonization_data = harmonize_data[self.commodity]

            for index, row in self.scenario_data.iterrows():
                if row["Deposit Type"] in com_harmonization_data:
                    if pd.isna(row["Product"]):
                        continue

                    list_products = [product.strip() for product in row["Product"].split(',')]
                    harmonized_product = com_harmonization_data[row["Deposit Type"]]["Product"]

                    if harmonized_product in list_products:
                        self.scenario_data.at[index, "Product"] = harmonized_product
                    else:
                        for other_com in com_harmonization_data[row["Deposit Type"]]['Conversions']:
                            if other_com in list_products:
                                self.scenario_data.at[index, "Product"] = harmonized_product
                                
                                factor = com_harmonization_data[row["Deposit Type"]]["Conversions"][other_com]
                                self.scenario_data.loc[index, years] *= factor


    def export_to_premise_scenarios(self, scenario_data):
        """
        Export the scenario data to premise scenario format
        """

        # Order of columns in the data scenario file
        years = list(self.production_time_steps.values())
        columns_order = ["scenario", "region", "variables", "unit"] + years

        premise_scenario_data = []
        for index, row in scenario_data.iterrows():

            # Find ISO code for country name
            if row["Country"] == "Dem. Rep. Congo":
                country_name = "Congo, The Democratic Republic of the"
            else:
                country_name = row["Country"]
            country_iso = pycountry.countries.lookup(country_name).alpha_2

            # Variable name: Production + Commodity name + Deposit type + Project name
            variable_name = "Production|" + str(self.commodity) + "|" + str(row["Deposit Type"]) + "|" + str(row["Project Name"])

            premise_scenario_data_fields = {}
            premise_scenario_data_fields.update(
                {
                    columns_order[0]: row["Scenario"],
                    columns_order[1]: country_iso,
                    columns_order[2]: variable_name,
                    columns_order[3]: row["Production Unit"],
                }
            )
            # Update information for production data
            premise_scenario_data_fields.update({year: row[year] for year in years})

            premise_scenario_data.append(premise_scenario_data_fields)
        
        premise_scenario_data = pd.DataFrame(premise_scenario_data)

        # Aggregate projects with the same name:
        agg_dict = {year: 'sum' for year in years}
        agg_dict.update({'region': 'first', 'unit': 'first'})
        premise_scenario_data = premise_scenario_data.groupby(['scenario', 'variables'], as_index=False).agg(agg_dict)

        # Add same variables across all scenarios:
        unique_variables = premise_scenario_data['variables'].unique()
        unique_scenarios = premise_scenario_data['scenario'].unique()
        variable_to_region_unit = premise_scenario_data[['variables', 'region', 'unit']].drop_duplicates().set_index('variables').to_dict('index')

        combinations = pd.MultiIndex.from_product([unique_scenarios, unique_variables], names=['scenario', 'variables']).to_frame(index=False)
        combinations['region'] = combinations['variables'].map(lambda var: variable_to_region_unit[var]['region'])
        combinations['unit'] = combinations['variables'].map(lambda var: variable_to_region_unit[var]['unit'])

        premise_scenario_data = pd.merge(combinations, premise_scenario_data, on=['scenario', 'variables', 'region', 'unit'], how='left').fillna(0)        
        for year in years:
            premise_scenario_data[str(year)] = premise_scenario_data[str(year)].astype(float)
            
        # Export scenario data file
        premise_scenario_data = premise_scenario_data[columns_order]
        filepath = (
            self.export_dir
            / f"{self.commodity.lower()}_scenario_data_{datetime.datetime.today().strftime('%d-%m-%Y')}.csv"
            )
        premise_scenario_data.to_csv(filepath, index=False)

        return premise_scenario_data


    def get_production_by_scenario(self):
        prod_sc = self.scenario_data[["Scenario"] + list(self.production_time_steps.values())].groupby("Scenario").sum().reindex(self.scenarios)
        return prod_sc
    
    def get_production_by_country(self):
        prod_country = self.scenario_data[["Scenario", "Country"] + list(self.production_time_steps.values())].groupby(["Scenario", "Country"]).sum().reindex(self.scenarios, level='Scenario')
        return prod_country