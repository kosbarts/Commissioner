### Run in the terminal by entering this file path (must be given execute permissions with chmod)
### requires a python 3 environment

#!/bin/sh
#source ../venv/bin/activate
set -e


############################################
######### generate variable font ###########


echo "Generating VFs"
mkdir -p ../fonts/variable
fontmake -g Commissioner-Variable-production.glyphs -o variable --output-path ../fonts/variable/Commissioner[FLAR,VOLM,slnt,wght].ttf
rm -rf master_ufo/ instance_ufo/ #deletes everything in root directory


######### generate variable font ###########
############################################




############################################
########## opentype table fixes ############


echo "Post processing variable fonts"

vfs=$(ls ../fonts/variable/*.ttf)
for vf in $vfs
do
    # fix DSIG #
	echo "fix DSIG in " $vf
    gftools fix-dsig --autofix $vf
	
	# fix hinting #
	gftools fix-nonhinting $vf $vf.fix;
	gftools fix-hinting $vf; 
	mv "$vf.fix" $vf;
	
	# drop MVAR. Table has issue with DW #
	ttx -f -x "MVAR" $vf; 
	rtrip=$(basename -s .ttf $vf)
	new_file=../fonts/variable/$rtrip.ttx;
	rm $vf;
	ttx $new_file
	rm $new_file
	
	# patch Name and STAT table #	
	ttx -m $vf "../sources/helpers/vf-patch.ttx"
	mv "../sources/helpers/vf-patch.ttf" "../fonts/variable/Commissioner[FLAR,VOLM,slnt,wght].ttf"
done
# remove any backup files #
rm ../fonts/variable/*backup*.ttf


########## opentype table fixes ############
############################################




############################################
############### font bake ##################


fontbakery check-googlefonts ../fonts/variable/*.ttf --ghmarkdown ../checks/checks_variable.md


############### font bake ##################
############################################



