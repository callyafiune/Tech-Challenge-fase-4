"""Verifica o Docker em sequência e registra evidências sem linhas de clientes."""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from credito_monitorado.publicacao import salvar_saida_publica

ROOT = Path(__file__).resolve().parents[1]

# O código é enviado pela entrada padrão; a sonda não integra a imagem final.
SONDA = """
import hashlib, importlib.util, json, os, shutil, sqlite3
from pathlib import Path
from urllib.parse import urlsplit
import re
assert os.getuid() == 10001
assert not any(importlib.util.find_spec(n) for n in ('pytest', 'ruff'))
assert shutil.which('uv') is None
assert os.environ['MLFLOW_DISABLE_TELEMETRY'] == 'true'
if os.environ.get('SONDA_IMAGEM') == '1':
    esperados = {'.gitattributes', '.python-version', 'artifacts', 'data',
                 'params.yaml', 'pyproject.toml', 'src', 'uv.lock'}
    assert set(os.listdir('/app')) == esperados
    assert not list(Path('/app/data').iterdir())
    assert not list(Path('/app/artifacts').iterdir())
    print(json.dumps({'uid': os.getuid(), 'diretorios_de_dados_vazios': True,
                      'arquivos_app': sorted(esperados), 'sem_dependencias_dev': True}))
else:
    resultados = []
    for path in sorted(Path('/app/artifacts').glob('*/resumo.json')):
        s = json.loads(path.read_text())
        if os.environ.get('SONDA_FALHA') == '1':
            assert s['status'] == 'falha'
            assert s['failure']['failed_stage'] == 'aquisicao'
            resultados.append({'execucao': s['execution_id'], 'falha': s['failure']})
            continue
        assert s['status'] == 'sucesso' and s['dataset']['rows'] == 30000
        assert s['contracts']['status'] == 'blocked_as_expected'
        assert s['model']['roundtrip_predictions_equal']
        assert set(s['scenarios']) == {'control', 'covariate', 'concept', 'combined'}
        assert s['tracking']['status'] == 'completed'
        db = sqlite3.connect('file:/app/artifacts/mlflow.db?mode=ro', uri=True)
        pai = s['tracking']['run_id']
        estado = db.execute('select status from runs where run_uuid=?', (pai,)).fetchone()
        assert estado[0] == 'FINISHED'
        filhos = db.execute(
            "select r.run_uuid,r.status from runs r join tags t on r.run_uuid=t.run_uuid "
            "where t.key='mlflow.parentRunId' and t.value=?", (pai,)).fetchall()
        assert len(filhos) == 4 and all(f[1] == 'FINISHED' for f in filhos)
        db.close()
        cenarios = {}
        for nome, c in s['scenarios'].items():
            assert c['rows'] == 2500
            assert (path.parent / nome / c['evidently_html']).is_file()
            assert (path.parent / nome / 'evidently.json').is_file()
            esperados = [] if nome in ('control', 'concept') else ['limit_bal', 'pay_0']
            assert sorted(c['drift']['summary']['drifted_features']) == sorted(esperados)
            cenarios[nome] = {'linhas': c['rows'], 'metricas': c['performance']}
        html = (path.parent / 'index.html').read_text()
        for link in re.findall(r'href=["\\\']([^"\\\']+)["\\\']', html):
            if not urlsplit(link).scheme and not link.startswith('#'):
                assert (path.parent / urlsplit(link).path).is_file(), link
        resultados.append({'execucao': s['execution_id'], 'status': s['status'],
            'duracao_segundos': s['duration_seconds'], 'eventos': len(s['events']),
            'alertas': len(s['alerts']), 'cenarios': cenarios, 'mlflow_pai': pai,
            'mlflow_filhos': filhos, 'dataset_sha256': s['dataset']['sha256'],
            'modelo_sha256': s['model']['sha256'],
            'source_sha256': s['source']['source_sha256']})
    esperado = 1 if os.environ.get('SONDA_FALHA') == '1' else 2
    assert len(resultados) == esperado
    if esperado == 2:
        assert resultados[0]['cenarios'] == resultados[1]['cenarios']
    print(json.dumps(resultados))
"""


def json_da_sonda(saida: str):
    """Separa o JSON da sonda dos avisos de criação e remoção do Compose."""
    for linha in reversed(saida.splitlines()):
        try:
            valor = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if isinstance(valor, (dict, list)):
            return valor
    raise ValueError("A sonda não retornou JSON válido; consulte o log literal.")


