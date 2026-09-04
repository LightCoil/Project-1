
(() => {
    "use strict";

    const DEFAULT_RELAY = "https://batteries-fabrics-pleased-mitchell.trycloudflare.com";
    const POLL_INTERVAL = 2000;

    let relayUrl = DEFAULT_RELAY;
    let token = "";
    let running = false;

    function log(...args) {
        console.log(
            "[PROJECT-1 Browser Bridge]",
            ...args
        );
    }

    async function loadConfig() {
        try {
            const data = await chrome.storage.local.get([
                "relayUrl",
                "token"
            ]);

            relayUrl =
                data.relayUrl ||
                DEFAULT_RELAY;

            token =
                data.token ||
                "";

            relayUrl = String(relayUrl).replace(/\/+$/, "");

        } catch (error) {
            log("Config error:", error);
        }
    }

    async function authenticatedFetch(
        path,
        options = {}
    ) {
        const headers = new Headers(
            options.headers || {}
        );

        headers.set(
            "X-Bridge-Token",
            token
        );

        headers.set(
            "Cache-Control",
            "no-cache"
        );

        return fetch(
            relayUrl + path,
            {
                ...options,
                headers,
                cache: "no-store",
            }
        );
    }

    function isChatGPTPage() {
        return (
            location.hostname === "chatgpt.com" ||
            location.hostname === "chat.openai.com"
        );
    }

    async function heartbeat() {
        if (!token) {
            log("Bridge token is not configured.");
            return;
        }

        try {
            const response =
                await authenticatedFetch(
                    "/browser/poll"
                );

            if (!response.ok) {
                log(
                    "Heartbeat HTTP error:",
                    response.status
                );
                return;
            }

            const data =
                await response.json();

            if (data.ok) {
                log(
                    "Heartbeat OK",
                    data.pending
                        ? "request pending"
                        : "idle"
                );

                if (data.pending && data.request) {
                    await handleRequest(
                        data.request
                    );
                }
            }

        } catch (error) {
            log(
                "Heartbeat failed:",
                error
            );
        }
    }

    function findComposer() {
        const selectors = [
            "textarea",
            "div[contenteditable='true']",
            "[contenteditable='true'][role='textbox']"
        ];

        for (const selector of selectors) {
            const element =
                document.querySelector(selector);

            if (element) {
                return element;
            }
        }

        return null;
    }

    function setComposerText(
        element,
        text
    ) {
        element.focus();

        if (
            element instanceof HTMLTextAreaElement
        ) {
            const setter =
                Object.getOwnPropertyDescriptor(
                    HTMLTextAreaElement.prototype,
                    "value"
                )?.set;

            if (setter) {
                setter.call(
                    element,
                    text
                );
            } else {
                element.value = text;
            }

            element.dispatchEvent(
                new Event(
                    "input",
                    {
                        bubbles: true
                    }
                )
            );

            return;
        }

        element.textContent = text;

        element.dispatchEvent(
            new InputEvent(
                "input",
                {
                    bubbles: true,
                    inputType: "insertText",
                    data: text,
                }
            )
        );
    }

    function findSendButton() {
        const selectors = [
            "button[data-testid*='send']",
            "button[aria-label*='Send']",
            "button[aria-label*='send']",
            "button[type='submit']"
        ];

        for (const selector of selectors) {
            const button =
                document.querySelector(
                    selector
                );

            if (
                button &&
                !button.disabled
            ) {
                return button;
            }
        }

        return null;
    }

    async function sendToChatGPT(text) {
        if (!isChatGPTPage()) {
            throw new Error(
                "Current tab is not ChatGPT Web."
            );
        }

        const composer =
            findComposer();

        if (!composer) {
            throw new Error(
                "ChatGPT composer was not found."
            );
        }

        setComposerText(
            composer,
            text
        );

        await new Promise(
            resolve =>
                setTimeout(resolve, 300)
        );

        const button =
            findSendButton();

        if (button) {
            button.click();
            return;
        }

        composer.dispatchEvent(
            new KeyboardEvent(
                "keydown",
                {
                    key: "Enter",
                    code: "Enter",
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                }
            )
        );

        await new Promise(
            resolve =>
                setTimeout(resolve, 100)
        );

        composer.dispatchEvent(
            new KeyboardEvent(
                "keyup",
                {
                    key: "Enter",
                    code: "Enter",
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                }
            )
        );
    }

    async function handleRequest(request) {
        if (!request || !request.id) {
            return;
        }

        log(
            "Received orchestrator request:",
            request.id
        );

        const payload =
            request.payload || {};

        const prompt =
            String(
                payload.prompt ||
                payload.message ||
                ""
            ).trim();

        if (!prompt) {
            log(
                "Request contains no prompt."
            );
            return;
        }

        try {
            await sendToChatGPT(
                prompt
            );

            log(
                "Message sent to ChatGPT Web."
            );

            // The actual response extraction is intentionally
            // handled separately. This step proves that PROJECT-1
            // can cross the browser boundary and submit a message
            // into the visible ChatGPT conversation.

        } catch (error) {
            log(
                "Failed to send request:",
                error
            );
        }
    }

    async function start() {
        if (running) {
            return;
        }

        running = true;

        await loadConfig();

        log(
            "PROJECT-1 Browser Bridge started."
        );

        log(
            "Relay:",
            relayUrl
        );

        if (!isChatGPTPage()) {
            log(
                "Waiting for ChatGPT Web page."
            );
        }

        await heartbeat();

        setInterval(
            heartbeat,
            POLL_INTERVAL
        );
    }

    start();

})();
