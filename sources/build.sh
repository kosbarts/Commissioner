#!/bin/sh
#source ../venv/bin/activate
set -e

#echo "Generating Static fonts"
#mkdir -p ../fonts/ttfs
#fontmake -g Commissioner-Variable.glyphs -i -o ttf --output-dir ../fonts/ttfs/

echo "Generating VFs"
mkdir -p ../fonts/variable
fontmake -g Commissioner-Variable.glyphs -o variable --output-path ../fonts/variable/Commissioner-VF.ttf

rm -rf master_ufo/ instance_ufo/
echo "Post processing"


#ttfs=$(ls ../fonts/ttfs/*.ttf)
#echo $ttfs
#for ttf in $ttfs
#do
#	gftools fix-dsig -f $ttf;
#	gftools fix-nonhinting $ttf "$ttf.fix";
#	mv "$ttf.fix" $ttf;
#done
#rm ../fonts/ttfs/*backup*.ttf

vfs=$(ls ../fonts/variable/*.ttf)
for vf in $vfs
do
	gftools fix-dsig -f $vf;
	gftools fix-nonhinting $vf "$vf.fix";
	mv "$vf.fix" $vf;
	ttx -f -x "MVAR" $vf; # Drop MVAR. Table has issue in DW
	rtrip=$(basename -s .ttf $vf)
	new_file=../fonts/variable/$rtrip.ttx;
	rm $vf;
	ttx $new_file
	rm ../fonts/variable/*.ttx
done
rm ../fonts/variable/*backup*.ttf

gftools fix-vf-meta $vfs;
for vf in $vfs
do
	mv "$vf.fix" $vf;
done



#cd ..
#
## ============================================================================
## Autohinting ================================================================
#
#statics=$(ls fonts/ttfs/*.ttf)
#echo hello
#for file in $statics; do 
#    echo "fix DSIG in " ${file}
#    gftools fix-dsig --autofix ${file}
#
#    echo "TTFautohint " ${file}
#    # autohint with detailed info
#    hintedFile=${file/".ttf"/"-hinted.ttf"}
#    ttfautohint -I ${file} ${hintedFile} 
#    cp ${hintedFile} ${file}
#    rm -rf ${hintedFile}
#done

