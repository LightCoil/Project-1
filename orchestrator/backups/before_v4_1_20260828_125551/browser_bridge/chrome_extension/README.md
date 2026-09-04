# PROJECT-1 Browser Chat Bridge v4.0

This directory contains the browser-side transport boundary.

## Architecture

Colab / Orchestrator
        ↓
BrowserChatClient
        ↓
Browser Relay
        ↓
Chrome Extension
        ↓
Visible ChatGPT Web Chat
        ↓
Chrome Extension
        ↓
Browser Relay
        ↓
BrowserChatClient
        ↓
Orchestrator

## Important

The relay does not contain a ChatGPT API key.

The extension operates on the visible ChatGPT web interface.

The orchestrator does not directly call a ChatGPT API.

## Installation

1. Start the relay from Colab.
2. Copy the displayed relay token.
3. Load this directory as an unpacked Chrome extension.
4. Open ChatGPT in Chrome.
5. Open the extension popup.
6. Enter the relay URL and token.
7. Save the settings.
8. Verify that the bridge reports the browser as connected.

## Current status

v4.0 is the transport foundation.

The orchestrator is NOT connected to this bridge automatically yet.

That will be the next integration step after the transport itself is verified.
