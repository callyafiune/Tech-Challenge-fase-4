"""Relatório operacional local e agregado, sem dependências de rede."""

from __future__ import annotations

from html import escape
from pathlib import Path


def _number(value: object) -> str:
    if isinstance(value, bool):
        return "sim" if value else "não"
    return f"{value:.4f}" if isinstance(value, (float, int)) else "indisponível"


def _table(headers: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{escape(column)}</th>" for column in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (
        f"<div class='tabela'><table><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def render_summary(summary: dict, output_dir: Path) -> Path:
    """Apresenta os mesmos resultados consumidos pelos alertas e pelo MLflow."""
    scenarios = []
    distributions = []
    scenario_names = {
        "control": "Controle",
        "covariate": "Covariável",
        "concept": "Conceito simulado",
        "combined": "Combinado",
    }
    label_names = {
        "available_labels": "observados",
        "original_labels": "observados",
        "original": "observados",
        "counterfactual_simulated": "contrafactuais",
        "pending_labels": "pendentes",
    }
    for name, result in summary.get("scenarios", {}).items():
        metrics = result.get("performance") or {}
        drift = result["drift"]["summary"]
        relative = f"{name}/{result['evidently_html']}"
        scenarios.append(
            [
                escape(scenario_names.get(name, name)),
                result["rows"],
                escape(label_names.get(result["labels_status"], result["labels_status"])),
                _number(metrics.get("roc_auc")),
                _number(metrics.get("brier_score")),
                (
                    escape(", ".join(drift["drifted_features"]) or "nenhum")
                    if drift.get("status", "ok") == "ok"
                    else "amostra insuficiente"
                ),
                f"<a href='{escape(relative, quote=True)}'>Abrir Evidently</a>",
            ]
        )
        for feature, values in result["drift"]["features"].items():
            distributions.append(
                [
                    escape(name),
                    escape(feature),
                    escape(values["method"]),
                    _number(values.get("psi")),
                    _number(values.get("ks")),
                    _number(values.get("pvalue_adjusted")),
                    "pendente" if values["drift"] is None else "SIM" if values["drift"] else "não",
                ]
            )
    events = summary.get("events", [])
    failures = sum(e["status"] == "falha" and not e.get("expected_failure") for e in events)
    alerts = summary.get("alerts", [])
    cards = [
        ("Estado", summary.get("status", "em execução")),
        ("Registros na origem", summary.get("dataset", {}).get("rows", 0)),
        ("Alertas", len(alerts)),
        ("Falhas inesperadas", failures),
        ("Duração em segundos", _number(summary.get("duration_seconds"))),
        ("RSS máximo em MiB", _number(max((e["rss_mb"] for e in events), default=0))),
    ]
    cards_html = "".join(
        f"<div class='cartao'><span>{escape(str(label))}</span>"
        f"<strong>{escape(str(value))}</strong></div>"
        for label, value in cards
    )
    scenario_table = _table(
        ["Cenário", "Volume", "Rótulos", "AUROC", "Brier ↓", "Atributos em drift", "Relatório"],
        scenarios,
    )
    drift_table = _table(
        ["Cenário", "Atributo", "Regra", "PSI", "KS D", "p BH", "Drift"], distributions
    )
    event_table = _table(
        [
            "Etapa",
            "Status",
            "Falha prevista",
            "Linhas",
            "Segundos",
            "RSS MiB",
            "CPU s",
            "Disco GiB",
        ],
        [
            [
                escape(e["stage"]),
                escape(e["status"]),
                "sim" if e.get("expected_failure") else "não",
                e["rows"],
                _number(e["duration_seconds"]),
                _number(e["rss_mb"]),
                _number(e["cpu_seconds"]),
                _number(e["disk_free_gb"]),
            ]
            for e in events
        ],
    )
    alert_table = _table(
        ["Código", "Severidade", "Cenário", "Mensagem", "Observado", "Limiar", "Ação recomendada"],
        [
            [escape(a[key]) for key in ("code", "severity", "scenario", "message")]
            + [
                _number(a.get("observed")),
                _number(a.get("threshold")),
                escape(a["recommended_action"]),
            ]
            for a in alerts
        ],
    )
    concept = summary.get("concept", {})
    concept_html = _table(
        ["Indicador", "Resultado"],
        [
            ["Atributos idênticos", "sim" if concept.get("same_features") else "não"],
            ["Probabilidades idênticas", "sim" if concept.get("same_predictions") else "não"],
            ["Aumento pareado de Brier", _number(concept.get("brier_increase"))],
            ["Intervalo de confiança de 95%", escape(str(concept.get("ci95", "indisponível")))],
            [
                "Evidência de alteração condicional simulada",
                "sim" if concept.get("conditional_change_evidence") else "não",
            ],
        ],
    )
    tracking = summary.get("tracking", {})
    model = summary.get("model", {})
    partition_rows = [
        [escape(name), values["rows"]] for name, values in summary.get("partitions", {}).items()
    ]
    partition_html = _table(["Partição", "Linhas"], partition_rows)
    metrics_html = _table(
        ["Métrica", "Validação", "Referência independente"],
        [
            [escape(name), _number(value), _number(model.get("reference_metrics", {}).get(name))]
            for name, value in model.get("validation_metrics", {}).items()
            if not name.startswith("dummy_")
        ],
    )
    combined = summary.get("concept_combined", {})
    combined_html = (
        f"Aumento pareado de Brier: {_number(combined.get('brier_increase'))}; "
        f"IC95%: {escape(str(combined.get('ci95', 'indisponível')))}."
    )
    policy = summary.get("config", {}).get("monitoring", {})
    fairness_rows = []
    for dimension, groups in summary.get("fairness", {}).get("groups", {}).items():
        for group, values in groups.items():
            fairness_rows.append(
                [
                    escape(dimension),
                    escape(group),
                    values["rows"],
                    "suprimido" if values["status"] != "ok" else "disponível",
                    _number(values.get("approval_rate")),
                    _number(values.get("roc_auc")),
                ]
            )
    fairness_html = _table(
        ["Dimensão", "Grupo", "Volume", "Estado", "Aprovação técnica", "AUROC"], fairness_rows
    )
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confiabilidade de crédito — monitoramento</title>
<style>
:root{{color-scheme:light;font-family:system-ui,sans-serif;color:#172d36;background:#f2f5f4}}
body{{margin:0}} main{{max-width:1350px;margin:auto;padding:36px 28px}} h1{{font-size:2.2rem}}
.linha{{display:flex;gap:14px;flex-wrap:wrap}}
.cartao{{background:white;border-top:4px solid #176b61;
padding:18px;min-width:155px;flex:1;border-radius:8px}}.cartao span{{display:block;color:#52646a}}
.cartao strong{{font-size:1.6rem}}
section{{background:white;padding:22px;margin:24px 0;border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{text-align:left;padding:10px;
border-bottom:1px solid #d9e4e0}}th{{background:#eaf0ed}}
.tabela{{overflow-x:auto}}a{{color:#075d86}}
details{{margin:16px 0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.85rem}}
.aviso{{border-left:4px solid #bc7b1f;padding:14px;background:#fff4dd}}footer{{color:#52646a}}
</style></head><body><main>
<p>TECH CHALLENGE · FASE 4 · SUSTENTAÇÃO</p><h1>Confiabilidade de crédito</h1>
<p>Execução <code>{escape(summary["execution_id"])}</code> ·
UTC {escape(summary["started_at_utc"])}</p>
<div class="linha">{cards_html}</div>
<p class="aviso">Experimento acadêmico com intervenções sintéticas. Drift nas entradas é sinal
de investigação. Conceito depende de rótulos observados; nesta demonstração eles são contrafactuais.
O bloqueio do lote inválido é uma falha esperada do contrato, comprovando sua atuação.</p>
<section><h2>Modelo congelado e separação</h2>
{partition_html}<p>
Limiar fixo: {model.get("threshold", "—")}. Atributos excluídos: identificador, sexo, escolaridade,
estado civil e alvo. Modelo avaliado fora do treino.</p>
{metrics_html}</section>
<section><h2>Cenários monitorados</h2>{scenario_table}
<p>Os relatórios Evidently têm suas próprias decisões brutas. Os alertas desta visão usam a
política explícita: PSI ≥ {policy.get("psi_threshold", 0.2)} ou KS com
p ajustado BH ≤ {policy.get("ks_alpha", 0.05)} e D ≥ {policy.get("ks_min_effect", 0.1)}.
Scores e limiares efetivos também constam no JSON por atributo.</p>
<details><summary>Estatísticas por atributo</summary>{drift_table}</details></section>
<section><h2>Diagnóstico pareado de conceito</h2>{concept_html}
<p>Mesmo X, mesmas probabilidades e alteração condicional dos rótulos. Aumento de Brier
material com IC positivo é evidência de degradação neste experimento controlado.</p></section>
<section><h2>Combinado comparado ao covariável</h2><p>{combined_html}</p></section>
<section><h2>Auditoria descritiva de grupos</h2>{fairness_html}
<p>Taxas na referência independente. Aprovação técnica significa predição zero.
Idade permanece como preditor; excluir sexo não elimina proxies ou garante equidade.</p></section>
<section><h2>Alertas e resposta</h2>{alert_table}</section>
<section><h2>Saúde do pipeline e infraestrutura</h2>{event_table}
<p>RSS, CPU acumulada do processo e disco são amostras nos limites dos estágios;
não representam monitoramento contínuo do host nem pico exato de memória.</p></section>
<section><h2>Rastreabilidade</h2><p>Run pai MLflow:
<code>{escape(tracking.get("run_id", "pendente"))}</code>.</p>
<p><a href="resumo.json">Resumo JSON</a> · <a href="manifesto.json">Manifesto</a> ·
<a href="logs.jsonl">Logs estruturados</a> · <a href="alertas.json">Alertas JSON</a></p>
<p>MLflow local: use o comando do README para consultar o banco e os quatro runs filhos.</p>
</section><footer>Dados UCI 350 · CC BY 4.0 · Apenas indicadores agregados ·
Revisão humana antes de decisões reais.</footer>
</main></body></html>"""
    path = Path(output_dir) / "index.html"
    path.write_text(html, encoding="utf-8")
    return path
