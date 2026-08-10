# ImageGen hero image — 生成手順と品質基準

Implementation Story のヒーロー画像を生成する直前に読む。生成しない handoff では読まない。

Use Codex ImageGen to create a 16:9 `infographic-diagram` that explains the central causal relationship or operating model. The image must be understandable without reading the surrounding article. Save the selected raster image inside the handoff output source tree, add it as `hero_visual: {path, alt, caption}`, and render it directly below the title and before `at_a_glance`.

## Image specification

Write the image specification with exact, short Japanese text for all five elements below. Prefer five to ten Japanese characters per label and five to seven labels total; do not replace them with generic English.

1. A conclusion-led title that says what the diagram proves.
2. A label for every major step or object.
3. A short condition on every decision branch.
4. A concrete outcome at every endpoint.
5. One takeaway sentence at the bottom.

Use this prompt shape:

```text
Text (verbatim):
- Title: "<結論が分かる日本語>"
- Steps: "<工程1>" / "<工程2>" / "<工程3>"
- Branches: "<条件A>" / "<条件B>"
- Outcomes: "<結果A>" / "<結果B>"
- Takeaway: "<一行結論>"
Constraints: render every quoted Japanese label clearly; no unexplained icons; no English substitution.
```

## Inspection and retry

After generation, inspect the image itself. Reject and regenerate once when any required label is missing, unreadable, garbled, too small, or replaced by English, or when icons and arrows do not make the causal direction clear. For a bridge retry to the same output path, add `--replace`; replacement is atomic and occurs only after the new PNG passes signature verification. If the second result still fails, omit ImageGen and use an HTML/CSS explanatory figure; never accept an attractive but semantically unclear image.

## Runtime invocation

- In Codex, use `$imagegen` and its built-in ImageGen tool.
- In Claude Code or another runtime without Codex ImageGen, first reduce the content to a non-sensitive visual specification. Do not include customer data, personal information, credentials, private source text, or internal identifiers. Save that specification to a local prompt file, then run `scripts/generate-with-codex-imagegen.sh --prompt-file <path> --output <handoff-source>/images/<name>.png`. This invokes `codex exec` ephemerally with the workspace-write sandbox and returns a verified PNG.
- If the bridge, authentication, or image generation fails, continue with the HTML overview. Do not switch to an API-key-based image generator or expose secrets.
