"""Centraliza eventos operacionais e alertas sem registrar linhas de clientes."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import psutil


def write_json(path: Path, value: object) -> None:
    """Persiste JSON legível, sem aceitar NaN como número válido."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


class Telemetry:
    """Registra estágios e recursos do processo; exceções nunca incluem payloads."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        self.alerts: list[dict] = []
        self.resources: list[dict] = []
        self.execution_id = self.output_dir.name

    def snapshot_resources(self) -> dict:
        """Amostra memória residente, CPU consumida e disco do diretório de saída."""
        process = psutil.Process()
        cpu = process.cpu_times()
        return {
            "rss_mb": round(process.memory_info().rss / 1024**2, 2),
            "cpu_seconds": round(cpu.user + cpu.system, 3),
            "disk_free_gb": round(
                psutil.disk_usage(str(self.output_dir.resolve())).free / 1024**3, 2
            ),
        }

    def _append(self, filename: str, event: dict) -> None:
        with (self.output_dir / filename).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")

    @contextmanager
    def stage(self, name: str, rows: int = 0, expected_failure: bool = False) -> Iterator[None]:
        """Mede uma etapa, inclusive quando ela falha, e preserva a exceção original."""
        start = time.perf_counter()
        event = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "stage": name,
            "rows": int(rows),
            "status": "sucesso",
            "execution_id": self.execution_id,
            "expected_failure": expected_failure,
        }
        try:
            yield
        except BaseException as error:
            event["status"] = "falha"
            event["error_type"] = type(error).__name__
            raise
        finally:
            event["duration_seconds"] = round(time.perf_counter() - start, 6)
            event.update(self.snapshot_resources())
            self.events.append(event)
            self.resources.append(
                {key: event[key] for key in ("rss_mb", "cpu_seconds", "disk_free_gb")}
            )
            self._append("logs.jsonl", event)

    def alert(
        self,
        code: str,
        severity: str,
        scenario: str,
        message: str,
        observed: float | None = None,
        threshold: float | None = None,
        recommended_action: str = "Investigar o alerta antes de alterar o modelo.",
    ) -> None:
        """Publica alerta agregado; os argumentos devem vir de mensagens controladas."""
        event = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "code": code,
            "severity": severity,
            "scenario": scenario,
            "message": message,
            "execution_id": self.execution_id,
            "observed": observed,
            "threshold": threshold,
            "recommended_action": recommended_action,
        }
        self.alerts.append(event)
        write_json(self.output_dir / "alertas.json", self.alerts)

    def check_health(self, max_stage_seconds: float, max_rss_mb: float) -> None:
        """Converte limites operacionais em alertas, sem alegar SLA de produção."""
        for event in self.events:
            if event["duration_seconds"] > max_stage_seconds:
                self.alert(
                    "LATENCIA",
                    "aviso",
                    event["stage"],
                    "Duração acima do limite configurado.",
                    observed=event["duration_seconds"],
                    threshold=max_stage_seconds,
                )
        if self.resources and max(row["rss_mb"] for row in self.resources) > max_rss_mb:
            self.alert(
                "MEMORIA",
                "aviso",
                "infraestrutura",
                "Memória acima do limite configurado.",
                observed=max(row["rss_mb"] for row in self.resources),
                threshold=max_rss_mb,
            )
        if self.resources and min(row["disk_free_gb"] for row in self.resources) < 1:
            self.alert(
                "DISCO",
                "critico",
                "infraestrutura",
                "Espaço livre abaixo de 1 GiB.",
                observed=min(row["disk_free_gb"] for row in self.resources),
                threshold=1,
            )
