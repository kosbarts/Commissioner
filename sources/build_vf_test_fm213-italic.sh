### Run in the terminal by entering this file path (must be given execute permissions with chmod)
### requires a python 3 environment

#!/bin/sh
#source ../venv/bin/activate
set -e


############################################
######### generate variable font ###########


echo "Generating VFs"
mkdir -p ../fonts-tests/variable_fm213_italic
fontmake -g Commissioner-Variable-Cyrillic-Greek-Ext-production.glyphs -o variable --output-path ../fonts-tests/variable_fm213_italic/Commissioner-fm213italic-original[FLAR,VOLM,slnt,wght].ttf
rm -rf master_ufo/ instance_ufo/ #deletes everything in root directory


######### generate variable font ###########
############################################




############################################
########## opentype table fixes ############


echo "Post processing variable fonts"

vfs=$(ls ../fonts-tests/variable_fm213_italic/*.ttf)
for vf in $vfs
do
    # fix DSIG #
	echo "fix DSIG in " $vf
    gftools fix-dsig --autofix $vf
	
	# fix hinting #
	gftools fix-nonhinting $vf $vf.fix; #run if fonts have not been released with Google yet
	#gftools fix-hinting $vf;  #run if the fonts have been previously autohinted with ttfautohint-vf
	mv "$vf.fix" $vf;
	
	# drop MVAR. Table has issue with DW #
	ttx -f -x "MVAR" $vf; 
	rtrip=$(basename -s .ttf $vf)
	new_file=../fonts-tests/variable_fm213_italic/$rtrip.ttx;
	rm $vf;
	ttx $new_file
	rm $new_file
	
	# patch Name and STAT table #	
	ttx -m $vf "../sources/helpers/vf-patch-italic.ttx"
	mv "../sources/helpers/vf-patch-italic.ttf" "../fonts-tests/variable_fm213_italic/Commissioner-fm213italic-patched[FLAR,VOLM,slnt,wght].ttf"
done
# remove any backup files #
rm ../fonts-tests/variable_fm213_italic/*backup*.ttf


########## opentype table fixes ############
############################################




############################################
############### font bake ##################


fontbakery check-googlefonts ../fonts-tests/variable_fm213_italic/*.ttf --ghmarkdown ../sources/checks/checks_variable-fm213-fb726-italic.md


############### font bake ##################
############################################



