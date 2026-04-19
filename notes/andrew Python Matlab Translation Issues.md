# Python MATLAB Translation Issues — Andrew branch

This file records settled corner-case decisions for faithful MATLAB-to-Python
translation on branch `andrew`. It includes the same settled material as the
repo-root `Python Matlab Translation Issues.md` (copied here for convenience)
plus additional decisions recorded only in this branch notes file.

Future agents should read the repo-root `Python Matlab Translation Issues.md` and
this file before translating or changing tests. If a new MATLAB/Python corner
case appears, ask the user first; after a decision is settled, add it here (for
branch-specific policy) or in the repo-root file (for shared policy), as your
workflow defines.

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

## MATLAB cells: naïve `np.asarray` and same-shaped `ndarray` elements

Decision: when preserving MATLAB cell semantics in Python, do not rely on
naïve `np.asarray(...)` (including `np.asarray(..., dtype=object)`) for a Python
`list` (or similar sequence) whose elements are multiple NumPy `ndarray` values
with the **same shape**. NumPy may interpret that input as a request to stack
those arrays into a single numeric tensor (higher-dimensional `ndarray`), not
as a MATLAB-style cell vector of separate matrices.

When true MATLAB-cell behavior is required (each stored element remains its own
container entry, iterated in MATLAB `numel` / column-major order as in
`spm_dir_norm.m`), preserve the elements in an **explicit object container**
(for example, a preallocated `numpy.ndarray` with `dtype=object` and per-index
assignment, or another structure that cannot silently merge same-shaped
arrays). Apply the same care anywhere cell recursion must mirror MATLAB without
collapsing distinct `ndarray` cells into one stacked array.

This issue surfaced during the `spm_dir_norm` translation and oracle tests: a
flat Python list of two `2×2` matrices must behave like a `1×2` MATLAB cell,
not like a `2×2×2` numeric array.
