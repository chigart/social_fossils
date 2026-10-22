import logging
from typing import Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class AirflowAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._token: str | None = None

    def _fetch_token(self) -> str:
        response = requests.get(f"{self.base_url}/auth/token")
        response.raise_for_status()
        return response.json()["access_token"]

    def _authorized_request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        if self._token is None:
            self._token = self._fetch_token()

        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        response = self.session.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:
            # Token expired or invalid; refresh once and retry.
            self._token = self._fetch_token()
            headers["Authorization"] = f"Bearer {self._token}"
            response = self.session.request(method, url, headers=headers, **kwargs)

        return response

    def trigger_dag_run(self, dag_id: str, conf: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._authorized_request(
                "POST", f"/api/v2/dags/{dag_id}/dagRuns", json={"conf": conf}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to trigger DAG run for {dag_id}: {e}")
            raise

    def get_dag_run(self, dag_id: str, run_id: str) -> dict[str, Any]:
        try:
            response = self._authorized_request(
                "GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}"
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get DAG run {dag_id}/{run_id}: {e}")
            raise

    def get_dag_run_tasks(self, dag_id: str, run_id: str) -> list[dict[str, Any]]:
        try:
            response = self._authorized_request(
                "GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("task_instances", [])
        except requests.RequestException as e:
            logger.error(f"Failed to get task instances for {dag_id}/{run_id}: {e}")
            raise


def get_airflow_client() -> AirflowAPIClient:
    return AirflowAPIClient(settings.airflow_base_url)
