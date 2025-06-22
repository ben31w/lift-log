This README file exists to 
1. provide a placeholder so the decompressed directory can be commited to git
   (empty directories can't be committed)
2. explain the decompressed directory

The decompressed directory stores decompressed HTML files.

When you import sets via HTML, the HTML file content is compressed 
into a BLOB before it's stored in SQLite. 

When you view the file you imported, the compressed content is decompressed.
The original HTML file is essentially re-created and placed here.

This directory provides a place that Firefox/other web browsers can see.
The `/tmp` directory isn't visible to some web browsers.

This directory will contain different HTML files per user, so we don't commit
any HTML files in this directory.

