# DJroid Architecture

This document outlines the current state of the architecture for the djroid application.

## Objective
You are an expert in Python CLI Tooling Architecture. You are tasked with understanding the architecture of this project and updating this document when necessary as the architecture itself changes.

## Entrypoint
The djroid cli tool entry point begins with the `cli.py` file, located at `/Users/moth-man/Workspace/Python/djroid/djroid/cli/cli.py`. This file contains the click group and click command decorators used to describe command operations. All commands (tag/tag-schema/scan/crate) have service classes imported into this file. These service classes are instantiated within the command decorator block, and necessary functions of that service class are called to fulfill the requirements of the command.

# Tag-Schema
  - Tag Schema click decorator is created
  - Tag Schema service is instantiated
  - Tag Schema .setup_schema() function is called to begin tag schema creation logic

# Scan
  - A user will 

# Crate

## Technologies
- Python (main language)
- Postgresql (database)
- SQLAlchemy (python to database interaction library)
- Click (python cli library)
- Rich (console interaction & visualization library)
- LangGraph (llm workflow for prompt to playlist logic)