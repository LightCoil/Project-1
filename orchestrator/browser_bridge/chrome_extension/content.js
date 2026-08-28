
(() => {

    const TAG = "[PROJECT-1 CONTENT]";

    let activeRequest = null;
    let observer = null;
    let responseTimer = null;

    function log(...args) {
        console.log(TAG, ...args);
    }

    function normalizeText(text) {
        return String(text || "")
            .replace(/\u200b/g, "")
            .replace(/\r/g, "")
            .trim();
    }

    function findComposer() {

        const selectors = [
            "textarea#prompt-textarea",
            "textarea[placeholder*='Ask']",
            "textarea",
            "[contenteditable='true']"
        ];

        for (const selector of selectors) {
            const nodes =
                document.querySelectorAll(selector);

            for (const node of nodes) {

                const rect =
                    node.getBoundingClientRect();

                const style =
                    window.getComputedStyle(node);

                if (
                    rect.width > 0 &&
                    rect.height > 0 &&
                    style.visibility !== "hidden" &&
                    style.display !== "none"
                ) {
                    return node;
                }
            }
        }

        return null;
    }

    function findSendButton() {

        const selectors = [
            "button[aria-label='Send message']",
            "button[data-testid*='send']",
            "button[aria-label*='Send']"
        ];

        for (const selector of selectors) {

            const node =
                document.querySelector(selector);

            if (!node) {
                continue;
            }

            const rect =
                node.getBoundingClientRect();

            if (
                rect.width > 0 &&
                rect.height > 0
            ) {
                return node;
            }
        }

        return null;
    }

    function assistantMessages() {

        const selectors = [
            "[data-message-author-role='assistant']",
            "[data-message-author-role='assistant'] div",
            "article"
        ];

        const result = [];

        for (const selector of selectors) {

            const nodes =
                document.querySelectorAll(selector);

            for (const node of nodes) {

                const text =
                    normalizeText(
                        node.innerText
                    );

                if (text.length > 0) {
                    result.push(node);
                }
            }

            if (result.length > 0) {
                break;
            }
        }

        return result;
    }

    function latestAssistantText() {

        const nodes =
            assistantMessages();

        if (!nodes.length) {
            return "";
        }

        return normalizeText(
            nodes[nodes.length - 1].innerText
        );
    }

    function assistantSnapshot() {

        return assistantMessages()
            .map(node =>
                normalizeText(node.innerText)
            )
            .filter(Boolean);
    }

    function setComposerText(element, text) {

        element.focus();

        if (element.tagName === "TEXTAREA") {

            const setter =
                Object.getOwnPropertyDescriptor(
                    HTMLTextAreaElement.prototype,
                    "value"
                )?.set;

            if (setter) {
                setter.call(element, text);
            } else {
                element.value = text;
            }

        } else {

            element.textContent = text;

        }

        element.dispatchEvent(
            new InputEvent(
                "input",
                {
                    bubbles: true,
                    inputType: "insertText",
                    data: text
                }
            )
        );

        element.dispatchEvent(
            new Event(
                "change",
                {
                    bubbles: true
                }
            )
        );
    }

    async function wait(ms) {
        return new Promise(
            resolve => setTimeout(resolve, ms)
        );
    }

    async function submitMessage(text) {

        const composer =
            findComposer();

        if (!composer) {
            throw new Error(
                "ChatGPT composer not found"
            );
        }

        setComposerText(
            composer,
            text
        );

        await wait(250);

        const button =
            findSendButton();

        if (button) {

            button.click();

        } else {

            composer.focus();

            composer.dispatchEvent(
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
    }

    function generationLooksActive() {

        const stopSelectors = [
            "button[aria-label*='Stop']",
            "button[data-testid*='stop']",
            "button[aria-label*='stop']"
        ];

        for (const selector of stopSelectors) {

            const node =
                document.querySelector(selector);

            if (node) {
                const rect =
                    node.getBoundingClientRect();

                if (
                    rect.width > 0 &&
                    rect.height > 0
                ) {
                    return true;
                }
            }
        }

        return false;
    }

    async function waitForAssistantResponse(
        request
    ) {

        const before =
            assistantSnapshot();

        const started =
            Date.now();

        let stableText = "";
        let stableSince = 0;

        while (
            Date.now() - started <
            (request.timeout_ms || 180000)
        ) {

            await wait(500);

            const current =
                assistantSnapshot();

            if (
                current.length === 0
            ) {
                continue;
            }

            const latest =
                current[current.length - 1];

            if (
                before.length > 0 &&
                current.length < before.length
            ) {
                continue;
            }

            if (!latest) {
                continue;
            }

            if (latest !== stableText) {

                stableText = latest;
                stableSince = Date.now();

                continue;
            }

            const stableFor =
                Date.now() - stableSince;

            if (
                stableFor >= 1800 &&
                !generationLooksActive()
            ) {
                return latest;
            }
        }

        throw new Error(
            "Timed out waiting for ChatGPT assistant response"
        );
    }

    async function sendResponse(
        request,
        response,
        error = null
    ) {

        try {

            const body = {
                id: request.id,
                ok: !error,
                response: response || "",
                error: error || null,
                url: location.href,
                timestamp: Date.now()
            };

            const data =
                await chrome.storage.local.get([
                    "relayUrl",
                    "token"
                ]);

            const relayUrl =
                String(
                    data.relayUrl ||
                    "http://127.0.0.1:8767"
                ).replace(/\/+$/, "");

            const token =
                String(
                    data.token || ""
                ).trim();

            const headers = {
                "Content-Type":
                    "application/json"
            };

            if (token) {
                headers[
                    "X-Bridge-Token"
                ] = token;
            }

            const result =
                await fetch(
                    relayUrl +
                    "/browser/response",
                    {
                        method: "POST",
                        headers,
                        body: JSON.stringify(body)
                    }
                );

            log(
                "RESPONSE RELAY",
                result.status
            );

        } catch (e) {

            console.error(
                TAG,
                "response relay failed",
                e
            );
        }
    }

    async function executeRequest(request) {

        if (activeRequest) {

            log(
                "request already active",
                activeRequest.id
            );

            return;
        }

        activeRequest = request;

        log(
            "REQUEST RECEIVED",
            request.id
        );

        try {

            if (
                request.type &&
                request.type !== "chat"
            ) {
                throw new Error(
                    "Unsupported request type: " +
                    request.type
                );
            }

            const text =
                String(
                    request.text || ""
                ).trim();

            if (!text) {
                throw new Error(
                    "Request text is empty"
                );
            }

            await submitMessage(text);

            log(
                "MESSAGE SUBMITTED",
                request.id
            );

            const answer =
                await waitForAssistantResponse(
                    request
                );

            log(
                "ASSISTANT RESPONSE FOUND",
                request.id,
                answer.slice(0, 120)
            );

            await sendResponse(
                request,
                answer,
                null
            );

        } catch (error) {

            console.error(
                TAG,
                "REQUEST FAILED",
                error
            );

            await sendResponse(
                request,
                "",
                String(error)
            );

        } finally {

            activeRequest = null;
        }
    }

    chrome.runtime.onMessage.addListener(
        (message) => {

            if (
                message &&
                message.type ===
                "PROJECT1_RELAY_REQUEST"
            ) {
                executeRequest(
                    message.request
                );
            }
        }
    );

    chrome.runtime.sendMessage(
        {
            type:
                "PROJECT1_CONTENT_READY"
        }
    ).catch(() => {});

    log(
        "CONTENT SCRIPT READY",
        location.href
    );

})();
