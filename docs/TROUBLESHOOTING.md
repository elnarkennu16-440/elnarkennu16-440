# Troubleshooting

## The generator says my portrait is not transparent

A PNG file can still contain a solid background. The generator requires an alpha channel with actual transparent pixels. Remove the background, export as PNG, and try again.

## The portrait looks too small

Crop the source more tightly around the head and torso before removing the background. Large transparent margins are trimmed automatically, but a small subject inside a complex cutout still reduces useful detail.

## The portrait looks noisy

Use a cleaner cutout with clear lighting. Hair, face, and clothing should have visible tonal separation. Avoid translucent shadows, leftover background fragments, and highly patterned clothing.

## Text is cut off in the terminal panel

Shorten `headline`, `research.direction`, `research.themes`, or project `heroLabel` values. `npm run check` validates hard limits, but shorter copy usually looks better than copy at the maximum.

## GitHub still displays an older image

Run the full generator again. Asset filenames are derived from configuration and portrait content, so any real change creates a new URL and bypasses the old cached asset.

## The README does not appear on my profile

Confirm all of the following:

- The repository is public.
- The repository is owned by your personal account.
- The repository name exactly matches your GitHub username.
- `README.md` exists on the default branch.

## Recent Activity does not update

Confirm `activity.enabled` is `true`, enable Actions for the repository, and run the workflow manually once. The scheduled job intentionally skips repositories whose name does not match the owner.

## `npm install` fails

Check `node --version`. This project requires Node.js 20 or newer. Delete `node_modules`, keep `package-lock.json`, and retry `npm ci` or `npm install`.
