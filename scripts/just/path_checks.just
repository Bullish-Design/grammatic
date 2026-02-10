check-missing PATH ERROR:
    "{{justfile_directory()}}/scripts/just/path_checks.py" missing "{{PATH}}" "{{ERROR}}"

check-dir PATH ERROR:
    "{{justfile_directory()}}/scripts/just/path_checks.py" dir "{{PATH}}" "{{ERROR}}"

check-file PATH ERROR:
    "{{justfile_directory()}}/scripts/just/path_checks.py" file "{{PATH}}" "{{ERROR}}"
