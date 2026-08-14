# Benchmark results

Source: `results/bench.jsonl` — **153** fidelity row(s) (one per vendor×benchmark×**version**; 131 distinct vendor×version pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).

Scores are 0–100 (higher = closer to the Microsoft Word oracle). Cross-renderer comparisons (LibreOffice vs Playwright) are **not** directly comparable — only compare within the same benchmark. Different **versions** of the same vendor are kept so you can compare pins (e.g. docxodus 6.4.0 vs 7.0.0).

## Rankings by benchmark

### `script_redlines`

script_redlines (LibreOffice render vs Word oracle)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 84.4662 | 92.6623 | 84.4662 | 92.6623 | 93.199 | 0 | 763 | 763 | 197 | 419 | 29 |
| 2 | jubarte-rust | jubarte-rust@cacb0b9bcb34+git.fc8c50f879974568278bcd33c476b153229313f0 | 84.4006 | 92.6088 | 84.4006 | 92.6088 | 93.199 | 0 | 763 | 763 | 196 | 418 | 30 |
| 3 | jubarte-rust | jubarte-rust@5c5581a12812+git.fc8c50f879974568278bcd33c476b153229313f0 | 84.0909 | 92.3803 | 84.0909 | 92.3803 | 93.199 | 0 | 763 | 763 | 196 | 414 | 34 |
| 4 | jubarte-rust | jubarte-rust@285b7cf3881f+git.fc8c50f879974568278bcd33c476b153229313f0 | 84.1766 | 92.2881 | 84.1766 | 92.2881 | 93.199 | 0 | 763 | 763 | 193 | 414 | 32 |
| 5 | jubarte-rust | jubarte-rust@7db1bf4110af+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.7766 | 92.1381 | 83.7766 | 92.1381 | 93.199 | 0 | 763 | 763 | 192 | 410 | 39 |
| 6 | jubarte-rust | jubarte-rust@bb2bc6195c45+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.7766 | 92.1381 | 83.7766 | 92.1381 | 93.199 | 0 | 763 | 763 | 192 | 410 | 39 |
| 7 | jubarte-rust | jubarte-rust@bf3c7b4b7e4b+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.6643 | 92.0187 | 83.6643 | 92.0187 | 93.199 | 0 | 763 | 763 | 192 | 407 | 38 |
| 8 | jubarte-rust | jubarte-rust@9020ef223997+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.3891 | 91.6687 | 83.3891 | 91.6687 | 93.199 | 0 | 763 | 763 | 187 | 403 | 39 |
| 9 | jubarte-rust | jubarte-rust@ac0e3a61d563+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.2656 | 91.6687 | 83.2656 | 91.6687 | 93.199 | 0 | 763 | 763 | 183 | 403 | 41 |
| 10 | jubarte-rust | jubarte-rust@3f6f9f41efbf+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.2518 | 91.5868 | 83.2518 | 91.5868 | 93.199 | 0 | 763 | 763 | 187 | 401 | 39 |
| 11 | jubarte-rust | jubarte-rust@d3a1b10c4408+git.fc8c50f879974568278bcd33c476b153229313f0 | 83.1221 | 91.5114 | 83.1221 | 91.5114 | 93.8933 | 0 | 763 | 763 | 149 | 401 | 41 |
| 12 | docxodus | 9.8.0 | 80.5534 | 91.1892 | 80.2367 | 91.108 | 100 | 4 | 760 | 763 | 186 | 392 | 95 |
| 13 | jubarte-rust | jubarte-rust@6923ca0b2b8e+git.fc8c50f879974568278bcd33c476b153229313f0 | 82.1163 | 90.3458 | 82.1163 | 90.3458 | 93.8933 | 0 | 763 | 763 | 147 | 386 | 46 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.0.0 | 80.5535 | 91.1892 | 80.2368 | 91.108 | 100 | 4 | 760 | 763 | 186 | 392 | 95 |
| 2 | jubarte-rust | jubarte-rust@4a6065089e4d+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.4063 | 88.7331 | 81.4063 | 88.7331 | 93.199 | 0 | 763 | 763 | 193 | 368 | 49 |
| 3 | jubarte-rust | jubarte-rust@eb34d99e486c+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.3959 | 88.7331 | 81.3959 | 88.7331 | 93.199 | 0 | 763 | 763 | 193 | 367 | 49 |
| 4 | jubarte-rust | jubarte-rust@3af52d7e2153+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.3835 | 88.6893 | 81.3835 | 88.6893 | 93.199 | 0 | 763 | 763 | 193 | 367 | 49 |
| 5 | jubarte-rust | jubarte-rust@1b9081666e72+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.3463 | 88.6893 | 81.3463 | 88.6893 | 90.1215 | 0 | 763 | 763 | 193 | 365 | 49 |
| 6 | jubarte-rust | jubarte-rust@9b88994c2a01+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.3659 | 88.6089 | 81.3659 | 88.6089 | 90.1215 | 0 | 763 | 763 | 194 | 367 | 49 |
| 7 | jubarte | jubarte-final@a58157a9cd2d | 81.4686 | 88.5972 | 81.4686 | 88.5972 | 79.25 | 0 | 763 | 763 | 202 | 369 | 65 |
| 8 | jubarte | jubarte-final@138300e8471d | 81.4564 | 88.5972 | 81.4564 | 88.5972 | 79.25 | 0 | 763 | 763 | 202 | 368 | 65 |
| 9 | jubarte | jubarte-final@300cc3edf753 | 81.4515 | 88.5972 | 81.4515 | 88.5972 | 79.25 | 0 | 763 | 763 | 202 | 368 | 65 |
| 10 | jubarte | jubarte-final@a6caf6b44537 | 81.4453 | 88.5972 | 81.4453 | 88.5972 | 79.25 | 0 | 763 | 763 | 199 | 368 | 65 |
| 11 | jubarte | jubarte-final@7ef64a75db56 | 81.4371 | 88.5972 | 81.4371 | 88.5972 | 79.25 | 0 | 763 | 763 | 201 | 367 | 65 |
| 12 | jubarte | 0.1.0@0676fa9064f1 | 81.3788 | 88.5165 | 81.3788 | 88.5165 | 79.25 | 0 | 763 | 763 | 201 | 366 | 66 |
| 13 | jubarte-rust | jubarte-rust@7ee5daea8fb9+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.3062 | 88.5165 | 81.3062 | 88.5165 | 89.746 | 0 | 763 | 763 | 191 | 366 | 49 |
| 14 | jubarte-rust | jubarte-rust@1ac8d72aa73a+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.2996 | 88.5165 | 81.2996 | 88.5165 | 88.9724 | 0 | 763 | 763 | 187 | 364 | 49 |
| 15 | jubarte-rust | jubarte-rust@f48dcacc7478+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.2961 | 88.5165 | 81.2961 | 88.5165 | 89.746 | 0 | 763 | 763 | 191 | 366 | 49 |
| 16 | jubarte | jubarte-final@38e6f956cb44 | 81.4165 | 88.5119 | 81.4165 | 88.5119 | 79.25 | 0 | 763 | 763 | 202 | 367 | 66 |
| 17 | jubarte-rust | jubarte-rust@076ef86b4e40+git.fc8c50f879974568278bcd33c476b153229313f0 | 81.2339 | 88.4278 | 81.2339 | 88.4278 | 89.6361 | 0 | 763 | 763 | 191 | 363 | 49 |
| 18 | jubarte-rust | jubarte-rust@b79584ee185e+git.7ff6c38606a1595e80a4600d81603640fbacd472 | 81.2453 | 88.3311 | 81.2453 | 88.3311 | 89.6361 | 0 | 763 | 763 | 187 | 364 | 49 |
| 19 | jubarte-rust | jubarte-rust@f3609460e82a+git.3e1883881eef64647a81dabe858a137e60026a3a | 81.1322 | 88.182 | 81.1322 | 88.182 | 89.0123 | 0 | 763 | 763 | 184 | 362 | 50 |
| 20 | jubarte-rust | jubarte-rust@9f4892c93e04+git.a6d5890 | 81.1095 | 88.182 | 81.1095 | 88.182 | 89.0123 | 0 | 763 | 763 | 184 | 363 | 49 |
| 21 | jubarte-rust | jubarte-rust@59b02c068a09+git.0fcae65 | 81.1719 | 88.1561 | 81.1719 | 88.1561 | 89.0123 | 0 | 763 | 763 | 184 | 363 | 49 |
| 22 | jubarte-rust | jubarte-rust@5d0e047c4d1e+git.963b8e2 | 81.1275 | 88.1561 | 81.1275 | 88.1561 | 89.0123 | 0 | 763 | 763 | 184 | 363 | 49 |
| 23 | jubarte-rust | jubarte-rust@6691bea93ef4+git.a0281fc | 81.1268 | 88.1561 | 81.1268 | 88.1561 | 89.0123 | 0 | 763 | 763 | 185 | 363 | 49 |
| 24 | jubarte-rust | jubarte-rust@d434447d27ce+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73 | 80.9224 | 86.7269 | 80.9224 | 86.7269 | 89.0123 | 0 | 763 | 763 | 182 | 358 | 49 |
| 25 | jubarte | jubarte-final@88c1b1c36479 | 80.5701 | 86.6639 | 80.5701 | 86.6639 | 74.1998 | 0 | 763 | 763 | 197 | 346 | 69 |
| 26 | jubarte | jubarte-final@6f48fe914d9a+git.d44dc07498de8ef7560e45ca7efcc3340f0b778e | 80.6024 | 86.6013 | 80.6024 | 86.6013 | 74.1998 | 0 | 763 | 763 | 201 | 347 | 69 |
| 27 | jubarte-rust | jubarte-rust@49d62ef4590b+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73 | 80.7925 | 86.452 | 80.7925 | 86.452 | 89.0123 | 0 | 763 | 763 | 181 | 355 | 49 |
| 28 | jubarte-rust | jubarte-rust@52cac2981586+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73 | 80.7045 | 86.4366 | 80.7045 | 86.4366 | 89.0123 | 0 | 763 | 763 | 181 | 354 | 49 |
| 29 | jubarte | jubarte-final@43a6633fd17e+git.a9e4a33ac250293c547fe878ebb81068deebaeb6 | 80.3604 | 86.4243 | 80.3604 | 86.4243 | 74.1998 | 0 | 763 | 763 | 188 | 343 | 70 |
| 30 | jubarte-rust | jubarte-rust@d100650f7be0+git.17afecafc3deb2b99c4577cbd0fbf6a0e6356daf | 80.5789 | 86.1607 | 80.5789 | 86.1607 | 89.0123 | 0 | 763 | 763 | 180 | 353 | 50 |
| 31 | jubarte-rust | jubarte-rust@50fd692d367f+git.e2cf3556ddbdfb115161c47529e36f20ca3c233a | 80.5658 | 86.1607 | 80.5658 | 86.1607 | 89.0123 | 0 | 763 | 763 | 180 | 353 | 51 |
| 32 | jubarte-rust | jubarte-rust@9b85d42d42e1+git.84bb80216132b6f249de1455dba9b6092664ecea | 80.5154 | 86.0126 | 80.5154 | 86.0126 | 89.0123 | 0 | 763 | 763 | 180 | 353 | 52 |
| 33 | jubarte-rust | jubarte-rust@a46fb002a1a8+git.970a113dde4b71de07ccdda4a67cd2cbc68bdcc1 | 80.4136 | 86.0123 | 80.4136 | 86.0123 | 89.0123 | 0 | 763 | 763 | 180 | 352 | 54 |
| 34 | jubarte | jubarte-final@066e56f0970b | 80.3036 | 85.9573 | 80.3036 | 85.9573 | 71.7327 | 0 | 763 | 763 | 199 | 344 | 69 |
| 35 | jubarte-rust | jubarte-rust@60fe4f2fb0cd+git.ebf1a79 | 79.4668 | 85.9057 | 79.4668 | 85.9057 | 89.1943 | 0 | 763 | 763 | 173 | 351 | 71 |
| 36 | jubarte-rust | jubarte-rust@656ba15ca16e+git.ebf1a79 | 79.4873 | 85.3205 | 79.4873 | 85.3205 | 89.1943 | 0 | 763 | 763 | 173 | 350 | 70 |
| 37 | jubarte-rust | jubarte-rust@9854c9e68ddd+git.9d46888 | 80.0835 | 85.1649 | 80.0835 | 85.1649 | 89.0123 | 0 | 763 | 763 | 179 | 347 | 55 |
| 38 | jubarte-rust | jubarte-rust@97da13af151c+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.581 | 84.8888 | 79.581 | 84.8888 | 89.6361 | 0 | 763 | 763 | 182 | 344 | 72 |
| 39 | jubarte-rust | jubarte-rust@8047e6cb5052+git.fddb30f | 80.0073 | 84.8864 | 80.0073 | 84.8864 | 88.4951 | 0 | 763 | 763 | 176 | 343 | 56 |
| 40 | jubarte-rust | jubarte-rust@9ba60702c118+git.e3bc6b6 | 79.6418 | 84.8864 | 79.6418 | 84.8864 | 89.0123 | 0 | 763 | 763 | 178 | 344 | 70 |
| 41 | jubarte-rust | jubarte-rust@279e58418eaa+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.5678 | 84.8864 | 79.5678 | 84.8864 | 89.1943 | 0 | 763 | 763 | 182 | 344 | 72 |
| 42 | jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.5678 | 84.8864 | 79.5678 | 84.8864 | 89.1943 | 0 | 763 | 763 | 182 | 344 | 72 |
| 43 | jubarte-rust | jubarte-rust@ba4cfc3ecc67+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.5621 | 84.8864 | 79.5621 | 84.8864 | 89.1943 | 0 | 763 | 763 | 182 | 344 | 72 |
| 44 | jubarte-wasm | 0.1.0@e1e19c982338+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.5621 | 84.8864 | 79.5621 | 84.8864 | 89.1943 | 0 | 763 | 763 | 182 | 344 | 72 |
| 45 | jubarte-rust | jubarte-rust@bea5f183c4c5+git.f6959f8 | 79.5396 | 84.8864 | 79.5396 | 84.8864 | 89.0123 | 0 | 763 | 763 | 178 | 344 | 71 |
| 46 | jubarte-rust | jubarte-rust@e0fe28e5b256+git.2351844 | 79.4635 | 84.8864 | 79.4635 | 84.8864 | 89.0123 | 0 | 763 | 763 | 178 | 343 | 71 |
| 47 | jubarte-rust | jubarte-rust@f86091a180ce+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.4635 | 84.8864 | 79.4635 | 84.8864 | 89.0123 | 0 | 763 | 763 | 178 | 343 | 71 |
| 48 | jubarte-wasm | 0.1.0@18f6c9fd87db+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.4635 | 84.8864 | 79.4635 | 84.8864 | 89.0123 | 0 | 763 | 763 | 178 | 343 | 71 |
| 49 | jubarte-rust | jubarte-rust@94ac5db42c3b+git.196d97e | 80.0099 | 84.5408 | 80.0099 | 84.5408 | 89.0123 | 0 | 763 | 763 | 179 | 346 | 54 |
| 50 | jubarte-rust | jubarte-rust@8dea7e733d6d+git.ec66729 | 79.9416 | 84.5408 | 79.9416 | 84.5408 | 88.4951 | 0 | 763 | 763 | 178 | 343 | 57 |
| 51 | jubarte-rust | jubarte-rust@36224f1d081b+git.27c8c00 | 79.7128 | 84.4626 | 79.7128 | 84.4626 | 88.4951 | 0 | 763 | 763 | 176 | 343 | 60 |
| 52 | jubarte-rust | jubarte-rust@0e0a602dab95+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.4838 | 84.4626 | 79.4838 | 84.4626 | 87.8941 | 0 | 763 | 763 | 179 | 340 | 72 |
| 53 | jubarte-rust | jubarte-rust@5d8d1ac7be6e+git.a3c8d40 | 79.7484 | 84.3155 | 79.7484 | 84.3155 | 88.4951 | 0 | 763 | 763 | 173 | 341 | 55 |
| 54 | jubarte-rust | jubarte-rust@66c3c793a724+git.059808d | 79.2188 | 84.222 | 79.2188 | 84.222 | 89.0123 | 0 | 763 | 763 | 177 | 339 | 71 |
| 55 | jubarte-rust | jubarte-rust@7837955c0955+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.0459 | 83.5854 | 79.0459 | 83.5854 | 89.0123 | 0 | 763 | 763 | 175 | 334 | 71 |
| 56 | jubarte-rust | jubarte-rust@39fcb0806e4c+git.0f39b64e69b54a04828d78e73d071d0949dee73c | 78.8943 | 83.5854 | 78.8943 | 83.5854 | 89.1943 | 0 | 763 | 763 | 176 | 337 | 75 |
| 57 | jubarte-wasm | 0.1.0@a795fa73ea5f+git.0f39b64e69b54a04828d78e73d071d0949dee73c | 78.8943 | 83.5854 | 78.8943 | 83.5854 | 89.1943 | 0 | 763 | 763 | 176 | 337 | 75 |
| 58 | jubarte | jubarte-final@389db881b0bf+git.07bd8ba2113c65fdb2fe4d4ab965060337f0a8e7 | 79.1927 | 83.2251 | 79.1927 | 83.2251 | 63.4649 | 0 | 763 | 763 | 174 | 323 | 74 |
| 59 | jubarte-rust | jubarte-rust@367ee1c460ed+git.0ab0e1c | 79.3289 | 82.9931 | 79.3289 | 82.9931 | 84.575 | 0 | 763 | 763 | 171 | 334 | 63 |
| 60 | jubarte-rust | jubarte-rust@5d704d24d79a+git.f91341b25e532ef7ff0a4ecb14e015a771f94c9f | 79.4531 | 82.7618 | 79.4531 | 82.7618 | 84.9356 | 0 | 763 | 763 | 166 | 336 | 57 |
| 61 | jubarte-rust | jubarte-rust@38a1d9d3004f+git.eb5b8fe | 78.8714 | 82.3032 | 78.8714 | 82.3032 | 88.9386 | 0 | 763 | 763 | 166 | 329 | 69 |
| 62 | jubarte-rust | jubarte-rust@d2de8e147655+git.b910a23bce9b63a393ac6186ab366a39d6aaa504 | 78.0451 | 81.8707 | 78.0451 | 81.8707 | 88.0561 | 0 | 763 | 763 | 165 | 321 | 82 |
| 63 | jubarte-wasm | 0.1.0@2957178cc645+git.b910a23bce9b63a393ac6186ab366a39d6aaa504 | 78.0451 | 81.8707 | 78.0451 | 81.8707 | 88.0561 | 0 | 763 | 763 | 165 | 321 | 82 |
| 64 | jubarte-wasm | 0.1.0@b13bcb128725+git.bae2df5748e5bce5a3873056a895cbe769285c74 | 77.9702 | 81.8301 | 77.9702 | 81.8301 | 88.0561 | 0 | 763 | 763 | 163 | 320 | 83 |
| 65 | jubarte-rust | jubarte-rust@747fdf8585a7+git.bae2df5748e5bce5a3873056a895cbe769285c74 | 77.9701 | 81.8301 | 77.9701 | 81.8301 | 88.0561 | 0 | 763 | 763 | 163 | 320 | 83 |
| 66 | jubarte-rust | jubarte-rust@667241eebe86+git.0e2923194145ea254ea617b9a99fb60ea9b1d431 | 77.9237 | 81.8301 | 77.9237 | 81.8301 | 87.9395 | 0 | 763 | 763 | 161 | 318 | 83 |
| 67 | jubarte-wasm | 0.1.0@d3810de5aa53+git.0e2923194145ea254ea617b9a99fb60ea9b1d431 | 77.9237 | 81.8301 | 77.9237 | 81.8301 | 87.9395 | 0 | 763 | 763 | 161 | 318 | 83 |
| 68 | jubarte-rust | jubarte-rust@bf7bb2748045+git.8cd638d6f0cdb261c55150c056af9cf44fa332a6 | 77.7516 | 81.4705 | 77.7516 | 81.4705 | 87.9395 | 0 | 763 | 763 | 161 | 317 | 86 |
| 69 | jubarte-wasm | 0.1.0@1331a4ff7c61+git.8cd638d6f0cdb261c55150c056af9cf44fa332a6 | 77.7516 | 81.4705 | 77.7516 | 81.4705 | 87.9395 | 0 | 763 | 763 | 161 | 317 | 86 |
| 70 | jubarte-rust | jubarte-rust@74bbefc415c4+git.6817a28378372d6e7c95227cf300889e74ab06e4 | 77.6944 | 81.4434 | 77.6944 | 81.4434 | 87.9395 | 0 | 763 | 763 | 161 | 316 | 86 |
| 71 | jubarte-wasm | 0.1.0@dc46d94d88ab+git.6817a28378372d6e7c95227cf300889e74ab06e4 | 77.6944 | 81.4434 | 77.6944 | 81.4434 | 87.9395 | 0 | 763 | 763 | 161 | 316 | 86 |
| 72 | jubarte-rust | jubarte-rust@736e49cff080+git.24b182f5824aaf9acdd3a0c00e9bf88b22b6fde9 | 77.555 | 81.1624 | 77.555 | 81.1624 | 86.1884 | 0 | 763 | 763 | 160 | 315 | 89 |
| 73 | jubarte-wasm | 0.1.0@d5f48a35f21a+git.24b182f5824aaf9acdd3a0c00e9bf88b22b6fde9 | 77.555 | 81.1624 | 77.555 | 81.1624 | 86.1884 | 0 | 763 | 763 | 160 | 315 | 89 |
| 74 | jubarte-rust | jubarte-rust@b9d4740f3529+git.ebf1a79 | 78.0735 | 81.1332 | 78.0735 | 81.1332 | 88.0561 | 0 | 763 | 763 | 163 | 329 | 85 |
| 75 | jubarte-rust | jubarte-rust@644fa2c1c30a+git.d619d40 | 78.6064 | 81.1185 | 78.6064 | 81.1185 | 79.5577 | 0 | 763 | 763 | 149 | 313 | 63 |
| 76 | jubarte | jubarte-final@7f6d70bdc3ce+git.b29cc0ab4efac5b6c25ad1fe0b08cbc2a8157970 | 78.1105 | 80.9583 | 78.1105 | 80.9583 | 60.2398 | 0 | 763 | 763 | 158 | 297 | 76 |
| 77 | jubarte | jubarte-final@77e68faebcda+git.b76f204f67549088bcdda1f961bf47f8bf8116e5 | 77.9828 | 80.6738 | 77.9828 | 80.6738 | 55.3087 | 0 | 763 | 763 | 154 | 295 | 76 |
| 78 | jubarte-rust | jubarte-rust@992b5db46add+git.09545197c99f7b21583e53cb6e2b220b50d295ac | 77.3357 | 80.4932 | 77.3357 | 80.4932 | 86.1884 | 0 | 763 | 763 | 159 | 312 | 88 |
| 79 | jubarte | jubarte-final@041a9bd0cbc3+git.8f8ea75949175abde9b7700308190a3dcd3508ab | 77.7654 | 79.9837 | 77.7654 | 79.9837 | 54.1655 | 0 | 763 | 763 | 152 | 293 | 76 |
| 80 | jubarte-rust | jubarte-rust@8a1e896365b3+git.1be1fcd060ce0d8e2a1b0f91df618d8ec651e3ba | 76.7112 | 78.971 | 76.7112 | 78.971 | 86.1884 | 0 | 763 | 763 | 158 | 309 | 101 |
| 81 | jubarte-wasm | 0.1.0 | 76.6806 | 78.8046 | 76.5801 | 78.6382 | 86.0616 | 1 | 762 | 763 | 157 | 308 | 101 |
| 82 | jubarte | jubarte-final@6db0dcdb2f1a+git.d99ccb5b3adda605e5304200ad88c1aff7fe53c2 | 77.0151 | 78.5311 | 77.0151 | 78.5311 | 53.0737 | 0 | 763 | 763 | 142 | 277 | 80 |
| 83 | jubarte | jubarte-final@d43557e042c1 | 77.0151 | 78.5311 | 77.0151 | 78.5311 | 53.0737 | 0 | 763 | 763 | 142 | 277 | 80 |
| 84 | jubarte-rust | jubarte-rust@fcea02da49f4 | 76.2072 | 77.9542 | 76.2072 | 77.9542 | 86.1884 | 0 | 763 | 763 | 158 | 307 | 108 |
| 85 | jubarte-ast | jubarte-final@138300e8471d | 74.1963 | 76.1486 | 74.1963 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 86 | jubarte-ast | jubarte-final@300cc3edf753 | 74.1963 | 76.1486 | 74.1963 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 87 | jubarte-ast | jubarte-final@38e6f956cb44 | 74.1963 | 76.1486 | 74.1963 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 88 | jubarte-ast | jubarte-final@7ef64a75db56 | 74.1963 | 76.1486 | 74.1963 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 89 | jubarte-ast | jubarte-final@88c1b1c36479 | 74.1963 | 76.1486 | 74.1963 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 90 | jubarte-ast | jubarte-final@a6caf6b44537 | 74.1963 | 76.1486 | 74.1963 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 91 | jubarte-ast | 0.1.0@0676fa9064f1 | 74.1962 | 76.1486 | 74.1962 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 92 | jubarte-ast | jubarte-final@a58157a9cd2d | 74.1962 | 76.1486 | 74.1962 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 93 | jubarte-ast | jubarte-final@d294713913bb+git.b256b039d54561800b4462fb67cfcd5a8143f606 | 74.4501 | 76.7449 | 73.572 | 76.1486 | 75.0483 | 10 | 754 | 763 | 96 | 234 | 112 |
| 94 | jubarte-rust | jubarte-rust@9457b6549b5d+git.ebf1a79 | 76.3953 | 76.0408 | 76.3953 | 76.0408 | 74.1998 | 0 | 763 | 763 | 144 | 301 | 90 |
| 95 | jubarte-ast | jubarte-final@0a703664346d+git.50155bfba69385bf0e99dd3a19b15da1f58e104c | 73.8663 | 75.8715 | 72.995 | 75.1212 | 75.0483 | 10 | 754 | 763 | 96 | 233 | 124 |
| 96 | jubarte-ast | jubarte-final@c043b0aaefb3+git.19b5f14c6088a71280786a864d45cac3aa6e7c92 | 73.8663 | 75.8715 | 72.995 | 75.1212 | 75.0483 | 10 | 754 | 763 | 96 | 233 | 124 |
| 97 | jubarte-ast | jubarte-final@6e7229a4d930+git.6f9f76fcd961c9ace7fce9941307b712ada01282 | 73.4588 | 74.2932 | 72.5923 | 73.7072 | 75.0483 | 10 | 754 | 763 | 91 | 229 | 126 |
| 98 | jubarte-ast | jubarte-final@dc06c68fa885+git.1cfd5d08a6d7283834465dfc84d04ee6fbac5f81 | 73.4438 | 74.1458 | 72.5775 | 73.5851 | 75.0483 | 10 | 754 | 763 | 91 | 229 | 126 |
| 99 | jubarte-ast | jubarte-final@5bf73ce40d09+git.f9c71f0cd5b7ea561c4739d61cad72a65296ed65 | 73.3729 | 74.1068 | 72.5074 | 73.5649 | 75.0483 | 10 | 754 | 763 | 91 | 228 | 127 |
| 100 | sanity-word | — | 68.1679 | 70.4845 | 68.1679 | 70.4845 | — | 0 | 230 | 230 | 0 | 0 | 38 |
| 101 | jubarte-ast | jubarte-final@041a9bd0cbc3+git.8f8ea75949175abde9b7700308190a3dcd3508ab | 71.0799 | 68.7935 | 70.2415 | 68.6388 | 75.0483 | 10 | 754 | 763 | 91 | 187 | 139 |
| 102 | jubarte-ast | jubarte-final@d43557e042c1 | 70.5699 | 68.6678 | 69.83 | 68.2992 | 74.8855 | 9 | 755 | 763 | 84 | 178 | 142 |
| 103 | ooxmlsdk | — | 55.1866 | 55.2398 | 55.1866 | 55.2398 | — | 0 | 232 | 232 | 0 | 0 | 52 |
| 104 | docxodus | 6.4.0 | 58.7425 | 55.0306 | 58.1749 | 54.9959 | — | 2 | 205 | 207 | 3 | 7 | 66 |
| 105 | folio | 0.3.1 | 55.3092 | 53.7539 | 54.7748 | 53.525 | — | 2 | 205 | 207 | 0 | 1 | 75 |
| 106 | superdoc | 1.19.2 | 56.3218 | 54.8131 | 49.3898 | 52.9529 | -0.0027 | 33 | 171 | 195 | 2 | 3 | 51 |
| 107 | folio | 0.15.13 | 52.1299 | 50.4313 | 50.8318 | 50.2913 | 4.3275 | 19 | 744 | 763 | 0 | 5 | 354 |
| 108 | superdoc | 1.21.3 | 53.1281 | 51.5561 | 46.3043 | 50.1612 | -0.0027 | 115 | 665 | 763 | 3 | 14 | 278 |
| 109 | docx-redline-js | 0.3.0-ts-migration | 50.5319 | 50.2615 | 48.4264 | 50.09 | — | 7 | 161 | 168 | 0 | 0 | 73 |
| 110 | docxodus | 7.0.0 | 50.4935 | 49.6384 | 50.4935 | 49.6384 | — | 0 | 196 | 196 | 0 | 0 | 102 |
| 111 | superdoc-redlines | 0.2.0 | 51.4092 | 50.1062 | 47.3665 | 49.1564 | 1.4947 | 68 | 703 | 763 | 0 | 5 | 346 |
| 112 | docx-redline-js | 0.3.0 | 46.1928 | 47.4243 | 45.1636 | 47.2226 | -3.3472 | 17 | 746 | 763 | 0 | 0 | 517 |
| 113 | redlines | 0.6.1 | 45.9391 | 47.1411 | 44.8554 | 47.0451 | -2.9557 | 18 | 745 | 763 | 0 | 0 | 488 |
| 114 | superdoc | 2.0.0 | 45.1946 | 46.7186 | 19.606 | 0 | -16.4745 | 432 | 331 | 763 | 1 | 4 | 269 |
| 115 | docx-redline-js | — | 55.1236 | 55.1236 | 12.2497 | 0 | — | 7 | 2 | 9 | 0 | 0 | 1 |

