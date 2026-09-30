#!/bin/zsh
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
# Build negative-control redline fixtures from three real pairs X, Y, Z (plus the real bad PDF R).
# Reads corpus/word: pools/redlines_en_500_pairs.csv names each Word redline by its sources' full
# ids (base_name, next_name); documents.csv files each source (names) with Word's PDF of it.
# R's redline was rejected from the corpus, so its PDF is copied from this folder's tracked copy.
W=${0:A:h:h:h}/corpus/word; P=$W/pools/redlines_en_500_pairs.csv; F=$1; rm -rf $F; mkdir -p $F/{a,b,redlines,pdfs}
col() { awk -F, -v k=$1 -v n=$2 '$4 "__vs__" $5 == k {print $n; exit}' $P }           # column n of redline k's row
doc() { awk -F, -v id=$1 -v n=$2 '$8 == id {print $n; exit}' $W/documents.csv }        # source id: 4 docx, 5 Word PDF
pairs=($(awk -F, 'NR > 1 {print $4 "__vs__" $5}' $P | grep -E "^(23ba7149bd4f|782587f67411|fd8268639aa3)" | LC_ALL=C sort))
X=$pairs[1]; Y=$pairs[2]; Z=$pairs[3]
R=0217951c5f043355bd62c80e33cbc736f027cec6eb5920cc23a9e66d43983734__vs__08c53c4f6a7731a1dd2b7d06d65d3631cefd5455facfc34fc05256c72fc40046
for s in $X $Y $Z $R; do a=${s%%__vs__*}; b=${s##*__vs__}; cp $W/$(doc $a 4) $F/a/$a.docx; cp $W/$(doc $b 4) $F/b/$b.docx; done
aX=${X%%__vs__*}; bX=${X##*__vs__}; aY=${Y%%__vs__*}; bY=${Y##*__vs__}; aZ=${Z%%__vs__*}; bZ=${Z##*__vs__}
# docx controls
cp $W/$(col $X 6) $F/redlines/${aY}__vs__${bY}.docx                                     # D1 swapped: X's redline under Y's name
cp $W/$(col $Z 6) $F/redlines/${aZ}__vs__${bY}.docx                                     # D2 half: right A (Z), wrong B (Y)
cp $W/$(doc $bX 4) $F/redlines/${aX}__vs__${bX}.docx                                    # D3 leftover: plain B saved as the redline
cp $W/$(doc $aZ 4) $F/redlines/${aZ}__vs__${bZ}.docx                                    # D4 leftover: plain A saved as the redline
# pdf controls
cp $W/$(col $X 7) $F/pdfs/${aY}__vs__${bY}.pdf                                          # P1 swapped
cp $W/$(col $Z 7) $F/pdfs/${aZ}__vs__${bY}.pdf                                          # P2 half
cp $W/$(doc $bX 5) $F/pdfs/${aX}__vs__${bX}.pdf                                         # P3 Word PDF of B only
cp $W/$(doc $aZ 5) $F/pdfs/${aZ}__vs__${bZ}.pdf                                         # P4 Word PDF of A only
cp ${0:A:h}/pdfs/$R.pdf $F/pdfs/                                                        # R  real: Word PDF lacks B's inserted table
echo "X=$X" > $F/pairs.txt; echo "Y=$Y" >> $F/pairs.txt; echo "Z=$Z" >> $F/pairs.txt; echo "R=$R" >> $F/pairs.txt
