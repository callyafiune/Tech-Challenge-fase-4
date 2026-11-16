"""Aquisição rastreável da base UCI e separação estratificada sem vazamento."""

import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile

import pandas as pd
from sklearn.model_selection import train_test_split

from credito_monitorado.contracts import validate_batch

DATASET_URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
# Verificado por HTTPS na fonte oficial UCI em 16/11/2026; alterações exigem nova auditoria.
DATASET_ZIP_SHA256 = "56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602"
DATASET_XLS_SHA256 = "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def acquire_dataset(cache_dir: Path) -> Path:
    """Obtém o XLS oficial e valida a integridade também ao reutilizar o cache."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / "uci350.zip"
    xls_path = cache_dir / "default_of_credit_card_clients.xls"
    manifest_path = cache_dir / "manifest.json"
    if zip_path.exists():
        content = zip_path.read_bytes()
    else:
        try:
            with urlopen(DATASET_URL, timeout=60) as response:
                content = response.read(50_000_001)
        except OSError:
            raise RuntimeError("Falha ao obter o dataset oficial UCI.") from None
    if _sha256(content) != DATASET_ZIP_SHA256:
        raise ValueError("A integridade do arquivo UCI não corresponde à versão aprovada.")
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            candidates = [entry for entry in archive.infolist() if entry.filename.endswith(".xls")]
            if len(candidates) != 1 or candidates[0].file_size > 50_000_000:
                raise ValueError("Estrutura inesperada no arquivo oficial UCI.")
            xls_content = archive.read(candidates[0])
    except BadZipFile:
        raise ValueError("Arquivo oficial UCI inválido.") from None
    xls_hash = _sha256(xls_content)
    if xls_hash != DATASET_XLS_SHA256:
        raise ValueError("A integridade do XLS UCI não corresponde à versão aprovada.")
    if xls_path.exists() and _sha256(xls_path.read_bytes()) != xls_hash:
        raise ValueError("O cache XLS foi alterado e deve ser investigado.")
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                manifest["source_url"] != DATASET_URL
                or manifest["zip_sha256"] != DATASET_ZIP_SHA256
                or manifest["xls_sha256"] != xls_hash
            ):
                raise ValueError("O manifesto do dataset não corresponde à origem aprovada.")
        except (json.JSONDecodeError, KeyError, TypeError):
            raise ValueError("Manifesto de proveniência inválido.") from None
    else:
        manifest = {
            "source_url": DATASET_URL,
            "dataset": "UCI 350 — Default of Credit Card Clients",
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "zip_sha256": DATASET_ZIP_SHA256,
            "xls_sha256": xls_hash,
            "license": "CC BY 4.0",
            "source_rows": 30000,
            "synthetic": False,
        }
    manifest["source_size_bytes"] = len(xls_content)
    # Extrai apenas o conteúdo esperado; nenhum caminho interno do ZIP é executado.
    zip_path.write_bytes(content)
    xls_path.write_bytes(xls_content)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return xls_path


def load_dataset(path: Path, min_rows: int = 5000) -> pd.DataFrame:
    """Normaliza os nomes UCI sem recodificar valores ou substituir a fonte real."""
    if isinstance(min_rows, bool) or not isinstance(min_rows, int) or not 5000 <= min_rows <= 30000:
        raise ValueError("O mínimo do dataset deve ser inteiro entre 5.000 e 30.000.")
    try:
        content = Path(path).read_bytes()
    except OSError:
        raise ValueError("Não foi possível ler o dataset XLS oficial.") from None
    content_hash = _sha256(content)
    if content_hash != DATASET_XLS_SHA256:
        raise ValueError("A integridade do dataset XLS não corresponde à fonte aprovada.")
    try:
        df = pd.read_excel(io.BytesIO(content), header=1, engine="xlrd")
    except (OSError, ValueError):
        raise ValueError("Não foi possível ler o dataset XLS oficial.") from None
    df.columns = [str(name).strip().lower() for name in df.columns]
    df = df.rename(columns={"id": "record_id", "default payment next month": "target"})
    validated = validate_batch(df)
    if len(validated) < min_rows:
        raise ValueError(
            "O dataset não atende ao mínimo configurado de amostras financeiras reais."
        )
    validated.attrs["provenance"] = {
        "source_url": DATASET_URL,
        "xls_sha256": content_hash,
        "source_rows": len(validated),
        "source_size_bytes": len(content),
        "synthetic": False,
    }
    return validated


def split_dataset(df: pd.DataFrame, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Separa 50/15/15/20%; IDs de clientes permanecem exclusivos por partição."""
    df = validate_batch(df)
    if set(df["target"].unique()) != {0, 1}:
        raise ValueError("A separação estratificada exige as duas classes do alvo.")
    train, remainder = train_test_split(
        df, train_size=0.5, stratify=df["target"], random_state=seed
    )
    validation, remainder = train_test_split(
        remainder, train_size=0.3, stratify=remainder["target"], random_state=seed
    )
    reference, production = train_test_split(
        remainder, train_size=3 / 7, stratify=remainder["target"], random_state=seed
    )
    parts = dict(
        zip(
            ["train", "validation", "reference", "production_pool"],
            [train, validation, reference, production],
            strict=True,
        )
    )
    ids = pd.concat([part["record_id"] for part in parts.values()], ignore_index=True)
    if not ids.is_unique or len(ids) != len(df):
        raise ValueError("As partições devem ter cobertura completa e identidades exclusivas.")
    return {name: part.reset_index(drop=True).copy() for name, part in parts.items()}
