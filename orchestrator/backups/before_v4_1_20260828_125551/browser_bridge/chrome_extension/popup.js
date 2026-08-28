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

        const saved =
            await chrome.storage.local.get(
                [
                    "relayUrl",
                    "token"
                ]
            );

        if (saved.relayUrl) {
            relay.value =
                saved.relayUrl;
        }

        if (saved.token) {
            token.value =
                saved.token;
        }

        document
            .getElementById("save")
            .addEventListener(
                "click",
                async () => {

                    await chrome.storage.local.set(
                        {
                            relayUrl:
                                relay.value.trim(),
                            token:
                                token.value.trim()
                        }
                    );

                    status.textContent =
                        "Saved.";
                }
            );
    }
);
