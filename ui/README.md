# CampusStay optional browser console

PHP API client on http://127.0.0.1:8180/. `public/index.php` renders the form, local CSS/JavaScript are in `public/assets`, and `public/api.php` offers fixed API-gateway actions through `bootstrap.php`. This folder has no database credentials or business database.

After setup, launch from the project root with `.\.venv\Scripts\python.exe ui\run.py`. The Windows launcher owns a separate XAMPP Apache instance and serves only public/. Dependencies are PHP extensions in composer.json.
