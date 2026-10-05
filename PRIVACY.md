# Privacy

## What the plugin sends

When a tool runs, the plugin makes an HTTPS GET request to `api.fxmacrodata.com` containing:

- the tool parameters: currency codes, indicator slug, dates, limit and timezone;
- your FXMacroData API key in the `X-API-Key` header, if you added one.

Nothing else is sent. The plugin does not send your prompts, conversation, files or Dify user details.

## What the plugin stores

Nothing. The plugin does not collect, store or log user data. Your API key is stored by Dify as an encrypted credential, not by the plugin.

## Third parties

Requests go only to FXMacroData (api.fxmacrodata.com). The data is not shared with any other service by the plugin. FXMacroData's handling of API requests is covered by its privacy policy: https://fxmacrodata.com/privacy?utm_source=github&utm_medium=referral&utm_campaign=dify-plugin-fxmacrodata&utm_content=privacy

## Contact

info@fxmacrodata.com
