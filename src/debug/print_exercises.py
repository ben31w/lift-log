"""
Convenience script that prints all the exercises in the database.

Note: This script assumes the run configuration working directory is the project root.
"""
from src.sql_utility import get_exercises

for e in get_exercises():
    print(e)
