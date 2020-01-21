### Run in the terminal by entering this file path (must be given execute permissions with chmod)
### requires a python 3 environment

#!/bin/sh
#source ../venv/bin/activate
set -e


############################################
######### generate static fonts ############


echo "Generating Static fonts"
mkdir -p ../fonts/static/ttfs
rm ../fonts/static/ttfs/*.ttf
fontmake -g Commissioner-Variable-production.glyphs -i -a -o ttf --output-dir ../fonts/static/ttfs/
rm -rf master_ufo/ instance_ufo/ #deletes everything in root directory

######### generate static fonts ############
############################################




############################################
########## opentype table fixes ############


echo "Post processing static fonts"

ttfs=$(ls ../fonts/static/ttfs/*.ttf)
for ttf in $ttfs
do
    # fix DSIG #
	echo "fix DSIG in " $ttf
    gftools fix-dsig --autofix $ttf
	
	# fix hinting #
	gftools fix-nonhinting $ttf $ttf.fix;
	gftools fix-hinting $ttf; 
	mv "$ttf.fix" $ttf;	
done
# remove any backup files #
rm ../fonts/static/ttfs/*backup*.ttf
		

########## opentype table fixes ############
############################################




############################################
############### font bake ##################


fontbakery check-googlefonts ../fonts/static/ttfs/*.ttf --ghmarkdown ../checks/checks_static.md


############### font bake ##################
############################################


