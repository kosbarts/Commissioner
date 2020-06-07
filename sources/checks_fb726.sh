### Run in the terminal by entering this file path (must be given execute permissions with chmod)
### requires a python 3 environment

#!/bin/sh
#source ../venv/bin/activate
set -e





############################################
############### font bake ##################


fontbakery check-googlefonts ../fonts-tests/static_fm213/ttfs/*.ttf --ghmarkdown ../sources/checks/checks_static-fm213-fb726.md


############### font bake ##################
############################################


fontbakery check-googlefonts ../fonts-tests/variable_fm213/*.ttf --ghmarkdown ../sources/checks/checks_variable-fm213-fb726.md
