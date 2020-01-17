#!/bin/sh
#source ../venv/bin/activate
set -e

echo "Generating Static fonts"
mkdir -p ../fonts/static/ttfs
fontmake -g Commissioner-Variable.glyphs -i -a -o ttf --output-dir ../fonts/static/ttfs/

#echo "Generating VFs"
#mkdir -p ../fonts/variable
#fontmake -g Commissioner-Variable.glyphs -o variable -a --output-path ../fonts/variable/Commissioner[FLAR,VOLM,slnt,wght].ttf
#rm -rf master_ufo/ instance_ufo/
#echo "Post processing"


ttfs=$(ls ../fonts/static/ttfs/*.ttf)
echo $ttfs
for ttf in $ttfs
do
	gftools fix-dsig -f $ttf;
	gftools fix-nonhinting $ttf "$ttf.fix";
	gftools fix-hinting $ttf;
	mv "$ttf.fix" $ttf;
done
rm ../fonts/static/ttfs/*backup*.ttf

#vfs=$(ls ../fonts/variable/*.ttf)
#for vf in $vfs
#do
#	gftools fix-dsig -f $vf;
#	gftools fix-nonhinting $vf "$vf.fix";
#	gftools fix-hinting $vf;
#	mv "$vf.fix" $vf;
#	ttx -f -x "MVAR" $vf; # Drop MVAR. Table has issue in DW
#	rtrip=$(basename -s .ttf $vf)
#	new_file=../fonts/variable/$rtrip.ttx;
#	rm $vf;
#	ttx $new_file
#	rm ../fonts/variable/*.ttx
#done
#rm ../fonts/variable/*backup*.ttf

#gftools fix-vf-meta $vfs;
#for vf in $vfs
#do
#	mv "$vf.fix" $vf;
#done

#fontbakery check-googlefonts ../fonts/variable/*.ttf --ghmarkdown ../checks/checks_variable.md
fontbakery check-googlefonts ../fonts/static/ttfs/*.ttf --ghmarkdown ../checks/checks_static.md



