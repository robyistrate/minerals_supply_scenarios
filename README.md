# ``minerals_supply_scenarios``

## Developing bottom-up scenarios for critical minerals supply based on market forecasts

Python library designed to assist in the development of scenarios for minerals supply based on asset-level data. The tool streamlines the process of importing, processing, and analyzing mining asset data from the S&P Capital IQ Pro database. By default, supply scenarios are created considering the development stage of the mining projects, thus reflecting different levels of production expansion.

The tool provides functionalities to export the resulting scenarios in a format that can be used directly with the [premise tool](https://github.com/polca/premise) for conducting prospective life cycle assessments.

Scenarios
----------------------------

By default, the following three supply scenarios are created considering projects' development stage:

| Scenario         | Narrative                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Plausibility                                   |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| **Baseline**     | This scenario describes a future where only projects already operational continue to operate throughout the time horizon. It includes projects at the stages of operating, limited production, preproduction, expansion, and satellite. Therefore, any production increase in this scenario results solely from the expansion at existing sites. This scenario takes a conservative view, acknowledging that the surging demand for raw materials makes it unlikely that no new projects will be launched in the near term. However, this scenario serves as a benchmark, allowing for exploring the impact of production expansion through new projects. | This scenario is considered plausible as it represents a conservative approach that aligns with existing operations and expansions.           |
| **Ambitious**    | This scenario envisions a future where projects currently in advanced stages of development ultimately become operational. In addition to the stages included in the Baseline scenario, it also incorporates projects at the stages of construction started, construction planned, feasibility complete, and commissioning.                                                                                                                | This scenario is considered plausible due to the advanced development stages of the included projects; however, uncertainties persist, as multiple factors could hinder achieving the production volumes projected by companies. |
| **Very Ambitious** | This scenario envisions a future where all projects, regardless of their current development stage, become operational according to the production timeline projected by companies.                                                                                                                                                                                                                                   | This scenario is plausible to a limited extent, as its materialization would require highly favorable conditions. |

Features
----------------------------

- **Data import from S&P databases**: Import raw datasets from S&P Capital IQ Pro database and clean, transform, and fill data gaps.
- **Scenario development**: Create and analyze multiple mineral supply scenarios using attributes of the imported dataset. By default, creates scenarios based on the development stage of the mining projects.
- **Export for use in prospective life cycle assessment**: Provides functionalities to export the resulting scenario data in a format that can be used directly with the [premise tool](https://github.com/polca/premise) for creating prospective life cycle inventory databases.

Installation
----------------------------


How to use
----------------------------
To use the tool, the raw dataset needs to be downloaded from the S&P database. When exporting the dataset, the following attributes must be included: *Primary comodity, Production forms, Country / Region Name, Development stage, Activity Status, List of Commodities, Mine type 1, Geologic Ore Body Type, Ore Minerals, Projected Start Up Year, Projected Closure Year, Production capacity - tonne, Commodity Production - tonne [for selected years]*

Copy the downloaded dataset into the [examples folder](https://github.com/robyistrate/minerals_supply_scenarios/tree/main/examples) and run the [example Jupyter notebook](https://github.com/robyistrate/minerals_supply_scenarios/blob/main/examples/example.ipynb)