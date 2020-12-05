### Run in the terminal by entering this file path (must be given execute permissions with chmod)
### requires a python 3 environment

#!/bin/sh
set -e

#requires https://github.com/bramstein/homebrew-webfonttools
#source ../venv/bin/activate
#brew tap bramstein/webfonttools
#brew install woff2

############################################
############## Make webfonts ###############


echo "Making Static and Variable webfonts"
rm -rf ../fonts/webfonts/* ../fonts/webfonts/woff2/* 
mkdir -p ../fonts/webfonts ../fonts/webfonts/woff2 


ttfs=$(ls ../fonts/static/ttfs/*.ttf)
for ttf in $ttfs
do
  woff2_compress $ttf
done

vfs=$(ls ../fonts/variable/*.ttf)
for vf in $vfs
do
  woff2_compress $vf
done

stwoff2s=$(ls ../fonts/static/ttfs/*.woff2)
for fonts in $stwoff2s
do
	mv $fonts ../fonts/webfonts/woff2/
done
vfwoff2s=$(ls ../fonts/variable/*.woff2)
for fonts in $vfwoff2s
do
	mv $fonts ../fonts/webfonts/woff2/
done

echo "Done!"

############## Make webfonts ###############
############################################



