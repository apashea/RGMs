- pulled Karim's github
- updated "andrew" branch to match "karim"
- ignore "karim" going forward, work in "andrew"

Initial pull and "andrew" update to match "karim" without touching "karim":
```
git clone https://github.com/KZaghw/RGMs.git     # pull full repo
cd .\RGMs                                        # correct directory
git fetch origin --prune                         # remove superfluous
git branch -a                                    
git switch --track -c karim origin/karim
git switch --track -c andrew origin/andrew
git switch andrew
git reset --hard origin/karim
git push --force-with-lease origin andrew
git status
git branch --show-current
```

## Confirming alignment
```
git rev-parse andrew
git rev-parse origin/karim
git rev-parse origin/andrew
```

## Ensure creds
```
# Set your global Git name (what shows up on commits)
git config --global user.name "apashea"

# Set your global Git email (should match a verified GitHub email)
git config --global user.email "andrewbpashea@gmail.com"
```

## Pushing to github: `status`->`add`->`diff`->`commit`->`push`
```
# From within the RGMs\ repo on branch `andrew`:
git status                                       # check repo connection
git branch --show-current                        # double-check desired branch
git add python_src/ matlab_src/ tests/ notes/ logs/ matlab_custom/ misc/    # add only from designated subdirectories
git status                                       # confirm what is staged for commit
git --no-pager diff --cached --name-only         # double-check specific files to be added/updated
git commit -m "Commit msg here"                  # commit with message
git push origin andrew                           # push the commit to your remote branch, e.g., "andrew"
```

## Hard reset to `main` (for major PRs)
1. Ensure no abort due to untracked files existing
```
cd C:\Users\andre\.cursor\RGMs   # repo root
git fetch origin                 # update origin/* (no changes to remote)
git switch andrew
git reset --hard                 # discard ALL local changes to tracked files on the CURRENT branch
git clean -fd                    # delete ALL untracked files and directories on the CURRENT branch
git status                       # should now show clean; switching branches will no longer abort
```

2. Pull all for refresh
```
cd C:\Users\andre\.cursor\RGMs   # go to repo root

git fetch origin                 # update origin/* from GitHub

git switch main                  # go to main
git reset --hard origin/main     # make local main EXACTLY origin/main
git clean -fd                    # delete ALL untracked files/dirs on main

git switch karim                 # go to karim
git reset --hard origin/karim    # make local karim EXACTLY origin/karim
git clean -fd                    # delete ALL untracked files/dirs on karim

git switch andrew                # go to andrew (create once with: git switch --track -c andrew origin/andrew)
git reset --hard origin/main     # make local andrew EXACTLY origin/main (same content as main)
git clean -fd                    # delete ALL untracked files/dirs on andrew

git push --force-with-lease origin andrew    # overwrite remote andrew to match local andrew (i.e., main)
git status                                         # confirm: on andrew, clean, ready to edit only andrew

```

## Recovery
```
# --------------------------------------------------------------------
# SAFETY / RECOVERY COMMANDS (run only when needed)
# --------------------------------------------------------------------
# A) If a forbidden file like AGENTS.md got staged by mistake, unstage it
#    without touching the working-copy edits.
git restore --staged AGENTS.md
# B) If you want to completely discard local edits to AGENTS.md and revert it
#    back to the last committed version on your current branch:
git restore AGENTS.md
# C) Optional: tell Git to ignore local changes to AGENTS.md going forward
#    (Git will treat it as "assume unchanged" and not show it in `git status`).
git update-index --assume-unchanged AGENTS.md
# D) If you later DO need to edit AGENTS.md intentionally, re-enable tracking:
git update-index --no-assume-unchanged AGENTS.md
```

## `conda` and `matlab.engine` setup
```
conda env list                     # check available envs
conda create -n rgms python=3.11   # create rgms env
cd C:\Users\andre\.cursor\RGMs     # cd into repo directory
conda activate rgms                # activate rgms
python -c "import sys; print(sys.executable)"   # confirm python available
python -V                                       # confirm Python version
python -m pip install matlabengine==24.2.2     # install matlab engine (check your version first; example 2024b)
python -c "import matlab.engine; print('matlab.engine import OK')"    # ensure matlab.engine imports successfully
python -c "import matlab.engine; eng = matlab.engine.start_matlab(); print(eng.sqrt(4.0)); eng.quit()"  # start_matlab
```


## Check all files and contents, save to .md
```
cd C:\Users\andre\.cursor\RGMs

# Ensure notes/ exists (safe even if it already does)
New-Item -ItemType Directory -Path .\notes -Force | Out-Null

# 1) Header + timestamp
"## RGMs repo file snapshot`r`n`r`nGenerated: $(Get-Date -Format o)`r`n" `
  | Out-File -FilePath .\notes\files_initial_check.md -Encoding UTF8

# 2) Full tree section (all files and folders, recursive)
"### Full tree`r`n" `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

Get-ChildItem -Recurse `
  | Select-Object FullName, Length, LastWriteTime `
  | Out-String `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

# 3) matlab_src tree
"### matlab_src tree`r`n" `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

Get-ChildItem matlab_src -Recurse `
  | Select-Object FullName, Length, LastWriteTime `
  | Out-String `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

# 4) python_src tree
"### python_src tree`r`n" `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

Get-ChildItem python_src -Recurse `
  | Select-Object FullName, Length, LastWriteTime `
  | Out-String `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

# 5) tests tree
"### tests tree`r`n" `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

Get-ChildItem tests -Recurse `
  | Select-Object FullName, Length, LastWriteTime `
  | Out-String `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

# 6) notes tree (so the snapshot file itself and other notes are visible)
"### notes tree`r`n" `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8

Get-ChildItem notes -Recurse `
  | Select-Object FullName, Length, LastWriteTime `
  | Out-String `
  | Out-File -FilePath .\notes\files_initial_check.md -Append -Encoding UTF8
```

## Traceback for these steps:
- Promptable: https://www.perplexity.ai/search/my-colleague-gave-me-access-to-chAPS0FcQmOwbF3RY5gCSg
- Shareable: https://www.perplexity.ai/search/my-colleague-gave-me-access-to-chAPS0FcQmOwbF3RY5gCSg#10


