$env:STREAMLIT_SERVER_FILE_WATCHER_TYPE="none"
Write-Output "Environment variable STREAMLIT_SERVER_FILE_WATCHER_TYPE=none has been set temporarily, to prevent terminal log error of RuntimeError: Tried to instantiate class '__path__._path'."
Pause
# HOW TO RUN:
#   1. Right-click this file → "Run with PowerShell"
#   2. OR open PowerShell, cd to this folder, then run:
#        .\streamlit-reload-error-log-debug.ps1