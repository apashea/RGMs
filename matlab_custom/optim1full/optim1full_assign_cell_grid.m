function optim1full_assign_cell_grid(parentExpr, flatCells, nr, nc)
%OPTIM1FULL_ASSIGN_CELL_GRID Assign flat Engine cell vector to parent cell grid.
%   parentExpr — MATLAB lhs in **base** workspace, e.g. 'PDP.Q.O{1}' or 'PDP.O'
%   flatCells  — column cell vector (length nr*nc)
%   nr, nc     — grid shape (column-major reshape like MATLAB cell grids)
%
%   Uses assignin/evalin('base', ...) so callers from Engine API update PDP.

flatCells = flatCells(:);
if numel(flatCells) ~= nr * nc
    error('optim1full_assign_cell_grid: flatCells length %d ~= nr*nc=%d', numel(flatCells), nr * nc);
end
G = reshape(flatCells, nr, nc);
assignin('base', 'rgms_G', G);
evalin('base', [parentExpr ' = rgms_G;']);

end
