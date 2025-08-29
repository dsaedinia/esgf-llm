# esgf-llm

A Python project for preparing ESGF data and providing workflows for **LLM fine-tuning and evaluation**. The repository includes scripts to preprocess and collate ESGF datasets, convert them into formats suitable for LLM fine-tuning, and Jupyter notebooks for training and evaluating models.

## Repository Structure

esgf-llm/

- CMIP CSVs/ # Original CSV reference files for CMIP data
- CMIP JSONs/ # Standardized JSON reference files for CMIP6
- data/ # Preprocessed JSONL files for individual ESGF facets
- legacy data/ # Older datasets and reference materials
- LLM-notebooks/ # Jupyter notebooks for fine-tuning and model evaluation
- RAG docs/ # Documentation and ESGF references used for RAG pipeline
- combine_json.py # Script to collate all processed JSONL files into one
- convert_to_chatML.py # Convert combined dataset to ChatML format for LLM fine-tuning
- IntakeCodeGenerator.py # Script for generating intake-esgf code
- Various convert\*\*.py # Scripts for preprocessing CSVs/JSONs into JSONL
- pyproject.toml # Python project configuration (uv-managed)
- uv.lock # Locked dependencies for reproducible environments
- README.md # Project documentation
- Other markdown/text files # Glossary, variable lookups, and notes

## Features

- **Data preprocessing scripts**: Process CSV/JSON input files into instruction/output pairs in standardized JSONL format.
- **Data collation**: `combine_json.py` must be executed last to create a unified dataset (`all_data.jsonl`).
- **Format conversion**: `convert_to_chatML.py` converts the combined dataset into ChatML format for LLM fine-tuning workflows.
- **Fine-tuning notebooks**: Jupyter notebook in `LLM-notebooks/` demonstrate training LLMs on ESGF data.
- **Evaluation notebooks**: Jupyter notebook in `LLM-notebooks/` for evaluating LLM performance and verifying generated outputs.
- Legacy and reference files are preserved for reproducibility and reference.

## Getting Started

### Prerequisites

- Python 3.10+
- `uv` for dependency management (or use `pip` to install requirements manually)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/dsaedinia/esgf-llm.git
cd esgf-llm
```

2. Install Dependencies:

```bash
uv sync
```

## Usage

1. Execute preprocessing scripts as needed
2. Collate all files (required last):

```bash
python combine_json.py
```

3. Optional: Convert to ChatML for fine-tuning:

```bash
python convert_to_chatML.py
```

4. Run fine-tuning notebooks in LLM-notebooks/ to train LLMs on the ESGF dataset.

5. Run evaluation notebooks to assess the performance of your fine-tuned LLMs.

## Notes

- Always run combine_json.py last to ensure all processed files are collated correctly.

- convert_to_chatML.py is only necessary for workflows that require ChatML formatting.

- Legacy files are preserved but not required for standard preprocessing or fine-tuning workflows.

- Jupyter notebooks in LLM-notebooks/ are intended to run on external HPC systems and have not been tested using the dependencies of this directory.