### Common-subset ranking (script_redlines)

Paired comparison on the **614** documents every full-map vendor below completed (largest score map per vendor; current-stamp smokes do not shrink the set). Keys: `results/common_subset_script_redlines.txt`. Unlike the aggregate tables, these medians are computed on the SAME documents.

| # | vendor | version | median | mean |
| --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 95.40 | 83.50 |
| 2 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 95.36 | 87.23 |
| 3 | jubarte | jubarte-final@a58157a9cd2d | 92.29 | 84.19 |
| 4 | jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 90.79 | 82.52 |
| 5 | jubarte-ast | jubarte-final@138300e8471d | 80.42 | 76.64 |
| 6 | superdoc | 1.21.3 | 52.14 | 53.71 |
| 7 | superdoc-redlines | 0.2.0 | 51.24 | 52.58 |
| 8 | folio | 0.15.13 | 51.10 | 53.93 |
| 9 | docx-redline-js | 0.3.0 | 48.16 | 47.89 |
| 10 | redlines | 0.6.1 | 47.96 | 47.32 |

### Paired comparisons (script_redlines)

Per-doc paired deltas on shared documents (best pin per vendor); `win/loss/tie` counts docs where the FIRST vendor scores higher/lower/equal. Wilcoxon signed-rank p, zsplit zero method.

