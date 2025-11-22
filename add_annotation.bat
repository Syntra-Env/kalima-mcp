@echo off
cd /d "%~dp0"

python scripts/add_annotation.py ^
  --verse 27:19 ^
  --type stylistic ^
  --subtype "speech-open" ^
  --scope span ^
  --tokens "5,6,7" ^
  --note "Opening formula of Sulayman's dua: direct address + request pattern mirrors Ibrahim's style but with different thematic focus." ^
  --tags "sulayman,speech,opening,style" ^
  --status raw ^
  --backup

pause
