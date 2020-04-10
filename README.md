# Commissioner
Commissioner is a variable and static sans typeface designed by Kostas Bartsokas.

![](sources/proofs/Commissioner_temporary.gif) 

## Basic Information
Commissioner is a low-contrast humanist sans-serif with almost classical proportions, conceived as a variable family. The family consists of three “voices”. The default style is a grotesque with straight stems. As the flair axis grows the straight grotesque terminals develop a swelling and become almost glyphic serifs and the joints become more idiosyncratic. The volume axis transforms the glyphic serifs to wedge-like ones. 

Each voice of Commissioner comes in a range of styles from Thin to Black including italics. The diverse proportions of lowercase and capitals add warmth and appeal to texts across sizes, while the different voices can express a variation in the typographic texture that ranges from delicate in text sizes to exuberant in larger sizes. 

Commissioner supports the Google Latin Plus and Google Latin Pro character sets.
Further expansions to scripts support include Greek and Cyrillic and are coming in 2020.

This typeface project received financial support from Google, and in the future may be available in Google Fonts.

**Variable Axes**

Commisioner has the following axes:

- Weight (wght) - 100 to 900. (Default 100) Controls the darkness of the composed text. Thin, UltraLight, ExtraBold, and Black are ideally used for display sizes, while Light, Regular, Medium, Semibold, Bold can be used for both display and text sizes.

- Slant (slnt) - 0 to -12 degrees. (Default 0) Controls the slant of the letters. A stronger slant creates more emphasis and contrast to upright styles. 

- Flair (FLAR) - 0 to 100. (Default 0) The values are arbitrary and the lenght of the axis could be narrower (i.e. 0 to 10). As the flair axis grows the straight grotesque terminals develop a swelling and joints become more idiosyncratic. The flair axis was originally called Flare, referring to the flaring of the stems, but at some point I decided to name it flair, as in stylisness and panache. 

- Volume (VOLM) - 0 to 100. (Default 0) The values are arbitrary and the lenght of the axis could be narrower (i.e. 0 to 10). The volume axis works only in combination with the Flair axis. It transforms the glyphic serifs to wedge-like ones and add a little more edge to details.  

## Building the fonts

### Step 1: Install Requirements

Set up a virtual environment in the root directory:

```
virtualenv -p python3 venv
```

Activate the virtual environment with:

```
source venv/bin/activate
```

Install requirements with:

```
pip install -U -r requirements.txt
```

### Step 2: Build the fonts

**Design vs Production source file**

TTFautohint doesn't like components which have been flipped. Commissioner-Variable.glyphs is the working design file with all components kept in place. If you are planning to make changes in the desing you should work on this one. 

For production it is suggested to copy the file and rename it to Commissioner-Variable-production.glyphs which is the file name that the Builds use. Add the script `sources/helpers/decompose-transformed-components.py` to your Glyphs scripts folder and run it before production. Affected glyphs show up in a new tab and you should check for any compatability issues. 

**Building the fonts**

The scripts for building the fonts are in the `/sources/` folder.

To build the variable font run:

```
cd sources
sh build_vf.sh
```

To build the static ttfs run:

```
cd sources
sh build_statics.sh
```

To build the variable font and the static ttfs run:

```
cd sources
sh build_all.sh
```  

If you want to build otf's do so through Glyphs using the source Glyphs file. 

**Weight Class Fix**

The usWeightClass for Thins and UltraLight are set to 100 and 200 consecutively. There is a debate on whether these values cause the fonts to get blurred on certain versions of Windows. (https://github.com/googlefonts/fontbakery/issues/2364) 

If you want to change them to 250 and 275 copy the script `sources/fix_usWeightClass.py` to your fonts directory and run it as follows.

```
cd fontfolder # make sure to change to the directory that includes the ttf's or otf's
python fix_usWeightClass.py
```

## ChangeLog

This is version 1.000. No changes to report. 

## License

Commissioner is licensed under the SIL Open Font License v1.1 (<http://scripts.sil.org/OFL>).

To view the copyright and specific terms and conditions please refer to [OFL.txt](https://github.com/kosbarts/Commissioner/blob/master/OFL.txt)
