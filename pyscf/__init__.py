"""Local shim for the `pyscf` package (no Windows wheel available).

qiskit-addon-slc only uses `pyscf.lib.davidson1` to find the minimal eigenvalue of a
Hermitian sparse matrix. This shim provides that one function on top of scipy's eigsh.
Lives in the project folder so it is found before any (missing) site-packages install.
"""
import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh


class _Lib:
    @staticmethod
    def davidson1(aop, x0, precond, tol=1e-6, max_cycle=500, max_space=12, lindep=1e-11,
                  max_memory=2000, **_):
        n = len(x0[0])
        op = LinearOperator((n, n), matvec=lambda v: aop([v])[0], dtype=np.complex128)
        try:
            vals, vecs = eigsh(op, k=1, which="SA", v0=x0[0], tol=tol, maxiter=max_cycle * 10)
            return [True], [float(vals[0])], [vecs[:, 0]]
        except Exception as exc:  # ArpackNoConvergence etc.
            vals = getattr(exc, "eigenvalues", None)
            if vals is not None and len(vals):
                return [False], [float(np.min(vals))], [None]
            raise


lib = _Lib()
