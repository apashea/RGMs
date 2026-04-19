# Python MATLAB Translation Issues

This file records settled corner-case decisions for faithful MATLAB-to-Python
translation in this repository.

Future agents should read this file before translating or changing tests. If a
new MATLAB/Python corner case appears, ask the user first; after a decision is
settled, add the decision here so later translations handle it consistently.

## Raw 1-D NumPy Arrays

Decision: treat raw 1-D numeric NumPy arrays as MATLAB row vectors.

MATLAB numeric vectors have orientation. A literal like `[1 2 3]` is a row
vector, while `[1; 2; 3]` is a column vector. NumPy arrays with shape `(n,)`
have no orientation, so translated functions should interpret them as row
vectors with shape `(1, n)`. Column vectors must be passed explicitly with
shape `(n, 1)`.

This policy matters for shape-sensitive functions including `spm_log.py`,
`spm_softmax.py`, `spm_psi.py`, `spm_betaln.py`, `spm_cat.py`,
`spm_cross.py`, `spm_dot.py`, `spm_cov2corr.py`, and new translations such as
`spm_sum.py` and `spm_MDP_size.py`.

## Shared `matlab_compat.py`

Decision: repo-root `matlab_compat.py` is an approved narrow exception to the
default rule against shared runtime translation helpers.

This file may contain only mechanical MATLAB compatibility primitives that are
used by multiple translated files, such as row-vector normalization, sparse
`full` conversion, MATLAB-like scalar unwrapping, and size/ndims behavior. Do
not move file-specific translation logic such as cell-array interpretation,
tensor products, concatenation rules, or MDP field access into this helper.

Add new helpers there only after the behavior is repeated across multiple
translations and settled against MATLAB oracle behavior.

## `spm_cat` Scalar Zero Partitions

Decision: follow the repository MATLAB `.m` source, not the docstring text, for
scalar zero partitions.

The `spm_cat.m` docstring says single `0` entries are expanded, but the fallback
MATLAB source in this repository only replaces empty cells. The expression
`spm_cat({eye(2), []; 0, [1 1; 1 1]})` errors in the `.m` fallback with
inconsistent concatenation dimensions. Python should not implement scalar-zero
expansion unless the MATLAB source used as oracle changes.

## `spm_check_version.py` MATLAB Engine Delegation

Decision: keep `spm_check_version.py` backed by MATLAB Engine for exact oracle
fidelity.

`spm_check_version.m` depends on the running MATLAB/Octave/toolbox installation
and MATLAB's `version`/`ver` behavior. Do not hard-code a Python version table.
The Python port should lazily delegate to the repository MATLAB source through
MATLAB Engine and surface MATLAB-originated errors.
