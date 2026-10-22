import logging
from typing import Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class AirflowAPIClient:
    def __init__(self, base_url: str, username: str = "admin", password: str = "admin"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)

    def trigger_dag_run(self, dag_id: str, conf: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"
        payload = {
            "conf": conf,
        }

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to trigger DAG run for {dag_id}: {e}")
            raise

    def get_dag_run(self, dag_id: str, run_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get DAG run {dag_id}/{run_id}: {e}")
            raise

    def get_dag_run_tasks(self, dag_id: str, run_id: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("task_instances", [])
        except requests.RequestException as e:
            logger.error(f"Failed to get task instances for {dag_id}/{run_id}: {e}")
            raise


def get_airflow_client() -> AirflowAPIClient:
    return AirflowAPIClient(settings.airflow_base_url)
