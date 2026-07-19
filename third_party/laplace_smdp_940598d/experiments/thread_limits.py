"""Set conservative BLAS/OpenMP thread defaults before NumPy is imported."""

from __future__ import annotations

import os


def configure(default_threads: str = "1") -> None:
    explicit = os.environ.get("LAPLACE_NUM_THREADS")
    value = explicit or default_threads
    variables = [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ]
    for name in variables:
        if explicit is not None:
            os.environ[name] = value
        else:
            os.environ.setdefault(name, value)


configure()
