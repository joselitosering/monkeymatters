#!/usr/bin/env node
/**
 * ONE-TIME local helper — run this yourself, on your own machine, whenever
 * you need a fresh Schwab refresh_token (initial setup, and again roughly
 * every 7 days when the previous one expires — Schwab confirmed there is no
 * way to renew a refresh_token programmatically past 7 days, so this manual
 * step is unavoidable, not a workaround for something better).
 *
 * This script is NEVER meant to run in GitHub Actions or any unattended
 * context — it needs YOUR browser and YOUR Schwab login. Nothing in this
 * file is committed with real credentials; you type them in each run.
 *
 * Usage:
 *   node get_refresh_token.mjs
 *
 * What it does:
 *   1. Prompts for your Schwab app's Client ID, Client Secret, and the
 *      Callback URL you registered for this app (e.g. https://127.0.0.1).
 *   2. Prints an authorization URL — open it in your browser, log in to
 *      Schwab, and approve access for the "Market Data" product.
 *   3. Schwab redirects your browser to your Callback URL with a ?code=...
 *      parameter. That page will likely show a browser error (nothing is
 *      actually listening on 127.0.0.1) — that's expected. Copy the FULL
 *      URL from your browser's address bar anyway; the code is in it.
 *   4. Paste that full URL back into this script when prompted.
 *   5. This script exchanges the code for tokens and prints your
 *      refresh_token — copy that into the FINNHUB_API_KEY-style GitHub
 *      secret named SCHWAB_REFRESH_TOKEN (see generate_snapshot.mjs).
 *
 * Nothing here is saved to disk — if you close the terminal, you'll need to
 * re-run this and go through the browser step again.
 */

import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';

const rl = createInterface({ input: stdin, output: stdout });

function ask(question) {
  return rl.question(question);
}

async function main() {
  console.log('\n=== Schwab Trader API — One-Time Refresh Token Setup ===\n');

  const clientId = (await ask('Client ID (App Key): ')).trim();
  const clientSecret = (await ask('Client Secret: ')).trim();
  const callbackUrl = (await ask('Callback URL registered for this app (e.g. https://127.0.0.1): ')).trim();

  const authUrl = `https://api.schwabapi.com/v1/oauth/authorize?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(callbackUrl)}`;

  console.log('\n--- Step 1 ---');
  console.log('Open this URL in your browser, log in to Schwab, and approve access:\n');
  console.log(authUrl);
  console.log('\nAfter approving, your browser will redirect to your Callback URL.');
  console.log('That page will likely show a browser error (connection refused / not secure)');
  console.log('— that is EXPECTED, nothing is running on that address. Ignore the error,');
  console.log('just copy the FULL URL from the address bar (it contains ?code=...).\n');

  const redirectedUrl = (await ask('--- Step 2 ---\nPaste the full redirected URL here: ')).trim();

  let code;
  try {
    const parsed = new URL(redirectedUrl);
    code = parsed.searchParams.get('code');
  } catch {
    console.error('\nCould not parse that as a URL. Make sure you pasted the entire address bar contents.');
    rl.close();
    process.exit(1);
  }

  if (!code) {
    console.error('\nNo ?code= parameter found in that URL. Did the redirect actually happen? Try again from Step 1.');
    rl.close();
    process.exit(1);
  }

  console.log('\n--- Step 3 --- Exchanging code for tokens...\n');

  const basicAuth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: callbackUrl,
  });

  try {
    const res = await fetch('https://api.schwabapi.com/v1/oauth/token', {
      method: 'POST',
      headers: {
        Authorization: `Basic ${basicAuth}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body.toString(),
    });

    const text = await res.text();
    if (!res.ok) {
      console.error(`HTTP ${res.status} ${res.statusText}\n${text}`);
      rl.close();
      process.exit(1);
    }

    const data = JSON.parse(text);
    console.log('SUCCESS. Save these now — the refresh_token is what goes into GitHub Secrets:\n');
    console.log('  refresh_token (-> GitHub secret SCHWAB_REFRESH_TOKEN):');
    console.log(`  ${data.refresh_token}\n`);
    console.log('  access_token (valid 30 min, informational only, generate_snapshot.mjs');
    console.log('  will fetch its own each run using the refresh_token above):');
    console.log(`  ${data.access_token}\n`);
    console.log('This refresh_token is valid for ~7 days. When it stops working, re-run');
    console.log('this script to get a new one and update the GitHub secret again.');
  } catch (e) {
    console.error('Token exchange failed:', e.message);
    process.exit(1);
  }

  rl.close();
}

main();
