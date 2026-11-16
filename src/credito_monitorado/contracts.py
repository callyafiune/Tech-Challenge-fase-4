"""Contrato estrito para dados de crédito, sem divulgar registros nos erros."""

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

PAY_COLUMNS = ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"]
BILL_COLUMNS = [f"bill_amt{month}" for month in range(1, 7)]
AMOUNT_COLUMNS = [f"pay_amt{month}" for month in range(1, 7)]
FEATURES = ["limit_bal", "age", *PAY_COLUMNS, *BILL_COLUMNS, *AMOUNT_COLUMNS]
DEMOGRAPHIC_COLUMNS = ["sex", "education", "marriage"]
REQUIRED_COLUMNS = ["record_id", *FEATURES]


class DataContractError(ValueError):
    """Violação do contrato; a mensagem nunca contém valores dos clientes."""


def _integer_check() -> pa.Check:
    return pa.Check(lambda values: (values % 1 == 0).all(), name="inteiro_sem_truncamento")


def _schema(require_target: bool) -> pa.DataFrameSchema:
    columns = {
        "record_id": pa.Column(checks=[pa.Check.greater_than(0), _integer_check()], unique=True),
        "limit_bal": pa.Column(checks=[pa.Check.greater_than(0), pa.Check.le(2_000_000)]),
        "age": pa.Column(checks=[pa.Check.in_range(19, 100), _integer_check()]),
        "sex": pa.Column(checks=[pa.Check.isin([1, 2]), _integer_check()], required=require_target),
        "education": pa.Column(
            checks=[pa.Check.in_range(0, 6), _integer_check()], required=require_target
        ),
        "marriage": pa.Column(
            checks=[pa.Check.in_range(0, 3), _integer_check()], required=require_target
        ),
        "target": pa.Column(
            checks=[pa.Check.isin([0, 1]), _integer_check()], required=require_target
        ),
    }
    columns.update(
        {
            name: pa.Column(checks=[pa.Check.in_range(-2, 8), _integer_check()])
            for name in PAY_COLUMNS
        }
    )
    columns.update(
        {name: pa.Column(checks=pa.Check.in_range(-1_000_000, 2_000_000)) for name in BILL_COLUMNS}
    )
    columns.update(
        {name: pa.Column(checks=pa.Check.in_range(0, 2_000_000)) for name in AMOUNT_COLUMNS}
    )
    return pa.DataFrameSchema(columns, strict=True, coerce=False, unique_column_names=True)


def validate_batch(df: pd.DataFrame, require_target: bool = True) -> pd.DataFrame:
    """Valida tipos, unicidade e domínios, preservando valores e tipos da entrada.

    Códigos 0, 5 e 6 de escolaridade e 0 de estado civil são mantidos como na
    fonte UCI. Na inferência os demográficos não utilizados pelo modelo são
    opcionais, mas são validados quando presentes. Não há imputação, descarte
    de registros ou coerção de textos.
    """
    message = "Lote rejeitado pelo contrato de dados; verifique estrutura, tipos e domínios."
    if not isinstance(df, pd.DataFrame) or df.empty or not df.columns.is_unique:
        raise DataContractError(message)
    for dtype in df.dtypes:
        if not is_numeric_dtype(dtype) or is_bool_dtype(dtype) or is_complex_dtype(dtype):
            raise DataContractError(message)
    try:
        if np.isfinite(df.to_numpy(dtype=float)).all():
            return _schema(require_target).validate(df.copy(deep=True), lazy=True)
    except (pa.errors.SchemaError, pa.errors.SchemaErrors, TypeError, ValueError):
        # O Pandera retém valores inválidos na exceção; descarte-a por completo.
        pass
    # Fora do except, __context__ também permanece vazio, sem dados individuais.
    raise DataContractError(message)
