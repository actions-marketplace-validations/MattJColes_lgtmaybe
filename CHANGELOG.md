# Changelog

## [0.0.2](https://github.com/MattJColes/lgtmaybe/compare/lgtmaybe-v0.0.1...lgtmaybe-v0.0.2) (2026-06-07)


### Features

* add local CLI review mode + user-level config ([f0b8035](https://github.com/MattJColes/lgtmaybe/commit/f0b803553178eb89f0ca99cef6547474f4e39f0c))
* agent output format + local AI-fix loop ([425ac2a](https://github.com/MattJColes/lgtmaybe/commit/425ac2a34b2cd26b15ae77119763f72869431220))
* agent output format + local AI-fix loop; drop CLI-posting ollama workflow ([6325033](https://github.com/MattJColes/lgtmaybe/commit/63250336ecda254d1001db5ab9febee81b73888b))
* configurable timeout, drop cost from summary, unblock small local models ([5b79c4e](https://github.com/MattJColes/lgtmaybe/commit/5b79c4e3ea2e319f7b1f47bf9e919e7b44844898))
* configurable timeout, drop cost summary, unblock small local models ([239a93a](https://github.com/MattJColes/lgtmaybe/commit/239a93a4f08f0462e9a2449c30a45f6b5ebb55fa))
* deterministic reviews (temperature=0) + skippable reflection ([d214d38](https://github.com/MattJColes/lgtmaybe/commit/d214d3874643d3a494b70787958a2df2ff4fabd9))
* deterministic reviews (temperature=0) and skippable reflection ([91d8131](https://github.com/MattJColes/lgtmaybe/commit/91d81317bb016660be61ee7c96a5370560311b96))
* eval harness — measure whether a model produces usable reviews ([e928cb0](https://github.com/MattJColes/lgtmaybe/commit/e928cb02759b24f94c0db8bdb9a871e10e1d5a06))
* eval harness — measure whether a model produces usable reviews ([3a37efd](https://github.com/MattJColes/lgtmaybe/commit/3a37efda56fdd54dfc2d6c5f44797f463003ddd5)), closes [#27](https://github.com/MattJColes/lgtmaybe/issues/27)
* expand reviewer scan coverage (logic, tests, docs) and refresh docs ([50a8eca](https://github.com/MattJColes/lgtmaybe/commit/50a8eca14ac50ed13ba8285676a9e99b85072703))
* expand reviewer scan coverage (logic, tests, docs) and refresh docs ([38ea0f9](https://github.com/MattJColes/lgtmaybe/commit/38ea0f927e8a843af7a49d8f2fb8d38800d3825a))
* expose timeout and temperature as GitHub Action inputs ([fab5282](https://github.com/MattJColes/lgtmaybe/commit/fab5282a8207c9aa92fcacff132d5a24784aa8ce))
* expose timeout and temperature as GitHub Action inputs ([1641883](https://github.com/MattJColes/lgtmaybe/commit/164188349def4b361ae85d3440f7f2830107f482))
* local CLI review mode + user-level config ([5613c5e](https://github.com/MattJColes/lgtmaybe/commit/5613c5e33a0259661e130f90a6f1c60266f9f16d))
* parallel tracks — providers, github, engine, config/CLI, docs ([8f9e2cd](https://github.com/MattJColes/lgtmaybe/commit/8f9e2cd25c5e5e2db1ed255b23ce5660a6bb8e09))
* parallel tracks — providers, github, engine, config/CLI, docs ([3baffb6](https://github.com/MattJColes/lgtmaybe/commit/3baffb66dd4db5cd1857849c54a271a01db45d0d))
* per-category fan-out; remove cost cap and approximate cost ([4a54f97](https://github.com/MattJColes/lgtmaybe/commit/4a54f97809c38a0b71848aac63a234b99175a42f))
* per-category fan-out; remove cost cap and approximate cost ([d0536d9](https://github.com/MattJColes/lgtmaybe/commit/d0536d91475a9a38cc1a5f0d7981f83854b4f2eb))
* review diff hunks with surrounding context lines ([1849198](https://github.com/MattJColes/lgtmaybe/commit/184919885cb76e8f608ed8959b6030897f11ab49))
* review diff hunks with surrounding context lines ([07adc5e](https://github.com/MattJColes/lgtmaybe/commit/07adc5e72b549c124a9597a7ae7e50e7ba9adc12))
* step 3 integration — real adapters, slash commands, guards ([4c33a19](https://github.com/MattJColes/lgtmaybe/commit/4c33a190adbd495cb3d32d7154a66b348a7cb42f))
* step 4 packaging — Action, release pipeline, examples, current models ([c60f0dc](https://github.com/MattJColes/lgtmaybe/commit/c60f0dcc099673bbc507511b1cb5407ffc907784))
* step 4 packaging — action.yml, release pipeline, examples, current models ([3a406fe](https://github.com/MattJColes/lgtmaybe/commit/3a406fe8fdfd952b19b7ddcc15d7f376a46a9926))
* structured output for the reflection pass ([c902f10](https://github.com/MattJColes/lgtmaybe/commit/c902f10d8e9c47b7af12c3bbfc14a6e7005339e5))
* structured output for the reflection pass ([4446ffb](https://github.com/MattJColes/lgtmaybe/commit/4446ffb42f7de058e36527e6af8aa92a2ecd77a6))
* structured outputs — constrain models to valid findings JSON ([39d1958](https://github.com/MattJColes/lgtmaybe/commit/39d1958ea5218a5c68797af7a299189b4933b7bd))
* structured outputs — constrain models to valid findings JSON ([413f582](https://github.com/MattJColes/lgtmaybe/commit/413f582bebdb8c11bc1a1536846dd600e84bae59)), closes [#27](https://github.com/MattJColes/lgtmaybe/issues/27)
* wire step 3 integration — real adapters, slash commands, guards ([4c13ec8](https://github.com/MattJColes/lgtmaybe/commit/4c13ec810c406046277aeb3e0b08e355dd320654))


### Bug Fixes

* reliable local reviews — provider-aware timeout/concurrency + fail loud ([d3e0ccc](https://github.com/MattJColes/lgtmaybe/commit/d3e0cccc43fe55c4cc92adfea5163f3d10c4f6c6))
* reliable local reviews — provider-aware timeout/concurrency + fail loud ([8f8474b](https://github.com/MattJColes/lgtmaybe/commit/8f8474b8966a5a9b8550cf7f4ac713b6eebf584d))
* use the factory-resolved model string at completion time ([311d31b](https://github.com/MattJColes/lgtmaybe/commit/311d31b978684d299b78172f25c45714c61c09e4))


### Dependencies

* bump litellm in the python-dependencies group ([8e105f1](https://github.com/MattJColes/lgtmaybe/commit/8e105f12c224c984e0bfa2734094311d88a92d03))


### Documentation

* add CONTRIBUTING.md ([dee443e](https://github.com/MattJColes/lgtmaybe/commit/dee443e02d22fc605382f6462704aa3b8149a4d6))
* add project logo ([c9dcdab](https://github.com/MattJColes/lgtmaybe/commit/c9dcdab9f920271a96ddd2d33a587ea33db6f2db))
* add project logo ([5368472](https://github.com/MattJColes/lgtmaybe/commit/53684728e8c7c1a5f3c81b49efcee49c02ed3548))
* add raster favicons and apple-touch-icon ([a302a32](https://github.com/MattJColes/lgtmaybe/commit/a302a32751561e144fa021fd64ff339fa9c5a859))
* drop max_cost_usd from the user-facing scope summary ([dbad25b](https://github.com/MattJColes/lgtmaybe/commit/dbad25b551e9d96fdd13a7fd771d42b6041ee934))
* explain what gets reviewed, scoping, and output shape ([b43d0b3](https://github.com/MattJColes/lgtmaybe/commit/b43d0b3789f6bb4c5e1c02fdc143304295c3efe5))
* fix CLI usage for the local-only review command ([7e37abb](https://github.com/MattJColes/lgtmaybe/commit/7e37abba2e68ec89c2185a0b9e7bff49baf5b30f))
* fold manual-steps.md into docs/, delete the file ([c69ae5c](https://github.com/MattJColes/lgtmaybe/commit/c69ae5ca2a8f215e41216cd17d290808b1bda244))
* homepage — cover local + Action review, bullet the functionality ([2fb0e58](https://github.com/MattJColes/lgtmaybe/commit/2fb0e58b369912bc4a33d5f7eb301bd87a67dd93))
* homepage copy — tagline, functionality bullets, local + Action review ([02c9e00](https://github.com/MattJColes/lgtmaybe/commit/02c9e001d35564e76c6b0a596c48825e2169c761))
* host the docs on GitHub Pages via MkDocs Material ([9e11a46](https://github.com/MattJColes/lgtmaybe/commit/9e11a46521c6d6c8d064f71df0e532b9a3d84fec))
* left-align homepage tagline ([d85597d](https://github.com/MattJColes/lgtmaybe/commit/d85597d06f7432512de62c2ba48f785219b893ef))
* make the inline/summary feature a paragraph, not a bullet ([0cddca3](https://github.com/MattJColes/lgtmaybe/commit/0cddca3150492b5067875a3ba442831427adc052))
* make the inline/summary feature a paragraph, not a bullet ([1ee8145](https://github.com/MattJColes/lgtmaybe/commit/1ee81453f07922dccaf47b4ae4eeac65dc4cad7e))
* **ollama:** replace codellama with current model recommendations ([0bbe319](https://github.com/MattJColes/lgtmaybe/commit/0bbe319beedd73dee27c8fba986f39f13020a1ce))
* record step 4 packaging in CLAUDE.md ([9db1ba7](https://github.com/MattJColes/lgtmaybe/commit/9db1ba7d60093db62585c961a9b37ba45503bd18))
* theme to logo colours, center hero, note context-line review ([0956e61](https://github.com/MattJColes/lgtmaybe/commit/0956e617bff3625513c26472479d7977815dd7bd))
* theme to logo colours, center hero, note context-line review ([b831b1e](https://github.com/MattJColes/lgtmaybe/commit/b831b1eaf9848e43fb87d03f1650ca9003e68894))
* trim manual-steps to remaining human-only actions ([8ccd3d5](https://github.com/MattJColes/lgtmaybe/commit/8ccd3d5f9e98071f012121cb789e4567cc7a4aa6))

## Changelog
