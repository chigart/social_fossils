FROM apache/airflow:3.3.2-python3.12

USER airflow

USER root

COPY --chown=airflow:0 airflow /airflow
COPY --chown=airflow:0 backend/app /app/app
COPY --chown=airflow:0 backend/alembic /app/alembic
COPY --chown=airflow:0 backend/alembic.ini /app/alembic.ini
RUN chmod +x /airflow/entrypoint.sh

USER airflow
