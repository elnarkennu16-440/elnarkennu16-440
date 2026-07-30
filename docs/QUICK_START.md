# Quick Start

## Before You Begin

You need:

- A GitHub account.
- Node.js 20 or newer.
- Git.
- A head-to-torso PNG with a genuinely transparent background.

Your source portrait should ideally be at least 1200 pixels tall, well lit, and separated cleanly from the background.

## 1. Create Your Profile Repository

On the starter repository, click **Use this template**, select **Create a new repository**, and choose your personal GitHub account as the owner. Name the new public repository exactly after your username.

For example, the user `octocat` must create `octocat/octocat`.

Do not name it `my-profile`, `github-readme`, or `portfolio`; GitHub will treat those as normal repositories instead of a Profile README. Do not clone the starter repository directly: create your own profile repository from the template first.

## 2. Clone Your New Repository

Clone the profile repository you just created. For example, if your username is `octocat`:

```bash
git clone https://github.com/octocat/octocat.git
cd octocat
npm ci
```

Replace every `octocat` with your own GitHub username. `npm ci` installs the exact dependency versions recorded in the included lockfile.

## 3. Keep the Portrait Private

The safest option is to keep your portrait outside the repository:

```text
~/Pictures/profile-transparent.png
```

The generator reads the file and emits ASCII SVG assets. It never copies the source image.

## 4. Generate the Profile

Use the guided wizard:

```bash
npm run setup
```

The wizard asks for your public profile content and the absolute portrait path. It then updates `profile.config.json`, creates four responsive SVG assets, and replaces the starter `README.md` with your generated profile.

Or edit `profile.config.json` and run:

```bash
npm run generate -- --source ~/Pictures/profile-transparent.png
```

The command creates four SVG variants and rewrites `README.md` as your profile.

## 5. Review

```bash
npm run check
git status --short
```

Open the generated desktop and mobile SVG files from `assets/hero/`. Check both dark and light variants.

Make sure:

- Your face and upper body are recognizable.
- The ambient background does not overpower the portrait.
- Hero values are factual and concise.
- Project links are correct.
- No source portrait appears in `git status`.

## 6. Publish

```bash
git add README.md profile.config.json assets/hero
git commit -m "feat: create my GitHub profile"
git push origin main
```

Visit `https://github.com/YOUR_USERNAME` and confirm the README appears above pinned repositories.

## 7. Enable Activity Updates

The included workflow runs only when the repository name matches its owner. If `activity.enabled` is `true`, GitHub Actions can update the bounded Recent Activity section without modifying curated profile content.

Open the Actions tab once and enable workflows if GitHub asks you to approve them for a repository created from a template.
