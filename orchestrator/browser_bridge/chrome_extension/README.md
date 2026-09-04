PROJECT-1 Browser Chat Bridge v4.7

Relay:
https://batteries-fabrics-pleased-mitchell.trycloudflare.com

Target:
ChatGPT Web

Authentication:
PROJECT-1 relay token via X-Bridge-Token.

IMPORTANT:
This token is NOT a ChatGPT token.
It is only the authentication token of the PROJECT-1 relay.

No ChatGPT API is used.

Installation:

1. Open chrome://extensions
2. Enable Developer mode.
3. Find PROJECT-1 Browser Chat Bridge.
4. Click Reload.
5. If not installed, choose Load unpacked.
6. Select this directory:
   /content/Project-1/orchestrator/browser_bridge/chrome_extension
7. Open ChatGPT Web in a normal tab.
8. Open the extension popup.
9. Enter the PROJECT-1 Bridge Token printed by Colab.
10. Save configuration.
11. Reload the ChatGPT tab.

The extension sends a heartbeat every 2 seconds
to:

GET /browser/poll

using:

X-Bridge-Token: <PROJECT-1 relay token>

Once the relay receives the heartbeat,
browser_connected becomes True.

No ChatGPT credentials are collected.
No ChatGPT cookies are extracted.
No ChatGPT API endpoint is called.
