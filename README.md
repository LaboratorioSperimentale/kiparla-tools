# KIParla Toolkit

This repository contains a set of tools to process, maintain and analyze files from the KIParla corpus

## How to install

1. Create a virtual environment
   `python3 -m venv .venv`

2. Activate it
   `source .venv/bin/activate`

3. Install the package
   `pip install git+https://github.com/LaboratorioSperimentale/kiparla-tools`

## Recipes

* `eaf2csv` - transform an eaf file or a series of eaf files into csv
* `csv2eaf` - transform a csv file or a series of csv files into eaf format
* `process` -
* `align` -
* `produce-conllu` -


# TODO
* parametrize get_stats() in order to produce stats even when annotators_data is not available
* substitute xxx
* conll2csv
* fix bug when switching tokens with _ after alignment

# ISSUES