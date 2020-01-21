# Commissioner
Commissioner is a variable and static sans typeface designed by Kostas Bartsokas.

---

## Basic Information
Commissioner is a humanist sans-serif with almost classical proportions, conceived as a variable family. In essence it is an experiment on a low-contrast distant relative of Optima. The family consists of three “voices”. As the flare axis grows the straight grotesque terminals develop a swelling and joints become more idiosyncratic. The volume axis transforms the glyphic serifs to wedge-like ones. 

Each voice of Commissioner comes in a range of styles from Thin to Black including italics. The diverse proportions of lowercase and capitals add warmth and appeal to texts across sizes, while the different voices can express a variation in the typographic texture that ranges from delicate in text sizes to exuberant in larger sizes. 

Commissioner supports the Google Latin Plus and Google Latin Pro character sets.
Further expansions to scripts support include Greek and Cyrillic and are coming in 2020.

This typeface was funded by Google and is distributed by Google Fonts.

---

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

The scripts for building the fonts are in the `sources/` folder.

To build the variable font run:

```
sources/scripts/build_vf.sh
```

To build the static ttfs run:

```
sources/scripts/build_statics.sh
```

To build variable font and static ttfs run:

```
sources/scripts/build_all.sh
```  

If you want to build otf's do so through Glyphs using the source Glyphs file. 

**Weight Class Fix**

The usWeightClass for Thins and UltraLight are set to 100 and 200 consecutively. There is a debate on whether these values cause the fonts to get blurred on certain versions of Windows. (https://github.com/googlefonts/fontbakery/issues/2364) 

If you want to change them to 250 and 275 copy the script `sources/fix_usWeightClass.py` to your fonts directory and run it as follows.

```
cd fontfolder # make sure to change to the directory that includes the ttf's or otf's
python fix_usWeightClass.py
```

---

## ChangeLog

This is version 1.000. No changes to report. 

---

## License

Commissioner is licensed under the SIL Open Font License v1.1 (<http://scripts.sil.org/OFL>).

To view the copyright and specific terms and conditions please refer to [OFL.txt](https://github.com/kosbarts/Commissioner/blob/master/OFL.txt)