def main() -> None:
    """Usa projetos novos por verificação, preservando volumes para inspeção."""
    projeto = f"credito-verificacao-{datetime.now(UTC):%Y%m%d%H%M%S}"
    evidencia = {"inicio_utc": datetime.now(UTC).isoformat(), "projeto": projeto, "comandos": []}
    destino = ROOT / "docs/verificacao_docker.json"
    contador = 0

    def executar(nome, comando, entrada=None, esperado=0, binario=False):
        nonlocal contador
        contador += 1
        inicio = datetime.now(UTC).isoformat()
        resultado = subprocess.run(
            comando,
            cwd=ROOT,
            input=entrada.encode("utf-8") if entrada is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if not binario else subprocess.PIPE,
            timeout=900,
        )
        if binario:
            conteudo = json.dumps(
                {"bytes_stdout": len(resultado.stdout), "codigo_saida": resultado.returncode}
            )
        else:
            conteudo = resultado.stdout.decode("utf-8", errors="surrogateescape")
        log = ROOT / f"docs/validacao/docker-sequencial-{contador:02d}-{nome}.log"
        salvar_saida_publica(conteudo.encode("utf-8", errors="surrogateescape"), log, ROOT)
        registro = {
            "etapa": nome,
            "comando": comando,
            "inicio_utc": inicio,
            "fim_utc": datetime.now(UTC).isoformat(),
            "codigo_saida": resultado.returncode,
            "saida_esperada": esperado,
            "log": log.relative_to(ROOT / "docs").as_posix(),
            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        }
        if entrada is not None:
            registro["entrada_sha256"] = hashlib.sha256(entrada.encode()).hexdigest()
        evidencia["comandos"].append(registro)
        destino.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n", "utf-8")
        print(f"{nome}: saída {resultado.returncode}", flush=True)
        if resultado.returncode != esperado:
            raise RuntimeError(f"Código de saída inesperado em {nome}; consulte {log.name}.")
        return resultado.stdout if binario else conteudo

    def compose(nome=projeto, offline=False):
        argumentos = ["docker", "compose", "--ansi", "never", "-p", nome, "-f", "compose.yaml"]
        return argumentos + (["-f", "compose.sem-rede.yaml"] if offline else [])

    executar("config", compose() + ["config", "--quiet"])
    executar("config-sem-rede", compose(offline=True) + ["config", "--quiet"])
    executar("build-check", ["docker", "build", "--check", "."])
    build = executar("build", compose() + ["--progress", "plain", "build", "pipeline"])
    imagem = json.loads(
        executar("imagem-inicial", ["docker", "image", "inspect", "credito-monitorado:local"])
    )[0]
    assert imagem["Id"] in build
    evidencia["imagem"] = {
        "id": imagem["Id"],
        "conteudo_bytes": imagem["Size"],
        "arquitetura": imagem["Architecture"],
        "sistema": imagem["Os"],
    }
    evidencia["bases_build"] = sorted(
        set(
            re.findall(
                r"(?:docker.io/library/python|ghcr.io/astral-sh/uv|docker.io/docker/dockerfile)"
                r":[^\s]+@sha256:[0-9a-f]{64}",
                build,
            )
        )
    )
    assert len(evidencia["bases_build"]) == 3
    evidencia["tamanho_docker"] = json.loads(
        executar(
            "tamanho",
            ["docker", "image", "ls", "--format", "{{json .}}", "credito-monitorado:local"],
        )
    )
    evidencia["imagem_sem_volumes"] = json_da_sonda(
        executar(
            "imagem-sem-volumes",
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "-e",
                "SONDA_IMAGEM=1",
                "--entrypoint",
                "python",
                "-i",
                "credito-monitorado:local",
                "-",
            ],
            SONDA,
        )
    )
    parametros = ["up", "--no-build", "--abort-on-container-exit", "--exit-code-from", "pipeline"]
    negativo = f"{projeto}-sem-cache"
    executar("falha-sem-cache", compose(negativo, True) + parametros, esperado=1)
    evidencia["falha_esperada"] = json_da_sonda(
        executar(
            "diagnostico-falha",
            compose(negativo, True)
            + [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                "SONDA_FALHA=1",
                "--entrypoint",
                "python",
                "pipeline",
                "-",
            ],
            SONDA,
        )
    )
    executar("com-rede", compose() + parametros)
    executar("sem-rede", compose(offline=True) + parametros)
    evidencia["execucoes"] = json_da_sonda(
        executar(
            "sonda",
            compose()
            + ["run", "--rm", "--no-deps", "-T", "--entrypoint", "python", "pipeline", "-"],
            SONDA,
        )
    )
    container = f"{projeto}-pipeline-1"
    estado = json.loads(executar("conteiner", ["docker", "inspect", container]))[0]
    assert estado["Image"] == imagem["Id"]
    assert estado["HostConfig"]["ReadonlyRootfs"]
    assert estado["HostConfig"]["NetworkMode"] == "none"
    assert estado["State"]["ExitCode"] == 0
    evidencia["imagem_executada"] = estado["Image"]
    exportado = executar(
        "exportacao", compose() + ["cp", "pipeline:/app/artifacts/.", "-"], binario=True
    )
    with tarfile.open(fileobj=io.BytesIO(exportado)) as arquivo:
        membros = {m.name.removeprefix("./"): m for m in arquivo.getmembers() if m.isfile()}
        verificados = 0
        for execucao in evidencia["execucoes"]:
            prefixo = execucao["execucao"] + "/"
            manifesto = json.load(arquivo.extractfile(membros[prefixo + "manifesto.json"]))
            for nome, digest in manifesto["artifacts_sha256"].items():
                conteudo = arquivo.extractfile(membros[prefixo + nome]).read()
                assert hashlib.sha256(conteudo).hexdigest() == digest
                verificados += 1
    evidencia["exportacao"] = {"arquivos_com_hash_verificado": verificados}
    ui = f"{projeto}-ui"
    executar(
        "iniciar-ui",
        compose()
        + [
            "run",
            "--rm",
            "-d",
            "--name",
            ui,
            "-p",
            "127.0.0.1:5000:5000",
            "--entrypoint",
            "mlflow",
            "pipeline",
            "ui",
            "--backend-store-uri",
            "sqlite:////app/artifacts/mlflow.db",
            "--host",
            "0.0.0.0",
            "--port",
            "5000",
        ],
    )
    try:
        inicio_http = datetime.now(UTC).isoformat()
        consultar = build_opener(ProxyHandler({}))
        limite = time.monotonic() + 120
        while True:
            try:
                with consultar.open("http://127.0.0.1:5000/health", timeout=5) as resposta:
                    assert resposta.status == 200
                break
            except (URLError, OSError):
                if time.monotonic() > limite:
                    raise RuntimeError("A UI não ficou disponível no prazo.") from None
                time.sleep(1)
        consulta = Request(
            "http://127.0.0.1:5000/api/2.0/mlflow/runs/search",
            data=json.dumps({"experiment_ids": ["1"], "max_results": 100}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with consultar.open(consulta, timeout=30) as resposta:
            runs = json.load(resposta)["runs"]
        assert len(runs) == 10 and all(r["info"]["status"] == "FINISHED" for r in runs)
        executar("ui-inspecao", ["docker", "inspect", ui])
        resultado_http = {
            "inicio_utc": inicio_http,
            "fim_utc": datetime.now(UTC).isoformat(),
            "saude_http": 200,
            "runs_finalizados": len(runs),
            "consultas": ["GET /health", "POST /api/2.0/mlflow/runs/search"],
            "destino": "http://127.0.0.1:5000",
            "experimentos": ["1"],
        }
        log_http = ROOT / "docs/validacao/docker-sequencial-http.json"
        log_http.write_text(json.dumps(resultado_http, indent=2) + "\n", "utf-8")
        evidencia["ui"] = resultado_http | {
            "log": log_http.relative_to(ROOT / "docs").as_posix(),
            "log_sha256": hashlib.sha256(log_http.read_bytes()).hexdigest(),
        }
    finally:
        executar("encerrar-ui", ["docker", "stop", ui])
    fontes = [
        ROOT / nome
        for nome in (
            "Dockerfile",
            ".dockerignore",
            "compose.yaml",
            "compose.sem-rede.yaml",
            "pyproject.toml",
            "uv.lock",
            "params.yaml",
            ".python-version",
            ".gitattributes",
            "scripts/verificar_docker.py",
        )
    ]
    fontes.extend((ROOT / "src").rglob("*.py"))
    evidencia["arquivos_sha256"] = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes
    }
    evidencia["fim_utc"] = datetime.now(UTC).isoformat()
    destino.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("Verificação sequencial concluída; volumes preservados para inspeção.")


if __name__ == "__main__":
    main()
