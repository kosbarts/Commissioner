#MenuTitle: Decompose Transformed Components (Including Brace/Bracket Layers)
"""TTFautohint doesn't like components which have been flipped"""


bad_components = []
bad_components_ls = []

def check_for_only_one_comp(glyph):
	for thisLayer in glyph.layers:
		for thisComponent in thisLayer.components:
			if sum(thisComponent.scale) != 2.0:
				print glyph
				bad_components.append(glyph)
				bad_components_ls.append(glyph.name)
				return
			elif thisComponent.rotation != 0.0:
				print glyph
				bad_components.append(glyph)
				bad_components_ls.append(glyph.name)
				return

def find_transformed_component_glyphs(font):
	for thisGlyph in font.glyphs:
		check_for_only_one_comp(thisGlyph)					

def main():
	font = Glyphs.font
	find_transformed_component_glyphs(font)
	if not bad_components:
		print "Skipping. No transformed components"
		return
	tabString = "/"+"/".join(bad_components_ls)
	font.newTab(tabString)
	
	
	for thisGlyph in bad_components:
		for thisLayer in thisGlyph.layers:
			print thisLayer
			print "Decomposing transformed %s in %s" % (
				thisGlyph, thisLayer
			)
			thisLayer.decomposeComponents()
			thisLayer.correctPathDirection()

		
if __name__ == "__main__":
	main()
			



