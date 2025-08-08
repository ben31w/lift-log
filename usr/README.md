# `usr` Directory
This directory contains user-specific data:
- SQLite file (`personal.db`)
- Decompressed HTML files
- Exercise Aliases file (`aliases.txt`)

Only this file is commited to Git. 
Everything else in this directory is user-specific and ignored.

***Note, the aliases file actually is committed for now.
This may change in the future.

## About the SQLite file
The name `personal.db` was chosen arbitrarily

## About the decompressed HTML files
When you import sets via HTML, the HTML file content is compressed 
into a BLOB before it's stored in SQLite. 

When you view the file you imported, the compressed content is decompressed.
The original HTML file is essentially re-created and placed here.

This directory provides a place that Firefox/other web browsers can see.
The `/tmp` directory isn't visible to some web browsers.
