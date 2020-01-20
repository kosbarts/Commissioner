### Run in the terminal by entering this file path (must be given execute permissions with chmod)
### requires a python 3 environment

#!/bin/sh
#source ../venv/bin/activate
set -e


############################################
#### generate static and variable fonts ####


echo "Generating Static fonts"
mkdir -p ../fonts/static/ttfs
rm ../fonts/static/ttfs/*.ttf
fontmake -g Commissioner-Variable.glyphs -i -a -o ttf --output-dir ../fonts/static/ttfs/


echo "Generating VFs"
mkdir -p ../fonts/variable
fontmake -g Commissioner-Variable.glyphs -o variable --output-path ../fonts/variable/Commissioner[FLAR,VOLM,slnt,wght].ttf
rm -rf master_ufo/ instance_ufo/ #deletes everything in root directory


#### generate static and variable fonts ####
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
	ttx -m $vf vf-patch.ttx
	mv vf-patch.ttf "../fonts/variable/Commissioner[FLAR,VOLM,slnt,wght].ttf"
	#rm vf-patch.ttf
done
# remove any backup files #
rm ../fonts/variable/*backup*.ttf


########## opentype table fixes ############
############################################




############################################
############### font bake ##################


fontbakery check-googlefonts ../fonts/static/ttfs/*.ttf --ghmarkdown ../checks/checks_static.md
fontbakery check-googlefonts ../fonts/variable/*.ttf --ghmarkdown ../checks/checks_variable.md


############### font bake ##################
############################################


