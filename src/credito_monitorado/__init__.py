"""Sustentação e confiabilidade de modelos de risco de crédito."""

import os

# A demonstração usa rastreamento local explícito; não envia telemetria das bibliotecas.
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("ITERATIVE_DO_NOT_TRACK", "1")
os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
