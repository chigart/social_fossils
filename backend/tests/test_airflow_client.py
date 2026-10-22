from datetime import datetime, timezone
from unittest.mock import Mock

from app.airflow_client import AirflowAPIClient


def test_trigger_dag_run_sends_required_airflow_3_fields():
    client = AirflowAPIClient("http://airflow.test/")
    response = Mock()
    response.json.return_value = {"dag_run_id": "upload_job_12"}
    client._authorized_request = Mock(return_value=response)
    logical_date = datetime(2026, 10, 22, 12, 0)

    result = client.trigger_dag_run(
        "telegram_import",
        {"job_id": 12},
        dag_run_id="upload_job_12",
        logical_date=logical_date,
    )

    assert result == {"dag_run_id": "upload_job_12"}
    client._authorized_request.assert_called_once_with(
        "POST",
        "/api/v2/dags/telegram_import/dagRuns",
        json={
            "dag_run_id": "upload_job_12",
            "logical_date": "2026-10-22T12:00:00+00:00",
            "conf": {"job_id": 12},
        },
    )
    response.raise_for_status.assert_called_once_with()


def test_trigger_dag_run_preserves_timezone_aware_logical_date():
    client = AirflowAPIClient("http://airflow.test")
    response = Mock()
    response.json.return_value = {"dag_run_id": "upload_job_12"}
    client._authorized_request = Mock(return_value=response)
    logical_date = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)

    client.trigger_dag_run(
        "telegram_import",
        {"job_id": 12},
        dag_run_id="upload_job_12",
        logical_date=logical_date,
    )

    assert client._authorized_request.call_args.kwargs["json"]["logical_date"] == (
        "2026-10-22T12:00:00+00:00"
    )
