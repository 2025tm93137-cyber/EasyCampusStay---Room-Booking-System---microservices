FROM python:3.12-slim-bookworm
WORKDIR /app
RUN pip install --no-cache-dir PyMySQL==1.1.2
COPY deploy/provision/init.py /app/init.py
COPY services/inventory/database/schema.sql /app/schemas/inventory.sql
COPY services/reservation/database/schema.sql /app/schemas/reservation.sql
COPY services/payment/database/schema.sql /app/schemas/payment.sql
COPY services/notification/database/schema.sql /app/schemas/notification.sql
CMD ["python", "init.py"]
