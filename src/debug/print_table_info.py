"""
Convenience script that prints table information.

Note: This script assumes the run configuration working directory is the project root.
"""
import sqlite3

def print_result_set(result_set):
    for result in result_set.fetchall():
        print(result)

con = sqlite3.connect("usr/personal.db")
cur = con.cursor()

r = cur.execute("SELECT  name FROM sqlite_master WHERE type='table'")
print("\n---Tables---")
print_result_set(r)

r = cur.execute("PRAGMA table_info(import)")
print("\n---import schema---")
print_result_set(r)

r = cur.execute("PRAGMA table_info(daily_sets)")
print("\n---daily_sets schema---")
print_result_set(r)
