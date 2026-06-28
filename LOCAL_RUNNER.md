# Local 1ck.org Runner

`1ck.org` can fail on GitHub hosted runners when the captcha image is not served correctly. GitHub Actions now runs `site1` only. Run `site2` from the local WSL host instead.

## Local env file

Create this file on the local WSL host:

```bash
mkdir -p ~/.config/auto-checkin
cp config/site2.env.example ~/.config/auto-checkin/site2.env
chmod 600 ~/.config/auto-checkin/site2.env
```

Then fill `~/.config/auto-checkin/site2.env` locally. Do not commit the real env file.

## Manual test

```bash
bash scripts/run-site2-local.sh
```

The runner creates `.venv`, installs Python dependencies, installs Chromium for Playwright, loads the local env file, and runs only `site2`.

## Install local cron

Run this only after the manual test passes:

```bash
bash scripts/install-site2-cron.sh
```

Default cron is `30 0 * * *` in the local host timezone. Override it with `AUTO_CHECKIN_CRON` if needed:

```bash
AUTO_CHECKIN_CRON="45 0 * * *" bash scripts/install-site2-cron.sh
```
