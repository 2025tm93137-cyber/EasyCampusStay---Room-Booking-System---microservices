# Easy Stay optional browser interface

PHP API client on http://127.0.0.1:8180/. `public/index.php` renders the form, local CSS/JavaScript are in `public/assets`, and `public/api.php` offers fixed API-gateway actions through `bootstrap.php`. This folder has no database credentials or business database.

After setup, launch from the project root with `.\.venv\Scripts\python.exe ui\run.py`. The Windows launcher owns a separate XAMPP Apache instance and serves only public/. Dependencies are PHP extensions in composer.json.

The default **Book a room** tab contains the date, room choice, guest details, price and booking result. **Add sample rooms** explicitly creates new Inventory data; it never runs automatically on page load. Its defaults are five rooms at INR 2500 for the selected date. Change these defaults under **Service tests → Room setup**.

The **Service tests** tab contains health checks, payment/notification scenarios, request replay, changed-payload conflicts, workflow steps and raw API responses. Non-default scenarios are also shown as a warning beside Confirm booking. New bookings always receive a new key; Replay reuses the original payload and key. If the browser loses a booking response, Retry same booking reuses that key.

Sold-out or missing-date inventory disables new bookings in the UI. The Inventory database remains responsible for concurrency: displayed availability is only a snapshot, and a competing client can still take the last room before this request arrives.

HTTP 202 remains visible as the original POST response while polling reads the current booking state. Polling pauses after 60 further checks; Refresh this booking resumes checks. Notification retry is represented by the existing backend service and does not send a real email.

See `../EASY_STAY_START_HERE.txt` for Windows update instructions, a first booking walkthrough, the old-to-new control mapping and steps 23–25. The product name is Easy Stay; existing project folders, databases, API paths and launchers retain their configured names. The earlier CampusStay documents describe the same four-service implementation. Update the final report's display name consistently when preparing submission.
