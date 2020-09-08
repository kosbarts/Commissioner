
### Step 2: Build the fonts

**Design vs Production source file**

TTFautohint doesn't like components which have been flipped. Commissioner.glyphs is the working design file with all components kept in place. If you are planning to make changes in the desing you should work on this one. The file features 2 (two) sets of 54 instances, with one set activated. 

For production it is suggested to copy the file and rename it accordingly to a file name that the Builds use. Rename to: 

- Commissioner-production.glyphs . Keep the active instances. The file can be used to generate either the variable font, or the static ttf's, or both. The instances are named so that they can produce the static ttf's in 3 subfamilies. The variable font during the build will be patched automatically (vf_patch.ttx) to add the STAT table, and amend the name and fvar table.


- Commissioner-Variable-production.glyphs . Deactivate the active instances and activate the second set of instances. The file can be used to produce just the variable font. The second sets of instances are named in a variable friendly way so that there is no need to patch the fvar table during production. The variable font during the build process will be patched automatically (vf_Variablepatch.ttx) to add the STAT table and amend the name table. 

After you copy and rename the new file, add the script `sources/helpers/decompose-transformed-components.py` to your Glyphs scripts folder, reload scripts (opt+sft+cmd+Y), and run it on the new file before production. Affected glyphs show up in a new tab and you should check for any compatability issues.  


**Building the fonts**

The scripts for building the fonts are in the `/sources/` folder.

To build the variable font using Commissioner-Variable-production.glyphs run:

```
cd sources
sh build_Variablevf.sh
```

To build the variable font using Commissioner-production.glyphs run:

```
cd sources
sh build_vf.sh
```

To build the static ttfs using Commissioner-production.glyphs run:

```
cd sources
sh build_statics.sh
```

To build the variable font and the static ttfs using Commissioner-production.glyphs run:

```
cd sources
sh build_all.sh
```  

If you want to build otf's do so through Glyphs using the source Glyphs file with the default active instances. 

**Weight Class Fix**

The usWeightClass for Thins and UltraLight are set to 100 and 200 consecutively. There is a debate on whether these values cause the fonts to get blurred on certain versions of Windows. (https://github.com/googlefonts/fontbakery/issues/2364) 

If you want to change them to 250 and 275 copy the script `sources/fix_usWeightClass.py` to your fonts directory and run it as follows.

```
cd fontfolder # make sure to change to the directory that includes the ttf's or otf's
python fix_usWeightClass.py
```

