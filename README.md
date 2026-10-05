# FXMacroData for Dify

A Dify tool plugin for [FXMacroData](https://fxmacrodata.com/?utm_source=github&utm_medium=referral&utm_campaign=dify-plugin-fxmacrodata&utm_content=readme): macroeconomic indicators, release calendars and FX rates from official sources (central banks and statistics offices) for 22 currencies.

Source: https://github.com/fxmacrodata/dify-plugin-fxmacrodata

## Tools

| Tool | What it returns | Key needed |
| --- | --- | --- |
| `indicator_history` | Release history for one indicator, e.g. USD `inflation`, EUR `policy_rate`. Optional `start_date`, `end_date`, `limit` (1-100). | No for USD |
| `data_catalogue` | Every indicator available for a currency, with slug, name, unit, frequency, source and coverage. | No for USD |
| `release_calendar` | Upcoming scheduled releases for a currency. Optional `indicator`, `start_date`, `end_date`, `timezone`. | No for USD |
| `forex_rates` | Daily FX spot rates for a pair, e.g. `EUR`/`USD`, from central-bank reference rates. Optional `start_date`, `end_date`, `limit`. | Yes |

Currencies: AUD, BRL, CAD, CHF, CNH, CNY, DKK, EUR, GBP, HUF, ILS, JPY, KRW, MYR, NGN, NOK, NZD, PEN, SEK, THB, TWD, USD.

Each tool returns the API's JSON response unchanged, plus a short text summary for the model.

## Setup

1. Install the plugin from the Dify Marketplace (Plugins > Marketplace, search "FXMacroData").
2. Go to Tools > FXMacroData > Authorize.
3. Leave the API key empty to use USD data, or paste your FXMacroData API key to unlock everything. Keys are on the [subscribe page](https://fxmacrodata.com/subscribe?utm_source=github&utm_medium=referral&utm_campaign=dify-plugin-fxmacrodata&utm_content=readme).

The key is checked with one small request when you save it.

## Credentials

The `api_key` credential is optional and stored by Dify as a secret. The plugin sends it only as the `X-API-Key` request header, never in a URL.

Without a key:

- USD indicators, the USD catalogue and the USD calendar work.
- Data is delayed by 15 minutes. When a newer release is being held back, the response has a `freemium_delay` object and the text summary says so, with the time it becomes available.
- History is limited to the last 90 days. The response then has a `freemium_window` object.
- Other currencies and `forex_rates` return a message asking for a key.

With a key: every currency, full history, real-time releases and FX rates.

## Usage

### Agent apps

Add the FXMacroData tools to an agent and ask things like:

- "What was the latest US CPI print and how does it compare with last month?"
- "When is the next US non-farm payrolls release?"
- "Show EUR/USD over the last 30 days." (needs a key)

The agent can call `data_catalogue` first to find indicator slugs.

### Chatflow and Workflow apps

Add a tool node and fill the parameters directly, e.g. `indicator_history` with `currency = USD`, `indicator = unemployment`, `limit = 12`. Use the JSON output in later nodes; rows are in `data`, most recent first, with `date` and `val`.

## Connection

All requests are HTTPS GET to one fixed host, `https://api.fxmacrodata.com/v1`, with a 20 second timeout. The Dify instance needs outbound access to that host. No other hosts are contacted. API reference: https://fxmacrodata.com/api-docs?utm_source=github&utm_medium=referral&utm_campaign=dify-plugin-fxmacrodata&utm_content=readme

## Privacy

See [PRIVACY.md](PRIVACY.md).

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests
```

`tests/live_check.py` calls each tool once against the live API without a key (USD only).

Package with the Dify plugin CLI:

```bash
dify-plugin plugin package ./dify-plugin-fxmacrodata
```

`.difyignore` keeps tests and dev files out of the package.

## License

MIT
