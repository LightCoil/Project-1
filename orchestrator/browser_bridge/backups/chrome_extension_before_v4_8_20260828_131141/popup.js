
document.addEventListener(
    "DOMContentLoaded",
    async () => {

        const relay =
            document.getElementById(
                "relay"
            );

        const token =
            document.getElementById(
                "token"
            );

        const status =
            document.getElementById(
                "status"
            );

        const DEFAULT_RELAY =
            "https://batteries-fabrics-pleased-mitchell.trycloudflare.com";

        const saved =
            await chrome.storage.local.get([
                "relayUrl",
                "token"
            ]);

        relay.value =
            saved.relayUrl ||
            DEFAULT_RELAY;

        token.value =
            saved.token ||
            "";

        document
            .getElementById("save")
            .addEventListener(
                "click",
                async () => {

                    await chrome.storage.local.set({
                        relayUrl:
                            relay.value.trim(),
                        token:
                            token.value.trim()
                    });

                    status.textContent =
                        "Configuration saved.";

                }
            );
    }
);
