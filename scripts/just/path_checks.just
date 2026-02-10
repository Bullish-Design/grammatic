check-missing PATH ERROR:
    "{{justfile_directory()}}/scripts/just/path_checks.sh" missing "{{PATH}}" "{{ERROR}}"

check-dir PATH ERROR:
    "{{justfile_directory()}}/scripts/just/path_checks.sh" dir "{{PATH}}" "{{ERROR}}"

check-file PATH ERROR:
    "{{justfile_directory()}}/scripts/just/path_checks.sh" file "{{PATH}}" "{{ERROR}}"
