# Tender Alert Bot (BPPA/CPTU → Telegram)

## Setup (10 minutes)
1. **Telegram bot**: message @BotFather → /newbot → copy the token.
2. **Chat ID**: send any message to your bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id`.
3. **GitHub**: create a new private repo, upload all files in this folder
   (keep the `.github/workflows` path).
4. Repo → Settings → Secrets and variables → Actions → add
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
5. Repo → Actions → "Tender alert" → Run workflow. It then runs daily at 9am Dhaka time.

## Before first run: check config.json
Open https://www.bppa.gov.bd in your browser, go to the consulting-services
advertisement list, and paste that list page URL (and extra pages) into
`listing_urls`. Detail pages look like `.../advertisement-services/details-7441.html`.

## Local test
pip install -r requirements.txt
python scraper.py --dry
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python scraper.py --test

## Tuning
Edit keywords in config.json. The first run may send many alerts (all
currently listed items); later runs only send new ones.
"# tender-alert-bot" 
