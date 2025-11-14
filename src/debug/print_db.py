"""
Convenience script that prints all the records in the database.

Note: This script assumes the run configuration working directory is the project root.
"""
import sqlite3

con = sqlite3.connect("usr/personal.db")
cur = con.cursor()

print("\n---import table---")
r = cur.execute("SELECT date_time, file_hash, name, rowid FROM import")
print(r.fetchall())
print()
print("\n---daily_sets table---")
r = cur.execute("SELECT exercise, date, sets_string, import_id, rowid FROM daily_sets")
print(r.fetchall())


cur.close()
con.close()