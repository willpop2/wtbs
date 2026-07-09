# WTBS suggestion intake → daily email digest (Cloudflare Worker)

Reader edit-suggestions are stored, then **emailed to you once a day** as a single
digest. Nothing is auto-applied — you read the digest and apply the good ones.

```
Reader highlights text → widget POSTs JSON → Worker stores it in KV
                                          → daily cron emails you the batch → queue cleared
```

## What you need
- A **Cloudflare** account (free) with Wrangler: `npm i -g wrangler && wrangler login`
- A **Resend** account (free tier: 100 emails/day) for sending the digest:
  1. Sign up at resend.com, add + verify a sending domain (or use their test sender to your own address while trying it out).
  2. Create an API key.

## Deploy (one time)
From this `worker/` folder:

1. **Create the KV queue** and copy the printed id into `wrangler.toml` (`id = ...`):
   ```
   wrangler kv namespace create SUGGESTIONS
   ```
2. **Edit `wrangler.toml`**: set `MAIL_TO` (your inbox), `MAIL_FROM` (a Resend-verified
   address), `ALLOW_ORIGIN` (your deployed site origin), and the cron time if you like
   (it's UTC).
3. **Add the Resend key** and deploy:
   ```
   wrangler secret put RESEND_API_KEY
   wrangler deploy
   ```
   Wrangler prints the Worker URL, e.g. `https://wtbs-suggest.<you>.workers.dev`.

## Point the site at it
Rebuild so the widget posts to the Worker instead of running in preview mode:
```
WTBS_SUGGEST_ENDPOINT="https://wtbs-suggest.<you>.workers.dev" python build_site.py
```

## Try it
- Submit a suggestion on the site → it's queued (Worker returns `{ok:true, queued:N}`).
- Force a digest without waiting a day: `wrangler tail` to watch, and trigger the
  scheduled handler with `wrangler triggers` or just wait for the cron. (You can also
  temporarily set the cron a minute ahead to test.)

## Notes / options
- **Frequency:** change `crons` in `wrangler.toml` (e.g. twice daily, or weekly).
- **Queue safety:** the queue is only cleared after the email sends successfully, so a
  mail outage just rolls suggestions into the next day.
- **Spam:** the widget has a honeypot + required name/email; the Worker checks Origin.
  Add Cloudflare Turnstile later if needed.
- **Want a searchable archive too?** We can additionally file each suggestion as a
  GitHub issue — say the word and I'll add it back alongside the email.
- **Cost:** comfortably within Cloudflare + Resend free tiers.
