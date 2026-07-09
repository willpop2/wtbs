# WTBS suggestion intake → daily email digest (Cloudflare Worker)

Reader edit-suggestions are stored, then **emailed to you once a day** as a single
digest. Nothing is auto-applied — you read the digest and apply the good ones.

```
Reader highlights text → widget POSTs JSON → Worker stores it in KV
                                          → daily cron emails you the batch → queue cleared
```

## Deployed setup (live)

| Thing | Value |
| --- | --- |
| Worker URL | `https://wtbs-suggest.willpop2.workers.dev` |
| Cloudflare account | `wilson.price@gmail.com` (id `f69e2f6e95bb7fe8ede8cb5fcaebce38`) |
| workers.dev subdomain | `willpop2` |
| KV namespace `SUGGESTIONS` | id `0dea830aaffa4483ba59bf66a23db2ed` |
| Digest to (`MAIL_TO`) | `wilson.price@gmail.com` |
| Sender (`MAIL_FROM`) | `onboarding@resend.dev` (Resend test sender) |
| Allowed origin (`ALLOW_ORIGIN`) | `https://willpop2.github.io` |
| Cron | `0 14 * * *` (14:00 UTC ≈ 9–10am ET) |
| `RESEND_API_KEY` | set as a Worker secret (not in this repo) |

The site is already wired to this Worker: `build_site.py` defaults
`WTBS_SUGGEST_ENDPOINT` to the URL above, so `python build_site.py` keeps the
"Suggest an edit" button live without any extra flags.

> **Resend test-sender limit:** `onboarding@resend.dev` only delivers to the
> Resend account's own address (`wilson.price@gmail.com`). To send to other
> recipients or from a branded address, verify a domain in Resend and update
> `MAIL_FROM` (and optionally `MAIL_TO`) in `wrangler.toml`, then redeploy.

## Everyday operations

Run these from this `worker/` folder (`npx` needs no global install).

**Redeploy after editing the Worker or `wrangler.toml`:**
```
npx wrangler deploy
```

**Rotate the Resend key** (delete the old one in Resend → create a new one):
```
npx wrangler secret put RESEND_API_KEY   # paste the new re_... key at the prompt
```

**Watch live logs** (intake + scheduled runs):
```
npx wrangler tail
```

**Inspect / clear the pending queue:**
```
npx wrangler kv key get pending  --namespace-id 0dea830aaffa4483ba59bf66a23db2ed --remote
npx wrangler kv key put pending "[]" --namespace-id 0dea830aaffa4483ba59bf66a23db2ed --remote
```

**Force a digest now (without waiting for the cron)** — sends the real email via
the deployed secret, then clears the queue if Resend accepts it:
```
npx wrangler dev --remote --test-scheduled --port 8799
# in another shell:
curl "http://127.0.0.1:8799/__scheduled?cron=0+14+*+*+*"
```

## Rebuilding from scratch (if the KV id / account ever change)

1. Create the KV queue and paste the printed id into `wrangler.toml` (`id = ...`):
   ```
   npx wrangler kv namespace create SUGGESTIONS
   ```
2. Set `MAIL_TO`, `MAIL_FROM`, `ALLOW_ORIGIN`, and the cron in `wrangler.toml`.
3. Add the Resend key and deploy:
   ```
   npx wrangler secret put RESEND_API_KEY
   npx wrangler deploy
   ```
4. If the Worker URL changed, update the default in `build_site.py`
   (`SUGGEST_ENDPOINT`) and rebuild + push the site.

## Notes / options
- **Frequency:** change `crons` in `wrangler.toml` (e.g. twice daily, or weekly),
  then `npx wrangler deploy`.
- **Queue safety:** the queue is only cleared after the email sends successfully,
  so a mail outage just rolls suggestions into the next day.
- **Spam:** the widget has a honeypot + required name/email; the Worker checks
  Origin against `ALLOW_ORIGIN`. Add Cloudflare Turnstile later if needed.
- **Want a searchable archive too?** We can additionally file each suggestion as a
  GitHub issue — say the word and I'll add it alongside the email.
- **Cost:** comfortably within Cloudflare + Resend free tiers.
