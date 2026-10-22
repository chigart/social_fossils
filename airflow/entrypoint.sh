#!/bin/bash
set -eu
if [ -r /run/airflow-secrets/jwt_secret ]; then
  export AIRFLOW__API_AUTH__JWT_SECRET="$(cat /run/airflow-secrets/jwt_secret)"
fi
exec airflow "$@"
