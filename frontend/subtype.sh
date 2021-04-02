#!/bin/bash

cssfile="./node_modules/@fortawesome/fontawesome-free/css/all.css"
webfontdir="./node_modules/@fortawesome/fontawesome-free/webfonts"

if ! type fonttools &>/dev/null ; then
    echo "fonttools is not available. Install with:"
    echo "pip3 install fonttools[woff]"
    exit 1
fi

# first, we extract all used fontawesome id names from the html files in templates/ and the typescript files in ts/
# then we look up their glyph code in fontawesome's css file
ids=$(grep -rohE 'fa-[[:alnum:]-]+' ../templates/ ts/ | sort -u | \
	while read id; do \
		grep -A 1 "$id" "$cssfile" | grep -o '"\\.*"' | sed 's/"\\\(.*\)"/\1/'; \
	done | \
	tr '\n' ',')

# create subtyped fonts only containing the used glyphs
for path in "$webfontdir"/fa-brands-*.woff2 "$webfontdir"/fa-solid-*.woff2; do
	file=$(basename $path)
	echo "subsetting $file"
	# we ignore missing glyphs as we use the same glyph set for each font file.
	# since the glyphs are split among different font files, each call will report missing glyphs
	fonttools subset --flavor=woff2 --ignore-missing-glyphs "$path" --unicodes="$ids" --output-file="../static/$file"
done
