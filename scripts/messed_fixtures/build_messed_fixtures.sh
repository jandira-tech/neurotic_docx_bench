#!/bin/zsh
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
# Build negative-control redline fixtures from three real pairs X, Y, Z (plus the real bad PDF R).
G=/Users/arthrod/temp/T/neurotic_docx_bench/grok_run; F=$1; rm -rf $F; mkdir -p $F/{a,b,redlines,pdfs}
pairs=($(ls $G/500_extra_docx_redlines | grep -E "^(23ba7149bd4f|782587f67411|fd8268639aa3)" | sed 's/\.docx$//'))
X=$pairs[1]; Y=$pairs[2]; Z=$pairs[3]
R=0217951c5f043355bd62c80e33cbc736f027cec6eb5920cc23a9e66d43983734__vs__08c53c4f6a7731a1dd2b7d06d65d3631cefd5455facfc34fc05256c72fc40046
for s in $X $Y $Z $R; do cp $G/500_docx_part_a_original/${s%%__vs__*}.docx $F/a/; cp $G/500_docx_part_b_original/${s##*__vs__}.docx $F/b/; done
aX=${X%%__vs__*}; bX=${X##*__vs__}; aY=${Y%%__vs__*}; bY=${Y##*__vs__}; aZ=${Z%%__vs__*}; bZ=${Z##*__vs__}
# docx controls
cp $G/500_extra_docx_redlines/$X.docx $F/redlines/${aY}__vs__${bY}.docx                 # D1 swapped: X's redline under Y's name
cp $G/500_extra_docx_redlines/$Z.docx $F/redlines/${aZ}__vs__${bY}.docx                 # D2 half: right A (Z), wrong B (Y)
cp $G/500_docx_part_b_original/$bX.docx $F/redlines/${aX}__vs__${bX}.docx               # D3 leftover: plain B saved as the redline
cp $G/500_docx_part_a_original/$aZ.docx $F/redlines/${aZ}__vs__${bZ}.docx               # D4 leftover: plain A saved as the redline
# pdf controls
cp $G/500_extra_pdf_redlines/$X.pdf $F/pdfs/${aY}__vs__${bY}.pdf                        # P1 swapped
cp $G/500_extra_pdf_redlines/$Z.pdf $F/pdfs/${aZ}__vs__${bY}.pdf                        # P2 half
cp $G/500_pdf_part_b_original/$bX.pdf $F/pdfs/${aX}__vs__${bX}.pdf                      # P3 Word PDF of B only
cp $G/500_pdf_part_a_original/$aZ.pdf $F/pdfs/${aZ}__vs__${bZ}.pdf                      # P4 Word PDF of A only
cp $G/500_extra_pdf_redlines/$R.pdf $F/pdfs/                                            # R  real: Word PDF lacks B's inserted table
echo "X=$X" > $F/pairs.txt; echo "Y=$Y" >> $F/pairs.txt; echo "Z=$Z" >> $F/pairs.txt; echo "R=$R" >> $F/pairs.txt
