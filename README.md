# PCX Booking Watcher (BookMyShow + Telegram)

This is a starter GitHub Actions watcher configured with the BookMyShow URLs you supplied for **Avengers: Doomsday, Hyderabad**.

## What it does

- Opens the configured BookMyShow booking and seat-layout pages with a headless Chromium browser.
- Checks booking-page text for the `PCX` keyword.
- Checks seat-page text and common seat accessibility/class attributes for best-effort seat-state signals.
- Sends a Telegram message when a monitored page changes.
- Runs on a GitHub Actions schedule configured for every 5 minutes, plus manual runs.
- Can be reused by replacing the URLs and movie name in `config.json`.

## Important limitations (read this)

1. **This is not a guaranteed instant or guaranteed-complete ticket monitor.** GitHub scheduled jobs can start late, and BookMyShow may block automated requests, change its page structure, or render seat maps in a way that does not expose seat states to the browser.
2. The script does **not** buy tickets, reserve seats, bypass queues, solve CAPTCHAs, or evade access controls.
3. A page-change alert is not automatically proof that booking has opened. Open the supplied link and verify the show and seats yourself.
4. The seat-count parser is best-effort. If BookMyShow changes its markup or draws the map in a canvas, the count will be `null` rather than inventing a number.
5. The December 18 screenshot you supplied visibly labels the selected show `Infinity Vision 3D/PCX Screen`. The supplied December 18 and 19 seat-layout URLs are configured as user-provided PCX reference pages; the script cannot independently prove the auditorium from the URL alone.

## Setup

### 1. Create a GitHub repository

1. Open https://github.com/new
2. Create a repository, for example `pcx-booking-watcher`.
3. Choose **Public** or **Private**. Private is fine.
4. Create the repository.

### 2. Upload these files

Upload the contents of this ZIP to the repository, preserving this structure:

```text
pcx-booking-watcher/
├── .github/
│   └── workflows/
│       └── pcx-watcher.yml
├── config.json
├── requirements.txt
├── watcher.py
└── README.md
```

### 3. Create a Telegram bot

1. In Telegram, open `@BotFather`.
2. Send `/newbot` and follow its instructions.
3. Copy the bot token. Keep it private.
4. Open your new bot and press **Start**.
5. To get your chat ID, send a message to your bot, then open:
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
6. Find the `chat.id` number in the response. Do not share your token publicly.

### 4. Add GitHub repository secrets

In your repository:
**Settings → Secrets and variables → Actions → New repository secret**

Add:

- `TELEGRAM_BOT_TOKEN` = token from BotFather
- `TELEGRAM_CHAT_ID` = your Telegram chat ID

Never put these values in `config.json`, source code, screenshots, or public messages.

### 5. Run a test

Go to **Actions → PCX Booking Watcher → Run workflow**.

The first run may send an initial status notification for each URL. Check the workflow log for page errors or `PCX not confirmed on page`.

### 6. Enable scheduled runs

GitHub Actions must be enabled for the repository. The schedule is already set to every five minutes. GitHub may delay scheduled runs, especially during high-load periods; it is not a precise 5-minute guarantee.

## Reuse for another movie

Edit `config.json`:

- Change `movie`.
- Replace the `booking_pages` URLs with the new movie's BookMyShow event/date pages.
- Add seat-layout URLs only after selecting the exact PCX show.
- Keep `screen_keyword` as `PCX Screen` if BookMyShow uses that label.

For ALLU Dolby Screen 1, use a separate config/keyword or a separate copy of this repository. Do not mix screen keywords in the same configuration until the exact auditorium label is confirmed.

## Current configured reference URLs

- Dec 17 booking page: user-supplied.
- Dec 19 booking page: user-supplied.
- Dec 18 seat layout: user-supplied; screenshot shows the PCX label on the selected show.
- Dec 19 seat layout: user-supplied after selecting the PCX show.

## Troubleshooting

- **No Telegram message:** confirm both repository secrets and that you pressed Start on the bot.
- **PCX not confirmed:** inspect the workflow log and open the booking page manually. BookMyShow may have changed the text or blocked the automated browser.
- **Seat count is null:** the seat map may be rendered in a canvas/SVG or use different attributes. The page-change alert can still work, but seat counting needs a fresh inspection of the current page structure.
- **No workflow runs:** ensure Actions are enabled and the workflow file is on the repository's default branch.