| vendor A | vendor B | docs | win/loss/tie | median Δ | p |
| --- | --- | --- | --- | --- | --- |
| docx-redline-js | docxodus | 743 | 22/721/0 | -41.10 | 3.54e-120 |
| docx-redline-js | folio | 735 | 160/561/14 | -2.43 | 8.45e-58 |
| docx-redline-js | jubarte | 746 | 22/722/2 | -41.76 | 4.15e-121 |
| docx-redline-js | jubarte-ast | 746 | 24/721/1 | -29.73 | 3.47e-117 |
| docx-redline-js | jubarte-rust | 746 | 8/736/2 | -43.90 | 4.02e-123 |
| docx-redline-js | jubarte-wasm | 746 | 18/726/2 | -37.24 | 8.70e-122 |
| docx-redline-js | ooxmlsdk | 152 | 30/122/0 | -8.11 | 1.77e-13 |
| docx-redline-js | redlines | 736 | 368/367/1 | +0.01 | 8.11e-01 |
| docx-redline-js | sanity-word | 151 | 12/139/0 | -23.41 | 5.12e-23 |
| docx-redline-js | superdoc | 657 | 172/485/0 | -4.01 | 1.92e-43 |
| docx-redline-js | superdoc-redlines | 689 | 208/468/13 | -2.05 | 1.20e-32 |
| docxodus | folio | 741 | 703/38/0 | +29.90 | 2.60e-117 |
| docxodus | jubarte | 760 | 292/345/123 | +0.00 | 1.15e-01 |
| docxodus | jubarte-ast | 760 | 466/199/95 | +1.46 | 2.59e-28 |
| docxodus | jubarte-rust | 760 | 267/366/127 | +0.00 | 7.92e-08 |
| docxodus | jubarte-wasm | 760 | 343/286/131 | +0.00 | 2.55e-02 |
| docxodus | ooxmlsdk | 155 | 154/1/0 | +38.36 | 3.54e-27 |
| docxodus | redlines | 745 | 727/18/0 | +40.19 | 1.15e-121 |
| docxodus | sanity-word | 154 | 151/3/0 | +22.80 | 6.28e-27 |
| docxodus | superdoc | 662 | 616/44/2 | +35.15 | 1.31e-103 |
| docxodus | superdoc-redlines | 700 | 662/38/0 | +31.15 | 8.06e-113 |
| folio | jubarte | 744 | 40/702/2 | -31.76 | 3.64e-117 |
| folio | jubarte-ast | 744 | 58/685/1 | -21.52 | 9.26e-110 |
| folio | jubarte-rust | 744 | 18/724/2 | -34.10 | 1.74e-122 |
| folio | jubarte-wasm | 744 | 39/703/2 | -28.28 | 1.78e-119 |
| folio | ooxmlsdk | 154 | 85/69/0 | +1.65 | 3.53e-03 |
| folio | redlines | 734 | 571/162/1 | +3.86 | 3.34e-60 |
| folio | sanity-word | 153 | 34/119/0 | -11.62 | 3.78e-13 |
| folio | superdoc | 657 | 350/306/1 | +0.30 | 1.67e-01 |
| folio | superdoc-redlines | 685 | 412/233/40 | +0.19 | 4.69e-15 |
| jubarte | jubarte-ast | 763 | 451/206/106 | +2.00 | 1.15e-26 |
| jubarte | jubarte-rust | 763 | 240/334/189 | +0.00 | 1.28e-06 |
| jubarte | jubarte-wasm | 763 | 332/241/190 | +0.00 | 1.56e-04 |
| jubarte | ooxmlsdk | 155 | 149/6/0 | +32.88 | 7.68e-27 |
| jubarte | redlines | 745 | 729/16/0 | +40.64 | 2.99e-122 |
| jubarte | sanity-word | 154 | 134/20/0 | +18.50 | 8.79e-22 |
| jubarte | superdoc | 665 | 619/41/5 | +35.69 | 8.34e-104 |
| jubarte | superdoc-redlines | 703 | 672/29/2 | +32.76 | 6.71e-113 |
| jubarte-ast | jubarte-rust | 763 | 156/529/78 | -5.14 | 8.75e-57 |
| jubarte-ast | jubarte-wasm | 763 | 217/455/91 | -1.95 | 9.02e-24 |
| jubarte-ast | ooxmlsdk | 155 | 153/2/0 | +31.91 | 3.82e-27 |
| jubarte-ast | redlines | 745 | 717/28/0 | +30.38 | 2.44e-120 |
| jubarte-ast | sanity-word | 154 | 143/11/0 | +18.17 | 1.35e-25 |
| jubarte-ast | superdoc | 665 | 593/67/5 | +23.27 | 7.06e-95 |
| jubarte-ast | superdoc-redlines | 703 | 652/50/1 | +21.57 | 1.13e-106 |
| jubarte-rust | jubarte-wasm | 763 | 318/87/358 | +0.00 | 6.24e-34 |
| jubarte-rust | ooxmlsdk | 155 | 154/1/0 | +35.77 | 3.54e-27 |
| jubarte-rust | redlines | 745 | 740/5/0 | +42.33 | 1.76e-123 |
| jubarte-rust | sanity-word | 154 | 150/4/0 | +20.64 | 1.22e-26 |
| jubarte-rust | superdoc | 665 | 642/18/5 | +37.06 | 7.60e-109 |
| jubarte-rust | superdoc-redlines | 703 | 685/16/2 | +35.37 | 5.77e-116 |
| jubarte-wasm | ooxmlsdk | 155 | 153/2/0 | +35.52 | 3.68e-27 |
| jubarte-wasm | redlines | 745 | 726/19/0 | +38.47 | 5.58e-122 |
| jubarte-wasm | sanity-word | 154 | 149/5/0 | +20.21 | 2.50e-26 |
| jubarte-wasm | superdoc | 665 | 622/38/5 | +33.16 | 1.12e-103 |
| jubarte-wasm | superdoc-redlines | 703 | 671/30/2 | +29.54 | 1.90e-113 |
| ooxmlsdk | redlines | 153 | 117/36/0 | +5.77 | 1.04e-16 |
| ooxmlsdk | sanity-word | 230 | 15/215/0 | -14.02 | 3.48e-35 |
| ooxmlsdk | superdoc | 146 | 82/64/0 | +2.00 | 2.59e-01 |
| ooxmlsdk | superdoc-redlines | 146 | 74/72/0 | +0.10 | 2.96e-01 |
| redlines | sanity-word | 152 | 7/145/0 | -19.63 | 3.01e-26 |
| redlines | superdoc | 661 | 166/495/0 | -4.08 | 3.76e-48 |
| redlines | superdoc-redlines | 685 | 196/489/0 | -2.91 | 3.59e-35 |
| sanity-word | superdoc | 145 | 120/25/0 | +15.73 | 1.52e-17 |
| sanity-word | superdoc-redlines | 145 | 121/24/0 | +13.41 | 3.07e-16 |
| superdoc | superdoc-redlines | 629 | 345/284/0 | +0.60 | 3.61e-02 |

