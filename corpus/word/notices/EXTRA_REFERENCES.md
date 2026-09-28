# Extra Word references (build 16.114.26092233)

Word 16.114.26092111 made the 500 `<stem>.pdf` references on 2026-09-22. Microsoft AutoUpdate
installed 16.114.26092233 on 2026-09-24. A full re-render on 2026-09-25 (scripts/word_pdf.py, all 500,
same order) matched 482 references pixel for pixel (Jaccard >= 0.999). The other 18 differ, so their
new rendering is kept here as `<stem>.w26092233.pdf` beside the original. There are now 518 references.

| stem | Jaccard(old, new) |
|---|---|
| 0003fc93d088dc4c17f3eabc859086df5cdac48fc1106b6ea00d9776ea1eb35c | 0.074 |
| 0008eb8e63b7adff0d83f57644e9d7b3350ac05573e1d5e2dbb1bd1e2a799b24 | 0.987 |
| 000f3ee18b59fcb52f501b631315ae0d47489ee92f927b93469ce7266a2675b5 | 0.996 |
| 0012056ac9d4f46088b4ec6bb97b3a30a5f83e2a78a2de80fd82613ad8b021e2 | 0.983 |
| 001a86cd1e2a3ac48649f16db47fecd7576c530e0aa14d147a8133ad22057cae | 0.050 |
| 001d945ab84c573a4f083849620e16c3fe9acd416914f6f32a4d9112226e7414 | 0.995 |
| 002adf0715eed4d213774c26c60c78624c2a3cbb3d0397d257cb13f4410eca16 | 0.176 |
| 003ce553462860bc9d46b3e45209f66841c599e18ba366273d983e49c77946d6 | 0.738 |
| 0043183a08c25bef0d272c66acb2e3af5aa09b206e4544570c3f01b52ade772a | 0.918 |
| 004599833e81f0e72deb9f04ed6c29b659db22561f65fe35c38e91e32f7a430c | 0.136 |
| 008469e72716471f0a90687366bac1bed5d63ae8b5022a5a56589e0a9ee89b49 | 0.999 |
| 008726f798d340e8a479f1f488a0aee583923c4aaf29b0391c272168c8fcac45 | 0.998 |
| 00ac06fef95cc36c8559ec486c7822d97e29002456b38066e32d2e3da185c6ac | 0.096 |
| 00afb3e6b2bb1a5ab1e1770ba41f6f455f87472d24ab27678625f16ff15ef9af | 0.976 |
| 014b42f2b871a56421fcacd3fab65aa3f69a6c5332eee715a5afa5396a851eff | 0.151 |
| 015e4665fb2bcc025f24e7b451197933975b68ae37052ca7c9401294079c648d | 0.034 |
| 01870f7ea5cec263713c811d8938a05f1730d362aad060f61017d519c91e938d | 0.975 |
| 0199027cbf967c88ab833b77e5bc5d629bacecbd40a87c26bfc50b25de90c106 | 0.982 |

## Outdated originals (2026-09-25)

Each of the 18 stems above had its original Sep 22 reference renamed to `<stem>.outdated.pdf`, because Word build 16.114.26092233 no longer reproduces it.
- Scoring still counts these files exactly as before: the scorers fall back to the `.outdated` name.
- Gap hunting (worst-first) must not use them. It uses the `<stem>.w26092233.pdf` references instead.
