Inside Glyphs App:

gf-glyphs-scripts:
- Check Conflicting Anchors - Pass

- Check Missing Anchors - Pass

- Initial Setting of Vertical Metrics - Done

- FB Check Contours - Pass

- Decompose Transformed Components -

- Fix Fonts for GF spec -

- Proof kerning for current master -

- QA
Start
Flair Thin is not a correct style name
Flair ExtraLight is not a correct style name
Flair Light is not a correct style name
Flair Regular is not a correct style name
Flair Medium is not a correct style name
Flair SemiBold is not a correct style name
Flair Bold is not a correct style name
Flair ExtraBold is not a correct style name
Flair Black is not a correct style name
Flair Thin Italic is not a correct style name
Flair ExtraLight Italic is not a correct style name
Flair Light Italic is not a correct style name
Flair Italic is not a correct style name
Flair Medium Italic is not a correct style name
Flair SemiBold Italic is not a correct style name
Flair Bold Italic is not a correct style name
Flair ExtraBold Italic is not a correct style name
Flair Black Italic is not a correct style name
Loud Thin is not a correct style name
Loud ExtraLight is not a correct style name
Loud Light is not a correct style name
Loud Regular is not a correct style name
Loud Medium is not a correct style name
Loud SemiBold is not a correct style name
Loud Bold is not a correct style name
Loud ExtraBold is not a correct style name
Loud Black is not a correct style name
Loud Thin Italic is not a correct style name
Loud ExtraLight Italic is not a correct style name
Loud Light Italic is not a correct style name
Loud Italic is not a correct style name
Loud Medium Italic is not a correct style name
Loud SemiBold Italic is not a correct style name
Loud Bold Italic is not a correct style name
Loud ExtraBold Italic is not a correct style name
Loud Black Italic is not a correct style name
Google Fonts QA
~~~~~~~~~~~~~~~

Tests to ensure .glyphs files follow the Google Fonts specification.

The Google Fonts specification:
https://github.com/googlefonts/gf-docs/blob/master/ProjectChecklist.md

Quick start guide for Glyphs:
https://github.com/googlefonts/gf-docs/blob/master/QuickStartGlyphs.md


A fix script which will attempt to update the font to match the
specification can be found in the same directory as this script.
Google Fonts > Fix fonts for GF spec

    
================================================================================
TESTS RUN: 26 | PASSED: 20 | FAILED: 6
================================================================================


================================================================================
FAIL: Check copyright string is correct
--------------------------------------------------------------------------------
Copyright does not contain git url.

GF Upstream doc has no git url for family. If the family has been recently added, it may take 5 minutes for the Google Sheet API to update it.


================================================================================
FAIL: Check only Bold and Bold Italic have 'isBold' set
--------------------------------------------------------------------------------
'Flair Bold' instance is not a Bold weight.

Disable "Bold of" for this instance.

Only the 'Bold' and 'Bold Italic instances should have this flag enabled


================================================================================
FAIL: Check instances have the correct name for the GF API
--------------------------------------------------------------------------------
'Flair Light' instance is an invalid name.

The following names are accepted:
- Thin
- ExtraLight
- Light
- Regular
- Medium
- SemiBold
- Bold
- ExtraBold
- Black
- Thin
- ExtraLight
- Light
- Regular
- Medium
- SemiBold
- Bold
- ExtraBold
- Black
- Thin Italic
- ExtraLight Italic
- Light Italic
- Italic
- Medium Italic
- SemiBold Italic
- Bold Italic
- ExtraBold Italic
- Black Italic
- Thin Italic
- ExtraLight Italic
- Light Italic
- Regular Italic
- Medium Italic
- SemiBold Italic
- Bold Italic
- ExtraBold Italic
- Black Italic


================================================================================
FAIL: Check style linking is correct for italic instances
--------------------------------------------------------------------------------
Bold Italic instance must have no style linking.

Delete link to Bold


================================================================================
FAIL: Check style linking is correct for non italic instances
--------------------------------------------------------------------------------
Flair Bold instance must have no style linking. Delete link to Flair Regular


================================================================================
FAIL: Check the family is in GF Upstream document
--------------------------------------------------------------------------------
Family is not listed in the GF Master repo doc, http://tinyurl.com/kflp3k7.

Listing the family helps us keep track of it and ensure there is one original source


End

