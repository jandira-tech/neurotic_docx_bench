#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""What is a word to Word Compare, in en-US and pt-BR? One controlled edit
per pair inside a fixed sentence; the redline shows the unit Word deletes
and inserts (whole hyphenated word? the digits only? the accent?).

    probe_tokens.py OUT
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_paragraph_probes as lp  # noqa: E402

PT = "O contratante obriga-se a entregar o bem no prazo ajustado, e {X} será considerado para todos os efeitos deste instrumento, salvo disposição em contrário das partes."
EN = "The contractor shall deliver the goods within the agreed period, and {X} shall be considered for all purposes of this instrument unless the parties agree otherwise."

CASES = [
    # pt-BR
    ("pt_hyphen_compound", PT, "o guarda-chuva", "o guarda-sol"),
    ("pt_hyphen_added", PT, "o guarda chuva", "o guarda-chuva"),
    ("pt_mesoclisis", PT, "dar-lhe-ei o valor", "dar-lhe-ia o valor"),
    ("pt_enclisis", PT, "acostumar-se ao prazo", "acostumar-me ao prazo"),
    ("pt_apostrophe", PT, "o pau-d'água", "o pau-d'arco"),
    ("pt_accent_only", PT, "o que ele pôde fazer", "o que ele pode fazer"),
    ("pt_accent_only2", PT, "quem está presente", "quem esta presente"),
    ("pt_cedilla", PT, "a prestação devida", "a prestacao devida"),
    ("pt_case_only", PT, "o senhor contratante", "o Senhor contratante"),
    ("pt_money", PT, "o valor de R$ 1.000,00", "o valor de R$ 2.000,00"),
    ("pt_money_cents", PT, "o valor de R$ 1.000,00", "o valor de R$ 1.000,50"),
    ("pt_money_thousands", PT, "o valor de R$ 1.000.000,00", "o valor de R$ 1.000.001,00"),
    ("pt_section", PT, "o disposto no § 1º", "o disposto no § 2º"),
    ("pt_article", PT, "o disposto no art. 5.º", "o disposto no art. 6.º"),
    ("pt_ordinal_f", PT, "a 1ª parcela", "a 2ª parcela"),
    ("pt_date", PT, "a data de 03/10/2026", "a data de 04/10/2026"),
    ("pt_date_month", PT, "a data de 03/10/2026", "a data de 03/11/2026"),
    ("pt_percent", PT, "a taxa de 10%", "a taxa de 15%"),
    ("pt_nbsp_money", PT, "o valor de R$ 1.000,00", "o valor de R$ 2.000,00"),
    ("pt_quotes", PT, "o termo “contratante”", "o termo “contratado”"),
    ("pt_parenthesis", PT, "o item (a) do anexo", "o item (b) do anexo"),
    ("pt_roman", PT, "o inciso III do artigo", "o inciso IV do artigo"),
    ("pt_abbrev", PT, "o Sr. contratante", "o Dr. contratante"),
    ("pt_plural", PT, "o prazo ajustado", "os prazos ajustados"),
    ("pt_ellipsis", PT, "o prazo… ajustado", "o prazo ajustado"),
    ("pt_double_space", PT, "o prazo  ajustado", "o prazo ajustado"),
    # en-US
    ("en_contraction", EN, "it doesn't apply", "it didn't apply"),
    ("en_hyphen_compound", EN, "a non-exclusive license", "a non-transferable license"),
    ("en_hyphen_removed", EN, "a co-operative scheme", "a cooperative scheme"),
    ("en_email_hyphen", EN, "an e-mail notice", "an email notice"),
    ("en_money", EN, "the sum of $1,000.00", "the sum of $2,000.00"),
    ("en_money_cents", EN, "the sum of $1,000.00", "the sum of $1,000.50"),
    ("en_citation", EN, "under 15 U.S.C. 1601", "under 15 U.S.C. 1602"),
    ("en_citation_code", EN, "under 15 U.S.C. 1601", "under 15 C.F.R. 1601"),
    ("en_section_ref", EN, "under Section 1(a)(2)", "under Section 1(a)(3)"),
    ("en_endash_range", EN, "the years 2019–2020", "the years 2019–2021"),
    ("en_smart_quotes", EN, "the term “Contractor”", "the term “Consultant”"),
    ("en_case_only", EN, "the contractor", "the Contractor"),
    ("en_percent", EN, "a rate of 10%", "a rate of 15%"),
    ("en_date", EN, "the date of 10/03/2026", "the date of 10/04/2026"),
    ("en_apostrophe_poss", EN, "the Contractor's goods", "the Contractor’s goods"),
    ("en_plural", EN, "the agreed period", "the agreed periods"),
    ("en_ellipsis", EN, "the period… agreed", "the period agreed"),
    ("en_nbsp", EN, "the sum of $ 1,000", "the sum of $ 2,000"),
    ("en_slash", EN, "the buyer/seller", "the buyer/lessee"),
    ("en_number_word", EN, "within thirty (30) days", "within sixty (60) days"),
    ("en_number_only", EN, "within thirty (30) days", "within thirty (60) days"),
]


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/tokens")
    rows = []
    for name, frame, x_a, x_b in CASES:
        lp.docx(out / "A" / f"{name}.docx", [lp.para(frame.replace("{X}", x_a))])
        lp.docx(out / "B" / f"{name}.docx", [lp.para(frame.replace("{X}", x_b))])
        rows.append({"name": name, "a": x_a, "b": x_b})
    with (out / "manifest.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["name", "a", "b"]); wr.writeheader(); wr.writerows(rows)
    print(f"{len(rows)} pairs under {out}")


if __name__ == "__main__":
    main()
