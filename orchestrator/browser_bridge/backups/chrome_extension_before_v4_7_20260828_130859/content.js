(() => {
    "use strict";

    const DEFAULT_RELAY = "https://batteries-fabrics-pleased-mitchell.trycloudflare.com";

    let relayUrl = DEFAULT_RELAY;
    let token = "";

    let activeRequest = null;
    let lastSentPrompt = null;

    function log(...args) {
        console.log(
            "[PROJECT-1 Bridge]",
            ...args
        );
    }

    async function loadSettings() {

        const data =
            await chrome.storage.local.get(
                ["relayUrl", "token"]
            );

        relayUrl =
            data.relayUrl ||
            DEFAULT_RELAY;

        token =
            data.token ||
            "";
    }

    function headers() {

        return {
            "Content-Type":
                "application/json",
            "X-Bridge-Token":
                token
        };
    }

    async function poll() {

        if (!token) {
            return;
        }

        try {

            const response =
                await fetch(
                    relayUrl +
                    "/browser/poll",
                    {
                        method: "GET",
                        headers: headers()
                    }
                );

            if (!response.ok) {
                return;
            }

            const data =
                await response.json();

            if (!data.pending) {
                return;
            }

            const request =
                data.request;

            if (!request ||
                !request.payload) {
                return;
            }

            activeRequest = request;

            await executeChatRequest(
                request
            );

        } catch (error) {

            log(
                "Polling error:",
                error
            );
        }
    }

    function findComposer() {

        const selectors = [
            "textarea",
            "[contenteditable='true']"
        ];

        for (
            const selector
            of selectors
        ) {

            const elements =
                document.querySelectorAll(
                    selector
                );

            for (
                const element
                of elements
            ) {

                const rect =
                    element.getBoundingClientRect();

                if (
                    rect.width > 100 &&
                    rect.height > 20
                ) {
                    return element;
                }
            }
        }

        return null;
    }

    function setComposerValue(
        element,
        text
    ) {

        element.focus();

        if (
            element instanceof
            HTMLTextAreaElement
        ) {

            const setter =
                Object.getOwnPropertyDescriptor(
                    HTMLTextAreaElement.prototype,
                    "value"
                ).set;

            setter.call(
                element,
                text
            );

        } else {

            element.textContent = text;
        }

        element.dispatchEvent(
            new InputEvent(
                "input",
                {
                    bubbles: true,
                    inputType:
                        "insertText",
                    data: text
                }
            )
        );
    }

    function findSendButton() {

        const buttons =
            document.querySelectorAll(
                "button"
            );

        for (
            const button
            of buttons
        ) {

            const text =
                (
                    button.innerText ||
                    button.getAttribute(
                        "aria-label"
                    ) ||
                    ""
                ).toLowerCase();

            const aria =
                (
                    button.getAttribute(
                        "aria-label"
                    ) ||
                    ""
                ).toLowerCase();

            if (
                text.includes("send") ||
                aria.includes("send") ||
                aria.includes("отправ")
            ) {
                return button;
            }
        }

        return null;
    }

    function sendEnter(
        element
    ) {

        element.dispatchEvent(
            new KeyboardEvent(
                "keydown",
                {
                    key: "Enter",
                    code: "Enter",
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                }
            )
        );
    }

    async function waitForResponse() {

        let lastText = "";
        let stableCount = 0;

        const started =
            Date.now();

        while (
            Date.now() - started <
            180000
        ) {

            await new Promise(
                resolve =>
                    setTimeout(
                        resolve,
                        1000
                    )
            );

            const nodes =
                document.querySelectorAll(
                    "[data-message-author-role='assistant']"
                );

            if (nodes.length) {

                const last =
                    nodes[nodes.length - 1];

                const text =
                    (
                        last.innerText ||
                        last.textContent ||
                        ""
                    ).trim();

                if (
                    text &&
                    text === lastText
                ) {

                    stableCount += 1;

                } else {

                    stableCount = 0;
                    lastText = text;
                }

                if (
                    stableCount >= 2
                ) {
                    return text;
                }
            }
        }

        throw new Error(
            "Timed out waiting for ChatGPT response."
        );
    }

    async function executeChatRequest(
        request
    ) {

        const prompt =
            request.payload.prompt;

        if (!prompt) {
            return;
        }

        if (
            prompt === lastSentPrompt
        ) {
            return;
        }

        lastSentPrompt = prompt;

        const composer =
            findComposer();

        if (!composer) {

            log(
                "Chat composer not found."
            );

            return;
        }

        setComposerValue(
            composer,
            prompt
        );

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    300
                )
        );

        const button =
            findSendButton();

        if (button) {

            button.click();

        } else {

            sendEnter(
                composer
            );
        }

        log(
            "Prompt sent to ChatGPT."
        );

        const response =
            await waitForResponse();

        await fetch(
            relayUrl +
            "/browser/response",
            {
                method: "POST",
                headers: headers(),
                body: JSON.stringify(
                    {
                        request_id:
                            request.id,
                        response:
                            response
                    }
                )
            }
        );

        log(
            "ChatGPT response returned."
        );

        activeRequest = null;
    }

    async function start() {

        await loadSettings();

        log(
            "Bridge loaded.",
            relayUrl
        );

        setInterval(
            poll,
            1000
        );
    }

    start();

})();
