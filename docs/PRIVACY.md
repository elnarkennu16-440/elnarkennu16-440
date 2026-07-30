# Portrait Privacy

The generator is designed so the original portrait does not need to enter Git history.

## Recommended Workflow

1. Store the transparent portrait outside the repository.
2. Pass its absolute path to `npm run setup` or `npm run generate`.
3. Commit only `profile.config.json`, `README.md`, and generated files in `assets/hero/`.

## Before Every Commit

```bash
git status --short
git ls-files | grep -Ei 'portrait|source.*\.(png|jpe?g)$' || true
```

Inspect every new image intentionally. The generated SVG files contain an ASCII interpretation of the portrait and are public by design.

## Included Ignore Rules

The repository ignores:

- `input/`
- `portrait-source.*`
- `*.source.png`
- `*.source.jpg`
- `*.source.jpeg`

These patterns reduce accidental commits but do not replace reviewing `git status`.

## Public Information

Everything in `profile.config.json` is intended to be committed. Do not put private email addresses, private repositories, credentials, unpublished research, or confidential employer information in that file.