### Lens health (script_redlines)

Docs where the pixel lens and a judging lens (functional accept/reject invariant, WV-1 word-validate) conflict — the bench is measuring the wrong thing on those docs. A bench-health alarm, not a ranking signal.

- **docx-redline-js** 0.3.0: 2 doc(s) where the lenses disagree (0.5% of two-lens docs)
- **docxodus** 9.0.0: 86 doc(s) where the lenses disagree (25.4% of two-lens docs)
- **docxodus** 9.8.0: 17 doc(s) where the lenses disagree (4.5% of two-lens docs)
- **folio** 0.15.13: 106 doc(s) where the lenses disagree (28.8% of two-lens docs)
- **jubarte** 0.1.0@0676fa9064f1: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@041a9bd0cbc3+git.8f8ea75949175abde9b7700308190a3dcd3508ab: 19 doc(s) where the lenses disagree (5.0% of two-lens docs)
- **jubarte** jubarte-final@066e56f0970b: 20 doc(s) where the lenses disagree (5.3% of two-lens docs)
- **jubarte** jubarte-final@138300e8471d: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@300cc3edf753: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@389db881b0bf+git.07bd8ba2113c65fdb2fe4d4ab965060337f0a8e7: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@38e6f956cb44: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@43a6633fd17e+git.a9e4a33ac250293c547fe878ebb81068deebaeb6: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@6db0dcdb2f1a+git.d99ccb5b3adda605e5304200ad88c1aff7fe53c2: 20 doc(s) where the lenses disagree (5.3% of two-lens docs)
- **jubarte** jubarte-final@6f48fe914d9a+git.d44dc07498de8ef7560e45ca7efcc3340f0b778e: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@77e68faebcda+git.b76f204f67549088bcdda1f961bf47f8bf8116e5: 19 doc(s) where the lenses disagree (5.0% of two-lens docs)
- **jubarte** jubarte-final@7ef64a75db56: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@7f6d70bdc3ce+git.b29cc0ab4efac5b6c25ad1fe0b08cbc2a8157970: 19 doc(s) where the lenses disagree (5.0% of two-lens docs)
- **jubarte** jubarte-final@88c1b1c36479: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@a58157a9cd2d: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@a6caf6b44537: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte** jubarte-final@d43557e042c1: 20 doc(s) where the lenses disagree (5.3% of two-lens docs)
- **jubarte-ast** 0.1.0@0676fa9064f1: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@041a9bd0cbc3+git.8f8ea75949175abde9b7700308190a3dcd3508ab: 36 doc(s) where the lenses disagree (9.8% of two-lens docs)
- **jubarte-ast** jubarte-final@0a703664346d+git.50155bfba69385bf0e99dd3a19b15da1f58e104c: 25 doc(s) where the lenses disagree (6.8% of two-lens docs)
- **jubarte-ast** jubarte-final@138300e8471d: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@300cc3edf753: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@38e6f956cb44: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@5bf73ce40d09+git.f9c71f0cd5b7ea561c4739d61cad72a65296ed65: 25 doc(s) where the lenses disagree (6.8% of two-lens docs)
- **jubarte-ast** jubarte-final@6e7229a4d930+git.6f9f76fcd961c9ace7fce9941307b712ada01282: 25 doc(s) where the lenses disagree (6.8% of two-lens docs)
- **jubarte-ast** jubarte-final@7ef64a75db56: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@88c1b1c36479: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@a58157a9cd2d: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@a6caf6b44537: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@c043b0aaefb3+git.19b5f14c6088a71280786a864d45cac3aa6e7c92: 25 doc(s) where the lenses disagree (6.8% of two-lens docs)
- **jubarte-ast** jubarte-final@d294713913bb+git.b256b039d54561800b4462fb67cfcd5a8143f606: 25 doc(s) where the lenses disagree (6.8% of two-lens docs)
- **jubarte-ast** jubarte-final@d43557e042c1: 36 doc(s) where the lenses disagree (9.8% of two-lens docs)
- **jubarte-ast** jubarte-final@dc06c68fa885+git.1cfd5d08a6d7283834465dfc84d04ee6fbac5f81: 25 doc(s) where the lenses disagree (6.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@076ef86b4e40+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@0e0a602dab95+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64: 41 doc(s) where the lenses disagree (10.9% of two-lens docs)
- **jubarte-rust** jubarte-rust@1ac8d72aa73a+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@1b9081666e72+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@279e58418eaa+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@285b7cf3881f+git.fc8c50f879974568278bcd33c476b153229313f0: 41 doc(s) where the lenses disagree (10.9% of two-lens docs)
- **jubarte-rust** jubarte-rust@36224f1d081b+git.27c8c00: 23 doc(s) where the lenses disagree (6.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@367ee1c460ed+git.0ab0e1c: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@38a1d9d3004f+git.eb5b8fe: 23 doc(s) where the lenses disagree (6.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@39fcb0806e4c+git.0f39b64e69b54a04828d78e73d071d0949dee73c: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@3af52d7e2153+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@3f6f9f41efbf+git.fc8c50f879974568278bcd33c476b153229313f0: 42 doc(s) where the lenses disagree (11.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@49d62ef4590b+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@4a6065089e4d+git.fc8c50f879974568278bcd33c476b153229313f0: 23 doc(s) where the lenses disagree (6.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@50fd692d367f+git.e2cf3556ddbdfb115161c47529e36f20ca3c233a: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@52cac2981586+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@59b02c068a09+git.0fcae65: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@5c5581a12812+git.fc8c50f879974568278bcd33c476b153229313f0: 41 doc(s) where the lenses disagree (10.9% of two-lens docs)
- **jubarte-rust** jubarte-rust@5d0e047c4d1e+git.963b8e2: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@5d704d24d79a+git.f91341b25e532ef7ff0a4ecb14e015a771f94c9f: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@5d8d1ac7be6e+git.a3c8d40: 24 doc(s) where the lenses disagree (6.4% of two-lens docs)
- **jubarte-rust** jubarte-rust@60fe4f2fb0cd+git.ebf1a79: 24 doc(s) where the lenses disagree (6.4% of two-lens docs)
- **jubarte-rust** jubarte-rust@644fa2c1c30a+git.d619d40: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@656ba15ca16e+git.ebf1a79: 24 doc(s) where the lenses disagree (6.4% of two-lens docs)
- **jubarte-rust** jubarte-rust@667241eebe86+git.0e2923194145ea254ea617b9a99fb60ea9b1d431: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@6691bea93ef4+git.a0281fc: 21 doc(s) where the lenses disagree (5.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@66c3c793a724+git.059808d: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@6923ca0b2b8e+git.fc8c50f879974568278bcd33c476b153229313f0: 97 doc(s) where the lenses disagree (25.7% of two-lens docs)
- **jubarte-rust** jubarte-rust@736e49cff080+git.24b182f5824aaf9acdd3a0c00e9bf88b22b6fde9: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@747fdf8585a7+git.bae2df5748e5bce5a3873056a895cbe769285c74: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@74bbefc415c4+git.6817a28378372d6e7c95227cf300889e74ab06e4: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@7837955c0955+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 24 doc(s) where the lenses disagree (6.4% of two-lens docs)
- **jubarte-rust** jubarte-rust@7db1bf4110af+git.fc8c50f879974568278bcd33c476b153229313f0: 42 doc(s) where the lenses disagree (11.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@7ee5daea8fb9+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@8047e6cb5052+git.fddb30f: 23 doc(s) where the lenses disagree (6.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@8a1e896365b3+git.1be1fcd060ce0d8e2a1b0f91df618d8ec651e3ba: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@8dea7e733d6d+git.ec66729: 23 doc(s) where the lenses disagree (6.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@9020ef223997+git.fc8c50f879974568278bcd33c476b153229313f0: 42 doc(s) where the lenses disagree (11.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@9457b6549b5d+git.ebf1a79: 26 doc(s) where the lenses disagree (6.9% of two-lens docs)
- **jubarte-rust** jubarte-rust@94ac5db42c3b+git.196d97e: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@97da13af151c+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@9854c9e68ddd+git.9d46888: 23 doc(s) where the lenses disagree (6.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@992b5db46add+git.09545197c99f7b21583e53cb6e2b220b50d295ac: 24 doc(s) where the lenses disagree (6.4% of two-lens docs)
- **jubarte-rust** jubarte-rust@9b85d42d42e1+git.84bb80216132b6f249de1455dba9b6092664ecea: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@9b88994c2a01+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@9ba60702c118+git.e3bc6b6: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@9f4892c93e04+git.a6d5890: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@a46fb002a1a8+git.970a113dde4b71de07ccdda4a67cd2cbc68bdcc1: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@ac0e3a61d563+git.fc8c50f879974568278bcd33c476b153229313f0: 43 doc(s) where the lenses disagree (11.4% of two-lens docs)
- **jubarte-rust** jubarte-rust@b79584ee185e+git.7ff6c38606a1595e80a4600d81603640fbacd472: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@b9d4740f3529+git.ebf1a79: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@ba4cfc3ecc67+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@bb2bc6195c45+git.fc8c50f879974568278bcd33c476b153229313f0: 42 doc(s) where the lenses disagree (11.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@bea5f183c4c5+git.f6959f8: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@bf3c7b4b7e4b+git.fc8c50f879974568278bcd33c476b153229313f0: 42 doc(s) where the lenses disagree (11.1% of two-lens docs)
- **jubarte-rust** jubarte-rust@bf7bb2748045+git.8cd638d6f0cdb261c55150c056af9cf44fa332a6: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@cacb0b9bcb34+git.fc8c50f879974568278bcd33c476b153229313f0: 41 doc(s) where the lenses disagree (10.9% of two-lens docs)
- **jubarte-rust** jubarte-rust@d100650f7be0+git.17afecafc3deb2b99c4577cbd0fbf6a0e6356daf: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@d2de8e147655+git.b910a23bce9b63a393ac6186ab366a39d6aaa504: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@d3a1b10c4408+git.fc8c50f879974568278bcd33c476b153229313f0: 97 doc(s) where the lenses disagree (25.7% of two-lens docs)
- **jubarte-rust** jubarte-rust@d434447d27ce+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@e0fe28e5b256+git.2351844: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@eb34d99e486c+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@f3609460e82a+git.3e1883881eef64647a81dabe858a137e60026a3a: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@f48dcacc7478+git.fc8c50f879974568278bcd33c476b153229313f0: 22 doc(s) where the lenses disagree (5.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@f86091a180ce+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-rust** jubarte-rust@fcea02da49f4: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0: 25 doc(s) where the lenses disagree (6.7% of two-lens docs)
- **jubarte-wasm** 0.1.0@1331a4ff7c61+git.8cd638d6f0cdb261c55150c056af9cf44fa332a6: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@18f6c9fd87db+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@2957178cc645+git.b910a23bce9b63a393ac6186ab366a39d6aaa504: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@a795fa73ea5f+git.0f39b64e69b54a04828d78e73d071d0949dee73c: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@b13bcb128725+git.bae2df5748e5bce5a3873056a895cbe769285c74: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@d3810de5aa53+git.0e2923194145ea254ea617b9a99fb60ea9b1d431: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@d5f48a35f21a+git.24b182f5824aaf9acdd3a0c00e9bf88b22b6fde9: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@dc46d94d88ab+git.6817a28378372d6e7c95227cf300889e74ab06e4: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@e1e19c982338+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **redlines** 0.6.1: 64 doc(s) where the lenses disagree (17.6% of two-lens docs)
- **superdoc** 1.19.2: 25 doc(s) where the lenses disagree (15.9% of two-lens docs)
- **superdoc** 1.21.3: 53 doc(s) where the lenses disagree (16.9% of two-lens docs)
- **superdoc-redlines** 0.2.0: 38 doc(s) where the lenses disagree (11.2% of two-lens docs)

### `accepted_changes`

`accepted_changes`

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 90.1868 | 100 | 88.8203 | 100 | — | 4 | 195 | 198 | 119 | 145 | 18 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 68.9994 | 77.1882 | 68.9994 | 77.1882 | — | 0 | 164 | 164 | 14 | 22 | 43 |
| 2 | docxodus | 7.0.0 | 70.1963 | 74.9182 | 70.1963 | 74.9182 | — | 0 | 164 | 164 | 17 | 44 | 49 |
| 3 | superdoc | 1.19.2 | 63.818 | 61.1184 | 57.6669 | 55.8213 | — | 16 | 150 | 166 | 2 | 3 | 33 |
| 4 | folio | 0.3.1 | 57.9094 | 55.608 | 54.5813 | 53.9618 | — | 10 | 164 | 174 | 3 | 4 | 61 |

### `roundtrip`

roundtrip (self-diff → pdf_source)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 99.9949 | 100 | 99.9949 | 100 | — | 0 | 166 | 166 | 163 | 166 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.3.1 | 98.0712 | 100 | 98.0712 | 100 | — | 0 | 198 | 198 | 185 | 190 | 4 |
| 2 | docxodus | 7.0.0 | 97.4281 | 100 | 97.4281 | 100 | — | 0 | 166 | 166 | 148 | 157 | 4 |
| 3 | docxodus | 6.4.0 | 92.2445 | 100 | 92.2445 | 100 | — | 0 | 198 | 198 | 144 | 161 | 13 |
| 4 | superdoc | 1.19.2 | 93.0017 | 100 | 91.5854 | 100 | — | 3 | 194 | 197 | 144 | 158 | 8 |

### `visual_rendering`

visual_rendering (Playwright viewer)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 65.2677 | 67.8808 | 65.2677 | 67.8808 | — | 0 | 199 | 199 | 1 | 7 | 30 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 58.7798 | 61.2486 | 58.7798 | 61.2486 | — | 0 | 199 | 199 | 0 | 0 | 38 |
| 2 | folio | 0.5.0 | 59.6494 | 55.0967 | 59.6494 | 55.0967 | — | 0 | 198 | 198 | 0 | 3 | 56 |
| 3 | docxodus | 6.4.0-local.1 | 56.5017 | 49.7216 | 53.9463 | 49.2363 | — | 9 | 190 | 199 | 0 | 0 | 97 |
| 4 | docxodus | 7.0.0 | 56.5017 | 49.7216 | 53.9463 | 49.2363 | — | 9 | 190 | 199 | 0 | 0 | 97 |

### `visual_redlines`

visual_redlines (Playwright)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 61.0993 | 62.44 | 61.0993 | 62.44 | — | 0 | 155 | 155 | 0 | 0 | 26 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 60.9207 | 61.2232 | 48.5357 | 58.9198 | — | 37 | 145 | 182 | 0 | 0 | 13 |
| 2 | superdoc | 1.44.1 | 55.3334 | 56.4237 | 54.998 | 56.3376 | — | 1 | 164 | 165 | 0 | 0 | 44 |
| 3 | docxodus | 9.0.0 | 60.1462 | 57.5572 | 54.3453 | 55.3917 | — | 19 | 178 | 197 | 1 | 4 | 48 |
| 4 | folio | 0.5.0 | 51.5494 | 51.6497 | 50.9283 | 51.4809 | — | 2 | 164 | 166 | 0 | 0 | 68 |
| 5 | docxodus | 7.0.0 | 48.2275 | 48.0758 | 47.6464 | 48.0337 | — | 2 | 164 | 166 | 0 | 0 | 122 |

### `visual_accepted_changes`

visual_accepted_changes (Playwright)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 64.631 | 65.7934 | 64.631 | 65.7934 | — | 0 | 155 | 155 | 0 | 7 | 19 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 62.3235 | 62.7622 | 62.3235 | 62.7622 | — | 0 | 152 | 152 | 0 | 1 | 21 |
| 2 | superdoc | 1.44.1 | 59.3354 | 60.971 | 59.3354 | 60.971 | — | 0 | 165 | 165 | 0 | 0 | 35 |
| 3 | folio | 0.5.0 | 59.671 | 54.9489 | 59.671 | 54.9489 | — | 0 | 164 | 164 | 0 | 0 | 42 |

## All fidelity runs (flat)

| vendor | version | datetime | benchmark | mean | median | n_docs |
| --- | --- | --- | --- | --- | --- | --- |
| docx-redline-js | 0.3.0 | 2026-08-04T14:16:57.600170+00:00 | script_redlines | 46.1928 | 47.4243 | 746 |
| docx-redline-js | 0.3.0-ts-migration | 2026-07-15T23:24:01.804490+00:00 | script_redlines | 50.5319 | 50.2615 | 161 |
| docx-redline-js | — | 2026-07-15T23:21:34.805527+00:00 | script_redlines | 55.1236 | 55.1236 | 2 |
| docxodus | 6.4.0 | 2026-07-09T15:58:38.145555+00:00 | accepted_changes | 68.9994 | 77.1882 | 164 |
| docxodus | 6.4.0 | 2026-07-10T00:12:10.214778+00:00 | roundtrip | 92.2445 | 100 | 198 |
| docxodus | 6.4.0 | 2026-07-09T15:48:47.581159+00:00 | script_redlines | 58.7425 | 55.0306 | 205 |
| docxodus | 6.4.0 | 2026-07-09T17:19:51.161639+00:00 | visual_accepted_changes | 62.3235 | 62.7622 | 152 |
| docxodus | 6.4.0 | 2026-07-09T16:57:22.200205+00:00 | visual_redlines | 60.9207 | 61.2232 | 145 |
| docxodus | 6.4.0-local.1 | 2026-07-10T20:58:07.916380+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | accepted_changes | 70.1963 | 74.9182 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | roundtrip | 97.4281 | 100 | 166 |
| docxodus | 7.0.0 | 2026-07-11T02:25:04.610761+00:00 | script_redlines | 50.4935 | 49.6384 | 196 |
| docxodus | 7.0.0 | 2026-07-10T21:59:48.076126+00:00 | visual_redlines | 48.2275 | 48.0758 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:55:37.514080+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| docxodus | 9.0.0 | 2026-08-04T14:30:46.167624+00:00 | script_redlines | 80.5535 | 91.1892 | 760 |
| docxodus | 9.0.0 | 2026-08-04T13:11:19.057858+00:00 | visual_redlines | 60.1462 | 57.5572 | 178 |
| docxodus | 9.8.0 | 2026-08-12T23:42:30.397782+00:00 | accepted_changes | 90.1868 | 100 | 195 |
| docxodus | 9.8.0 | 2026-08-12T23:42:30.397782+00:00 | roundtrip | 99.9949 | 100 | 166 |
| docxodus | 9.8.0 | 2026-08-12T23:42:30.397782+00:00 | script_redlines | 80.5534 | 91.1892 | 760 |
| docxodus | 9.8.0 | 2026-08-13T02:19:03.018138+00:00 | visual_accepted_changes | 64.631 | 65.7934 | 155 |
| docxodus | 9.8.0 | 2026-08-13T02:15:21.827989+00:00 | visual_redlines | 61.0993 | 62.44 | 155 |
| docxodus | 9.8.0 | 2026-08-13T02:07:50.495893+00:00 | visual_rendering | 65.2677 | 67.8808 | 199 |
| folio | 0.15.13 | 2026-08-04T14:51:49.763490+00:00 | script_redlines | 52.1299 | 50.4313 | 744 |
| folio | 0.3.1 | 2026-07-09T13:48:42.309993+00:00 | accepted_changes | 57.9094 | 55.608 | 164 |
| folio | 0.3.1 | 2026-07-10T00:18:18.365930+00:00 | roundtrip | 98.0712 | 100 | 198 |
| folio | 0.3.1 | 2026-07-09T13:01:34.270204+00:00 | script_redlines | 55.3092 | 53.7539 | 205 |
| folio | 0.5.0 | 2026-07-08T20:35:26.466209+00:00 | visual_accepted_changes | 59.671 | 54.9489 | 164 |
| folio | 0.5.0 | 2026-07-08T20:20:25.117836+00:00 | visual_redlines | 51.5494 | 51.6497 | 164 |
| folio | 0.5.0 | 2026-07-08T20:14:38.167302+00:00 | visual_rendering | 59.6494 | 55.0967 | 198 |
| jubarte | 0.1.0@0676fa9064f1 | 2026-08-11T06:16:32.933733+00:00 | script_redlines | 81.3788 | 88.5165 | 763 |
| jubarte | jubarte-final@041a9bd0cbc3+git.8f8ea75949175abde9b7700308190a3dcd3508ab | 2026-08-05T02:33:10.924626+00:00 | script_redlines | 77.7654 | 79.9837 | 763 |
| jubarte | jubarte-final@066e56f0970b | 2026-08-05T21:38:30.354713+00:00 | script_redlines | 80.3036 | 85.9573 | 763 |
| jubarte | jubarte-final@138300e8471d | 2026-08-11T09:09:21.597339+00:00 | script_redlines | 81.4564 | 88.5972 | 763 |
| jubarte | jubarte-final@300cc3edf753 | 2026-08-11T07:40:26.733234+00:00 | script_redlines | 81.4515 | 88.5972 | 763 |
| jubarte | jubarte-final@389db881b0bf+git.07bd8ba2113c65fdb2fe4d4ab965060337f0a8e7 | 2026-08-05T10:46:59.204812+00:00 | script_redlines | 79.1927 | 83.2251 | 763 |
| jubarte | jubarte-final@38e6f956cb44 | 2026-08-11T09:59:59.345659+00:00 | script_redlines | 81.4165 | 88.5119 | 763 |
| jubarte | jubarte-final@43a6633fd17e+git.a9e4a33ac250293c547fe878ebb81068deebaeb6 | 2026-08-05T14:03:36.252040+00:00 | script_redlines | 80.3604 | 86.4243 | 763 |
| jubarte | jubarte-final@6db0dcdb2f1a+git.d99ccb5b3adda605e5304200ad88c1aff7fe53c2 | 2026-08-04T21:31:47.189077+00:00 | script_redlines | 77.0151 | 78.5311 | 763 |
| jubarte | jubarte-final@6f48fe914d9a+git.d44dc07498de8ef7560e45ca7efcc3340f0b778e | 2026-08-05T14:38:11.253906+00:00 | script_redlines | 80.6024 | 86.6013 | 763 |
| jubarte | jubarte-final@77e68faebcda+git.b76f204f67549088bcdda1f961bf47f8bf8116e5 | 2026-08-05T08:46:20.516338+00:00 | script_redlines | 77.9828 | 80.6738 | 763 |
| jubarte | jubarte-final@7ef64a75db56 | 2026-08-11T07:02:28.859614+00:00 | script_redlines | 81.4371 | 88.5972 | 763 |
| jubarte | jubarte-final@7f6d70bdc3ce+git.b29cc0ab4efac5b6c25ad1fe0b08cbc2a8157970 | 2026-08-05T09:45:35.759913+00:00 | script_redlines | 78.1105 | 80.9583 | 763 |
| jubarte | jubarte-final@88c1b1c36479 | 2026-08-11T01:43:45.807916+00:00 | script_redlines | 80.5701 | 86.6639 | 763 |
| jubarte | jubarte-final@a58157a9cd2d | 2026-08-11T10:33:59.842953+00:00 | script_redlines | 81.4686 | 88.5972 | 763 |
| jubarte | jubarte-final@a6caf6b44537 | 2026-08-11T08:27:44.882913+00:00 | script_redlines | 81.4453 | 88.5972 | 763 |
| jubarte | jubarte-final@d43557e042c1 | 2026-08-04T11:01:14.552442+00:00 | script_redlines | 77.0151 | 78.5311 | 763 |
| jubarte-ast | 0.1.0@0676fa9064f1 | 2026-08-11T06:34:50.355176+00:00 | script_redlines | 74.1962 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@041a9bd0cbc3+git.8f8ea75949175abde9b7700308190a3dcd3508ab | 2026-08-05T03:00:38.422875+00:00 | script_redlines | 71.0799 | 68.7935 | 754 |
| jubarte-ast | jubarte-final@0a703664346d+git.50155bfba69385bf0e99dd3a19b15da1f58e104c | 2026-08-05T14:55:51.076813+00:00 | script_redlines | 73.8663 | 75.8715 | 754 |
| jubarte-ast | jubarte-final@138300e8471d | 2026-08-11T09:24:50.477795+00:00 | script_redlines | 74.1963 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@300cc3edf753 | 2026-08-11T07:56:13.856310+00:00 | script_redlines | 74.1963 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@38e6f956cb44 | 2026-08-11T10:15:28.295686+00:00 | script_redlines | 74.1963 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@5bf73ce40d09+git.f9c71f0cd5b7ea561c4739d61cad72a65296ed65 | 2026-08-05T03:45:38.780899+00:00 | script_redlines | 73.3729 | 74.1068 | 754 |
| jubarte-ast | jubarte-final@6e7229a4d930+git.6f9f76fcd961c9ace7fce9941307b712ada01282 | 2026-08-05T08:07:06.048363+00:00 | script_redlines | 73.4588 | 74.2932 | 754 |
| jubarte-ast | jubarte-final@7ef64a75db56 | 2026-08-11T07:19:50.503642+00:00 | script_redlines | 74.1963 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@88c1b1c36479 | 2026-08-11T01:43:45.078578+00:00 | script_redlines | 74.1963 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@a58157a9cd2d | 2026-08-11T10:49:32.739563+00:00 | script_redlines | 74.1962 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@a6caf6b44537 | 2026-08-11T08:43:13.792216+00:00 | script_redlines | 74.1963 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@c043b0aaefb3+git.19b5f14c6088a71280786a864d45cac3aa6e7c92 | 2026-08-05T11:18:23.391679+00:00 | script_redlines | 73.8663 | 75.8715 | 754 |
| jubarte-ast | jubarte-final@d294713913bb+git.b256b039d54561800b4462fb67cfcd5a8143f606 | 2026-08-05T17:47:54.163333+00:00 | script_redlines | 74.4501 | 76.7449 | 754 |
| jubarte-ast | jubarte-final@d43557e042c1 | 2026-08-04T11:15:42.562625+00:00 | script_redlines | 70.5699 | 68.6678 | 755 |
| jubarte-ast | jubarte-final@dc06c68fa885+git.1cfd5d08a6d7283834465dfc84d04ee6fbac5f81 | 2026-08-05T07:47:52.355790+00:00 | script_redlines | 73.4438 | 74.1458 | 754 |
| jubarte-rust | jubarte-rust@076ef86b4e40+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T10:16:48.983319+00:00 | script_redlines | 81.2339 | 88.4278 | 763 |
| jubarte-rust | jubarte-rust@0e0a602dab95+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T22:07:30.760086+00:00 | script_redlines | 79.4838 | 84.4626 | 763 |
| jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 2026-08-13T20:58:50.595888+00:00 | script_redlines | 84.4662 | 92.6623 | 763 |
| jubarte-rust | jubarte-rust@1ac8d72aa73a+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T12:41:53.089859+00:00 | script_redlines | 81.2996 | 88.5165 | 763 |
| jubarte-rust | jubarte-rust@1b9081666e72+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T15:29:08.728155+00:00 | script_redlines | 81.3463 | 88.6893 | 763 |
| jubarte-rust | jubarte-rust@279e58418eaa+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T22:42:28.080931+00:00 | script_redlines | 79.5678 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@285b7cf3881f+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-12T18:09:15.344792+00:00 | script_redlines | 84.1766 | 92.2881 | 763 |
| jubarte-rust | jubarte-rust@36224f1d081b+git.27c8c00 | 2026-08-06T23:46:24.753202+00:00 | script_redlines | 79.7128 | 84.4626 | 763 |
| jubarte-rust | jubarte-rust@367ee1c460ed+git.0ab0e1c | 2026-08-06T21:45:04.942363+00:00 | script_redlines | 79.3289 | 82.9931 | 763 |
| jubarte-rust | jubarte-rust@38a1d9d3004f+git.eb5b8fe | 2026-08-06T19:27:40.151858+00:00 | script_redlines | 78.8714 | 82.3032 | 763 |
| jubarte-rust | jubarte-rust@39fcb0806e4c+git.0f39b64e69b54a04828d78e73d071d0949dee73c | 2026-08-05T15:30:40.564615+00:00 | script_redlines | 78.8943 | 83.5854 | 763 |
| jubarte-rust | jubarte-rust@3af52d7e2153+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T13:39:44.263115+00:00 | script_redlines | 81.3835 | 88.6893 | 763 |
| jubarte-rust | jubarte-rust@3f6f9f41efbf+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-12T01:24:55.548763+00:00 | script_redlines | 83.2518 | 91.5868 | 763 |
| jubarte-rust | jubarte-rust@49d62ef4590b+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73 | 2026-08-10T03:38:49.307028+00:00 | script_redlines | 80.7925 | 86.452 | 763 |
| jubarte-rust | jubarte-rust@4a6065089e4d+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T17:16:15.909363+00:00 | script_redlines | 81.4063 | 88.7331 | 763 |
| jubarte-rust | jubarte-rust@50fd692d367f+git.e2cf3556ddbdfb115161c47529e36f20ca3c233a | 2026-08-07T14:34:32.773470+00:00 | script_redlines | 80.5658 | 86.1607 | 763 |
| jubarte-rust | jubarte-rust@52cac2981586+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73 | 2026-08-10T02:38:08.855646+00:00 | script_redlines | 80.7045 | 86.4366 | 763 |
| jubarte-rust | jubarte-rust@59b02c068a09+git.0fcae65 | 2026-08-10T06:49:44.884280+00:00 | script_redlines | 81.1719 | 88.1561 | 763 |
| jubarte-rust | jubarte-rust@5c5581a12812+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-12T20:21:41.510518+00:00 | script_redlines | 84.0909 | 92.3803 | 763 |
| jubarte-rust | jubarte-rust@5d0e047c4d1e+git.963b8e2 | 2026-08-10T05:54:26.855087+00:00 | script_redlines | 81.1275 | 88.1561 | 763 |
| jubarte-rust | jubarte-rust@5d704d24d79a+git.f91341b25e532ef7ff0a4ecb14e015a771f94c9f | 2026-08-07T13:27:23.431527+00:00 | script_redlines | 79.4531 | 82.7618 | 763 |
| jubarte-rust | jubarte-rust@5d8d1ac7be6e+git.a3c8d40 | 2026-08-07T06:05:02.146869+00:00 | script_redlines | 79.7484 | 84.3155 | 763 |
| jubarte-rust | jubarte-rust@60fe4f2fb0cd+git.ebf1a79 | 2026-08-06T06:22:22.274196+00:00 | script_redlines | 79.4668 | 85.9057 | 763 |
| jubarte-rust | jubarte-rust@644fa2c1c30a+git.d619d40 | 2026-08-07T08:09:00.811435+00:00 | script_redlines | 78.6064 | 81.1185 | 763 |
| jubarte-rust | jubarte-rust@656ba15ca16e+git.ebf1a79 | 2026-08-06T04:22:42.751808+00:00 | script_redlines | 79.4873 | 85.3205 | 763 |
| jubarte-rust | jubarte-rust@667241eebe86+git.0e2923194145ea254ea617b9a99fb60ea9b1d431 | 2026-08-05T05:35:07.209228+00:00 | script_redlines | 77.9237 | 81.8301 | 763 |
| jubarte-rust | jubarte-rust@6691bea93ef4+git.a0281fc | 2026-08-10T06:27:10.970368+00:00 | script_redlines | 81.1268 | 88.1561 | 763 |
| jubarte-rust | jubarte-rust@66c3c793a724+git.059808d | 2026-08-06T12:57:33.785486+00:00 | script_redlines | 79.2188 | 84.222 | 763 |
| jubarte-rust | jubarte-rust@6923ca0b2b8e+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-11T14:13:31.573618+00:00 | script_redlines | 82.1163 | 90.3458 | 763 |
| jubarte-rust | jubarte-rust@736e49cff080+git.24b182f5824aaf9acdd3a0c00e9bf88b22b6fde9 | 2026-08-05T01:33:59.928493+00:00 | script_redlines | 77.555 | 81.1624 | 763 |
| jubarte-rust | jubarte-rust@747fdf8585a7+git.bae2df5748e5bce5a3873056a895cbe769285c74 | 2026-08-05T06:07:56.425508+00:00 | script_redlines | 77.9701 | 81.8301 | 763 |
| jubarte-rust | jubarte-rust@74bbefc415c4+git.6817a28378372d6e7c95227cf300889e74ab06e4 | 2026-08-05T04:27:28.945896+00:00 | script_redlines | 77.6944 | 81.4434 | 763 |
| jubarte-rust | jubarte-rust@7837955c0955+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-06T02:22:53.248339+00:00 | script_redlines | 79.0459 | 83.5854 | 763 |
| jubarte-rust | jubarte-rust@7db1bf4110af+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-12T15:33:40.499494+00:00 | script_redlines | 83.7766 | 92.1381 | 763 |
| jubarte-rust | jubarte-rust@7ee5daea8fb9+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T11:08:37.068685+00:00 | script_redlines | 81.3062 | 88.5165 | 763 |
| jubarte-rust | jubarte-rust@8047e6cb5052+git.fddb30f | 2026-08-07T04:05:04.520849+00:00 | script_redlines | 80.0073 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@8a1e896365b3+git.1be1fcd060ce0d8e2a1b0f91df618d8ec651e3ba | 2026-08-04T21:47:16.159213+00:00 | script_redlines | 76.7112 | 78.971 | 763 |
| jubarte-rust | jubarte-rust@8dea7e733d6d+git.ec66729 | 2026-08-07T02:05:01.735557+00:00 | script_redlines | 79.9416 | 84.5408 | 763 |
| jubarte-rust | jubarte-rust@9020ef223997+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-11T23:02:16.283305+00:00 | script_redlines | 83.3891 | 91.6687 | 763 |
| jubarte-rust | jubarte-rust@9457b6549b5d+git.ebf1a79 | 2026-08-06T08:22:07.009758+00:00 | script_redlines | 76.3953 | 76.0408 | 763 |
| jubarte-rust | jubarte-rust@94ac5db42c3b+git.196d97e | 2026-08-07T09:23:45.045079+00:00 | script_redlines | 80.0099 | 84.5408 | 763 |
| jubarte-rust | jubarte-rust@97da13af151c+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T23:21:10.310455+00:00 | script_redlines | 79.581 | 84.8888 | 763 |
| jubarte-rust | jubarte-rust@9854c9e68ddd+git.9d46888 | 2026-08-07T08:57:57.118734+00:00 | script_redlines | 80.0835 | 85.1649 | 763 |
| jubarte-rust | jubarte-rust@992b5db46add+git.09545197c99f7b21583e53cb6e2b220b50d295ac | 2026-08-05T01:18:04.625633+00:00 | script_redlines | 77.3357 | 80.4932 | 763 |
| jubarte-rust | jubarte-rust@9b85d42d42e1+git.84bb80216132b6f249de1455dba9b6092664ecea | 2026-08-07T14:01:09.875712+00:00 | script_redlines | 80.5154 | 86.0126 | 763 |
| jubarte-rust | jubarte-rust@9b88994c2a01+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T11:38:30.819266+00:00 | script_redlines | 81.3659 | 88.6089 | 763 |
| jubarte-rust | jubarte-rust@9ba60702c118+git.e3bc6b6 | 2026-08-06T16:49:27.427467+00:00 | script_redlines | 79.6418 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@9f4892c93e04+git.a6d5890 | 2026-08-10T05:17:42.167503+00:00 | script_redlines | 81.1095 | 88.182 | 763 |
| jubarte-rust | jubarte-rust@a46fb002a1a8+git.970a113dde4b71de07ccdda4a67cd2cbc68bdcc1 | 2026-08-07T11:40:02.955603+00:00 | script_redlines | 80.4136 | 86.0123 | 763 |
| jubarte-rust | jubarte-rust@ac0e3a61d563+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-11T16:26:30.292124+00:00 | script_redlines | 83.2656 | 91.6687 | 763 |
| jubarte-rust | jubarte-rust@b79584ee185e+git.7ff6c38606a1595e80a4600d81603640fbacd472 | 2026-08-10T08:56:23.927447+00:00 | script_redlines | 81.2453 | 88.3311 | 763 |
| jubarte-rust | jubarte-rust@b9d4740f3529+git.ebf1a79 | 2026-08-06T10:22:08.672897+00:00 | script_redlines | 78.0735 | 81.1332 | 763 |
| jubarte-rust | jubarte-rust@ba4cfc3ecc67+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T21:07:56.099636+00:00 | script_redlines | 79.5621 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@bb2bc6195c45+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-12T16:01:14.569297+00:00 | script_redlines | 83.7766 | 92.1381 | 763 |
| jubarte-rust | jubarte-rust@bea5f183c4c5+git.f6959f8 | 2026-08-06T14:49:23.352974+00:00 | script_redlines | 79.5396 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@bf3c7b4b7e4b+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-12T12:45:13.849918+00:00 | script_redlines | 83.6643 | 92.0187 | 763 |
| jubarte-rust | jubarte-rust@bf7bb2748045+git.8cd638d6f0cdb261c55150c056af9cf44fa332a6 | 2026-08-05T05:06:18.911799+00:00 | script_redlines | 77.7516 | 81.4705 | 763 |
| jubarte-rust | jubarte-rust@cacb0b9bcb34+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-13T01:56:34.183931+00:00 | script_redlines | 84.4006 | 92.6088 | 763 |
| jubarte-rust | jubarte-rust@d100650f7be0+git.17afecafc3deb2b99c4577cbd0fbf6a0e6356daf | 2026-08-09T14:49:25.517926+00:00 | script_redlines | 80.5789 | 86.1607 | 763 |
| jubarte-rust | jubarte-rust@d2de8e147655+git.b910a23bce9b63a393ac6186ab366a39d6aaa504 | 2026-08-05T06:42:18.448015+00:00 | script_redlines | 78.0451 | 81.8707 | 763 |
| jubarte-rust | jubarte-rust@d3a1b10c4408+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-11T15:30:45.793347+00:00 | script_redlines | 83.1221 | 91.5114 | 763 |
| jubarte-rust | jubarte-rust@d434447d27ce+git.fcb08274fcafbc0bf3669b26d1e9b0e957743a73 | 2026-08-10T04:28:09.572143+00:00 | script_redlines | 80.9224 | 86.7269 | 763 |
| jubarte-rust | jubarte-rust@e0fe28e5b256+git.2351844 | 2026-08-06T12:27:24.605402+00:00 | script_redlines | 79.4635 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@eb34d99e486c+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T16:10:13.375483+00:00 | script_redlines | 81.3959 | 88.7331 | 763 |
| jubarte-rust | jubarte-rust@f3609460e82a+git.3e1883881eef64647a81dabe858a137e60026a3a | 2026-08-10T08:16:19.352465+00:00 | script_redlines | 81.1322 | 88.182 | 763 |
| jubarte-rust | jubarte-rust@f48dcacc7478+git.fc8c50f879974568278bcd33c476b153229313f0 | 2026-08-10T10:35:21.096835+00:00 | script_redlines | 81.2961 | 88.5165 | 763 |
| jubarte-rust | jubarte-rust@f86091a180ce+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T16:38:58.367659+00:00 | script_redlines | 79.4635 | 84.8864 | 763 |
| jubarte-rust | jubarte-rust@fcea02da49f4 | 2026-08-04T10:41:28.294117+00:00 | script_redlines | 76.2072 | 77.9542 | 763 |
| jubarte-wasm | 0.1.0 | 2026-08-04T22:31:52.576960+00:00 | script_redlines | 76.6806 | 78.8046 | 762 |
| jubarte-wasm | 0.1.0@1331a4ff7c61+git.8cd638d6f0cdb261c55150c056af9cf44fa332a6 | 2026-08-05T05:20:10.492821+00:00 | script_redlines | 77.7516 | 81.4705 | 763 |
| jubarte-wasm | 0.1.0@18f6c9fd87db+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T16:52:20.605597+00:00 | script_redlines | 79.4635 | 84.8864 | 763 |
| jubarte-wasm | 0.1.0@2957178cc645+git.b910a23bce9b63a393ac6186ab366a39d6aaa504 | 2026-08-05T06:56:52.750427+00:00 | script_redlines | 78.0451 | 81.8707 | 763 |
| jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T22:59:39.181670+00:00 | script_redlines | 79.5678 | 84.8864 | 763 |
| jubarte-wasm | 0.1.0@a795fa73ea5f+git.0f39b64e69b54a04828d78e73d071d0949dee73c | 2026-08-05T15:43:59.390623+00:00 | script_redlines | 78.8943 | 83.5854 | 763 |
| jubarte-wasm | 0.1.0@b13bcb128725+git.bae2df5748e5bce5a3873056a895cbe769285c74 | 2026-08-05T06:23:27.017633+00:00 | script_redlines | 77.9702 | 81.8301 | 763 |
| jubarte-wasm | 0.1.0@d3810de5aa53+git.0e2923194145ea254ea617b9a99fb60ea9b1d431 | 2026-08-05T05:49:24.865326+00:00 | script_redlines | 77.9237 | 81.8301 | 763 |
| jubarte-wasm | 0.1.0@d5f48a35f21a+git.24b182f5824aaf9acdd3a0c00e9bf88b22b6fde9 | 2026-08-05T01:47:10.054544+00:00 | script_redlines | 77.555 | 81.1624 | 763 |
| jubarte-wasm | 0.1.0@dc46d94d88ab+git.6817a28378372d6e7c95227cf300889e74ab06e4 | 2026-08-05T04:40:42.076254+00:00 | script_redlines | 77.6944 | 81.4434 | 763 |
| jubarte-wasm | 0.1.0@e1e19c982338+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T21:22:59.121758+00:00 | script_redlines | 79.5621 | 84.8864 | 763 |
| ooxmlsdk | — | 2026-07-13T17:24:50.712941+00:00 | script_redlines | 55.1866 | 55.2398 | 232 |
| redlines | 0.6.1 | 2026-08-04T14:04:12.116292+00:00 | script_redlines | 45.9391 | 47.1411 | 745 |
| sanity-word | — | 2026-07-13T18:06:21.529826+00:00 | script_redlines | 68.1679 | 70.4845 | 230 |
| superdoc | 1.19.2 | 2026-07-09T15:38:31.872437+00:00 | accepted_changes | 63.818 | 61.1184 | 150 |
| superdoc | 1.19.2 | 2026-07-09T18:25:24.395459+00:00 | roundtrip | 93.0017 | 100 | 194 |
| superdoc | 1.19.2 | 2026-08-04T12:22:11.089004+00:00 | script_redlines | 56.3218 | 54.8131 | 171 |
| superdoc | 1.21.3 | 2026-08-04T13:48:05.360659+00:00 | script_redlines | 53.1281 | 51.5561 | 665 |
| superdoc | 1.44.1 | 2026-07-09T18:25:37.273372+00:00 | visual_accepted_changes | 59.3354 | 60.971 | 165 |
| superdoc | 1.44.1 | 2026-07-09T18:22:07.033240+00:00 | visual_redlines | 55.3334 | 56.4237 | 164 |
| superdoc | 1.44.1 | 2026-07-09T18:16:46.431642+00:00 | visual_rendering | 58.7798 | 61.2486 | 199 |
| superdoc | 2.0.0 | 2026-08-04T13:58:56.768817+00:00 | script_redlines | 45.1946 | 46.7186 | 331 |
| superdoc-redlines | 0.2.0 | 2026-08-04T15:03:29.049566+00:00 | script_redlines | 51.4092 | 50.1062 | 703 |

## Holdout gap

Sealed 40-pair holdout (`corpus/holdout_combined.txt`) vs the visible corpus, per vendor: the latest holdout-only run (`bench run --holdout`) next to the latest COMPARABLE main run — same tool_version, `holdout_mode=excluded` (disjoint from the sealed set), full corpus (n > 100). `gap = holdout − main`; a strongly negative gap flags overfitting to the visible corpus.

| vendor | main mean | n_main | holdout mean | n_holdout | gap |
| --- | --- | --- | --- | --- | --- |
| jubarte | 77.0151 | 763 | 75.6658 | 40 | -1.35 ± 5.61 |
| jubarte-ast | 70.5699 | 755 | 77.1666 | 40 | +6.60 ± 6.74 |
| jubarte-rust | 76.2072 | 763 | 80.1107 | 40 | +3.90 ± 6.26 |

`± 2·SE` uses the holdout line's per-doc scores; a |gap| below roughly 2·SE is within sampling noise, not evidence of overfitting.

## Redline generation speed

Source: `results/speed.jsonl` (+ `results/redline_speed_bench/**/summary.json` when present). **19** generation row(s) after dedupe (one per tool×kind; prefer larger `n`, then lower median). Unit: **ms per redline** (lower = faster). See [`docs/SPEED.md`](docs/SPEED.md) for methodology.

**Fairness (read before citing):**

- **`*-inproc` / Node engines** — warm process, algorithm cost (thesis-grade).
- **CLI tools** (`docxodus-csharp`, `jubarte-rust`) — spawn + I/O + compare per sample. C# cold-start dominates; do **not** cite CLI as algorithm cost.
- **WASM `docxodus`** — Mono/.NET WASM in-process after one-time init; fat tail.

### Microbench (`kind: speed`)

Classic `scripts/speed-bench.ts` / SuperDoc speed harness (typically ~30–40 pairs × 3 reps, in-memory for Node).

| # | tool | runtime | median ms | mean ms | p95 | p99 | /s | n | fail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | node | 75.27 | 236.569 | 1499.68 | 2262.59 | 4.2 | 90 | 0 |
| 2 | superdoc | python | 40.888 | 94.191 | 619.931 | 885.366 | 10.6 | 90 | 0 |
| 3 | jubarte-final-lossless | node | 18.128 | 52.764 | 311.108 | 558.05 | 19 | 90 | 0 |
| 4 | jubarte-final-native | node | 6.758 | 18.89 | 115.966 | 191.954 | 52.9 | 90 | 0 |
| 5 | jubarte-native | node | 4.5 | 7.671 | 33.267 | 47.434 | 130.4 | 90 | 0 |
| 6 | jubarte-third-native | node | 4.469 | 7.55 | 33.212 | 45.323 | 132.4 | 90 | 0 |
| 7 | jubarte-second-native | node | 4.46 | 7.485 | 31.96 | 44.696 | 133.6 | 90 | 0 |
| 8 | jubarte-lossless | node | 2.457 | 6.596 | 37.579 | 58.256 | 151.6 | 90 | 0 |
| 9 | jubarte-third-docxodus | node | 2.364 | 6.031 | 33.763 | 53.804 | 165.8 | 90 | 0 |
| 10 | jubarte-second-docxodus | node | 2.39 | 5.891 | 31.351 | 52.839 | 169.8 | 90 | 0 |
| 11 | docx-redline-js | node | 1.451 | 2.791 | 6.907 | 45.976 | 358.4 | 90 | 0 |

### Large-N `speed_redlines` (`scripts/redline_speed_bench.ts`)

Large fixture pools (often **1000 unique** docs → **5000 pairs**), including native C# Docxodus, jubarte-rust CLI/warm, WASM. Warm workers: `docxodus-csharp-inproc`, `jubarte-rust-inproc`.

| # | tool | runtime | fixtures | pairs | median ms | mean ms | p95 | p99 | /s | n | fail | profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | dotnet-wasm | 200 | 500 | 148.753 | 607.385 | 3212.297 | 7017.889 | 1.6 | 496 | 4 | — |
| 2 | docxodus-csharp | dotnet | 50 | 50 | 208.388 | 441.646 | 911.873 | 1154.008 | 2.3 | 50 | 0 | — |
| 3 | jubarte-lossless | node | 1000 | 5000 | 56.465 | 168.791 | 609.005 | 1049.093 | 5.9 | 4997 | 3 | v8-inspector |
| 4 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.145 | 175.709 | 578.45 | 17.5 | 5000 | 0 | — |
| 5 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.717 | 41.44 | 180.492 | 273.407 | 24.1 | 5000 | 0 | — |
| 6 | jubarte-rust | rust | 1000 | 5000 | 9.656 | 31.022 | 123.386 | 195.751 | 32.2 | 5000 | 0 | — |
| 7 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 7.888 | 25.832 | 101.854 | 206.808 | 38.7 | 4880 | 120 | samply |
| 8 | jubarte-rust-inproc | rust | 1000 | 5000 | 6.201 | 25.337 | 110.764 | 182.306 | 39.5 | 5000 | 0 | samply |

### Speed methodology notes

- Dedup key: `(kind, tool, unit)`. Best re-run by `(n, −median, run_ts)`.
- `speed_redlines` rows with **n < 10** are dropped as trivial smokes.
- Profiles (when present): samply `.profile.json.gz` for native CLIs/workers; V8 `.cpuprofile` for in-process Node (e.g. jubarte-lossless).
- Regenerate after a run: `python3 scripts/export-results-md.py`.

## Methodology notes (fidelity)

- Deduplication: one line per `(vendor, benchmark, tool_version)`. Re-runs of the **same** triple keep the best by `(render_fit, full_corpus_bucket, timestamp, overall_mean)` — prefer playwright for `visual_*` and soffice for script/accepted/roundtrip, then full-corpus lines (n > 100) over smokes, then the newest line (so a 383-doc post-holdout line supersedes a stale 403-doc one).
- **Versions are not collapsed.** docxodus `6.4.0` and `7.0.0` both appear so pins can be compared directly.
- **docxodus** filter: rows with **`n_docs ≤ 100`** are dropped (smoke / partial runs such as `visual_rendering` with n=21 or n=2). Full-corpus pins (typically n ≳ 145) are kept for every version.
- **jubarte-*** filter: rows with **ITT docs < 760** are dropped. A 164-doc subset is not the same measurement as the 763-doc ITT corpus.
- Other vendors keep every version even if n is small (e.g. `prebaked` sanity).
- Scores isolate *redline-markup fidelity vs Word* when candidates and the oracle share the same renderer (LibreOffice 26.2.4.2 for `script_redlines` / `accepted_changes` / `roundtrip`). Playwright `visual_*` scores are not cross-comparable with soffice scores.

## Licensing & legal considerations

These numbers are **independent engineering measurements**, not endorsements, certifications, or claims of compliance with any third-party product.

- **This repository** (scoring core derived from [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks)) is licensed under **AGPL-3.0-only**. See `LICENSE`.
- **Microsoft Word** is a proprietary product of Microsoft. The Word oracle redlines are produced by Word for measurement only; Microsoft is not affiliated with this benchmark and does not endorse these results. Trademarks remain the property of their owners.
- **Benchmarked engines** remain under their own licenses and copyrights; publishing a score does not change their terms:
  - jubarte / in-repo ports — see their package licenses
  - [docxodus](https://github.com/JSv4/docxodus) (MIT)
  - [docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)
  - [folio](https://github.com/stella/folio) (Apache-2.0)
  - [SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0) and related SuperDoc tooling
- **LibreOffice** is used only as a pinned PDF renderer for fair comparison; it is not a redline generator in this bench.
- Redistributing or reusing scores, corpus fixtures, or generated redlines must still respect the licenses of the underlying tools and any corpus rights.

Regenerate: `python3 scripts/export-results-md.py` (reads `results/bench.jsonl` + `results/speed.jsonl`).

<!-- DUAL_PATH_QUALITY:BEGIN -->
## jubarte-first dual-path redline quality (lossless vs via-AST)

_Generated by `scripts/redline_dual_path_report.mjs` from `runs/dual-path-403`. jubarte-first `1d33330` · corpus `64d2f609` · bench `b04b8b5` · Node v26.6.0._

Acceptance gate over the same pairs, judged identically for both engines with the
package-level accept/reject: a pair is `ok` only when every XML part of the redline is
well-formed AND `text(accept(redline)) == text(next)` AND `text(reject(redline)) == text(base)`.
Malformed XML is counted as a hard fail because Word reports it as unreadable content.

| engine | pairs | ok | ok % | well-formed | accept ok | reject ok | compare threw |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jubarte-first-lossless | 403 | 368 | 91.3% | 403 | 390 | 378 | 0 |
| jubarte-first-via-ast | 403 | 352 | 87.3% | 396 | 368 | 365 | 0 |
<!-- DUAL_PATH_QUALITY:END -->
