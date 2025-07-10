"""
Convenience script that prints all the records in the database.
"""
import sqlite3

# My run configuration is currently set to the project root, not src directory.
con = sqlite3.connect("usr/personal.db")
cur = con.cursor()

print("\n---import table---")
r = cur.execute("SELECT date_time, method, rowid FROM import")
print(r.fetchall())
print()
print("---daily_sets table---")
r = cur.execute("SELECT exercise, date, string, import_id, rowid FROM daily_sets")
print(r.fetchall())


cur.close()
con.close()