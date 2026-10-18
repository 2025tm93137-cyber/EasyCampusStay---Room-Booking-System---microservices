# Reservation database files

`00_create_database.sql` creates this service database. `01_create_user.sql.example` is a password template for a new own-database runtime user. `schema.sql` creates local InnoDB tables/constraints; import it as the administrator with this database selected.

For consistent automatically generated credentials, use root `scripts/configure.py` then `scripts/init_databases.py`. The optional `--export-sql` writes a private phpMyAdmin import under ignored `.runtime/`. No tables or credentials are shared with another business service.
