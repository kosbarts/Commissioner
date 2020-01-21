# Check if any otfs and ttfs have usWeightClass values of 100 and 200 
# and changes them to 250 and 275 consecutively.
# Files are overwritten. 
# Based on Ben Kiel's setUseTypoMetricsFalse script:
# https://github.com/Typefounding/setUseTypoMetricsFalse

import sys
import os 
import os.path
from fontTools.ttLib import TTFont

# Helper to find files
def getFiles(path, extension):
    if not extension.startswith('.'):
        extension = '.' + extension
    if extension == '.ufo':
        return [dir for (dir, dirs, files) in os.walk(path) if dir[-len(extension):] == extension]
    else:
        return [os.sep.join((dir, file)) for (dir, dirs, files) in os.walk(path) for file in files if file[-len(extension):] == extension]

def fixusWeightClass(fontPath):
    # Get Font object from path
    font = TTFont(fontPath)

    # Get the OS/2 Table
    os2 = font["OS/2"]
	
    # Get the WeightClass
    wght = os2.usWeightClass
    

    # Check if Thin
    if wght == 100:
        
        # Set to 250
        os2.usWeightClass = 250
		
    # Check if UltraLight	
    elif wght == 200:
		
        # Set to 275
        os2.usWeightClass = 275
        
        # Save font
        font.save(fontPath)
    else:
        print (fontPath + " Nothing to fix.")
    

def main():
       
    # Get to work
    print ("Setting OS/2.usWeightClass 100 = 250, 200 = 275")
    print ("-----------------------------------------------")
    print ("Working from:")
    print (os.getcwd())
    files = getFiles(os.getcwd(), 'otf')
    files += getFiles(os.getcwd(), 'ttf')
    print ("Found these fonts to fix:")
    print (files)
    for file in files:
        print ("Fixing: " + file)
        fixusWeightClass(file)
    print ("---------------------------------")
    print ("Done.")

if __name__ == "__main__":
    main()