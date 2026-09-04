
(() => {
    "use strict";

    // ================================================================
    // PROJECT1_RUNTIME_TRACE_4927
    // TEMPORARY DIAGNOSTIC INSTRUMENTATION
    // ================================================================

    const PROJECT1_TRACE_PREFIX =
        "[PROJECT-1][RUNTIME-TRACE]";

    function project1Trace(stage, details = "") {
        try {
            console.log(
                PROJECT1_TRACE_PREFIX,
                stage,
                details
            );
        } catch (_) {
            // Diagnostics must never break the bridge.
        }
    }


    /*
     * PROJECT-1 Browser Chat Bridge v4.8
     *
     * Architecture:
     *
     *   PROJECT-1
     *       ↓
     *   /browser/poll
     *       ↓
     *   Chrome extension
     *       ↓
     *   visible ChatGPT Web DOM
     *       ↓
     *   /browser/response
     *       ↓
     *   PROJECT-1
     *
     * No ChatGPT API.
     * No OpenAI API.
     * No ChatGPT authentication token extraction.
     */

    const DEFAULT_RELAY =
        "https://protected-less-ratios-township.trycloudflare.com";

    let relayUrl = DEFAULT_RELAY;
    let bridgeToken = "";

    let processing = false;
    let lastRequestId = null;

    const HEARTBEAT_MS = 2000;
    const RESPONSE_TIMEOUT_MS = 180000;
    const STABLE_MS = 2500;

    // ------------------------------------------------------------
    // STORAGE
    // ------------------------------------------------------------

    async function loadConfiguration() {

        try {

            const data =
                await chrome.storage.local.get([
                    "relayUrl",
                    "token",
                ]);

            relayUrl =
                String(
                    data.relayUrl ||
                    DEFAULT_RELAY
                ).replace(/\/+$/, "");

            bridgeToken =
                String(
                    data.token || ""
                ).trim();

        } catch (error) {

            console.error(
                "[PROJECT-1] configuration error",
                error
            );
        }
    }

    // ------------------------------------------------------------
    // AUTHENTICATED FETCH
    // ------------------------------------------------------------

    async function authenticatedFetch(
        path,
        options = {}
    ) {

        if (!relayUrl) {
            throw new Error(
                "Relay URL is empty."
            );
        }

        if (!bridgeToken) {
            throw new Error(
                "PROJECT-1 bridge token is empty."
            );
        }

        const headers = {
            ...(options.headers || {}),
            "X-Bridge-Token": bridgeToken,
        };

        return fetch(
            relayUrl + path,
            {
                ...options,
                headers,
            }
        );
    }

    // ------------------------------------------------------------
    // HEARTBEAT / POLL
    // ------------------------------------------------------------

    async function pollRelay() {

        if (processing) {
            return;
        }

        try {

            const response =
                await authenticatedFetch(
                    "/browser/poll",
                    {
                        method: "GET",
                        cache: "no-store",
                    }
                );

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            const data =
                await response.json();

            if (!data || !data.ok) {
                return;
            }

            if (
                data.pending &&
                data.request
            ) {

                const request =
                    data.request;

                if (
                    request.id &&
                    request.id !== lastRequestId
                ) {

                    lastRequestId =
                        request.id;

                    await processRequest(
                        request
                    );
                }
            }

        } catch (error) {

            /*
             * Network failures are intentionally
             * non-fatal. The next heartbeat retries.
             */

            console.debug(
                "[PROJECT-1] relay poll:",
                error
            );
        }
    }

    // ------------------------------------------------------------
    // CHATGPT DOM HELPERS
    // ------------------------------------------------------------

    function getPromptElement() {

        const selectors = [
            "#prompt-textarea",
            "textarea[data-testid='text-input']",
            "textarea[placeholder*='Message']",
            "textarea",
            "[contenteditable='true'][role='textbox']",
        ];

        for (
            const selector of selectors
        ) {

            const element =
                document.querySelector(
                    selector
                );

            if (
                element &&
                isVisible(element)
            ) {
                return element;
            }
        }

        return null;
    }

    function isVisible(element) {

        if (!element) {
            return false;
        }

        const style =
            window.getComputedStyle(
                element
            );

        const rect =
            element.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            rect.width > 0 &&
            rect.height > 0
        );
    }

    function getSendButton() {

        const selectors = [
            "button[data-testid='send-button']",
            "button[aria-label*='Send']",
            "button[aria-label*='send']",
            "button[type='submit']",
        ];

        for (
            const selector of selectors
        ) {

            const buttons =
                document.querySelectorAll(
                    selector
                );

            for (
                const button of buttons
            ) {

                if (
                    isVisible(button) &&
                    !button.disabled
                ) {
                    return button;
                }
            }
        }

        return null;
    }

    // ------------------------------------------------------------
    // SET CHATGPT INPUT
    // ------------------------------------------------------------

    function setPromptValue(
        element,
        text
    ) {

        element.focus();

        /*
         * React-controlled textarea inputs require
         * the native setter instead of assigning .value
         * directly.
         */

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
                    data: text,
                }
            )
        );

        element.dispatchEvent(
            new Event(
                "change",
                {
                    bubbles: true,
                }
            )
        );
    }

    // ------------------------------------------------------------
    // CHATGPT ASSISTANT MESSAGES
    // ------------------------------------------------------------

    function getAssistantMessages() {

        const selectors = [
            "[data-message-author-role='assistant']",
            "article[data-testid*='conversation-turn']",
        ];

        let messages = [];

        for (
            const selector of selectors
        ) {

            const nodes =
                document.querySelectorAll(
                    selector
                );

            if (nodes.length) {

                messages = [
                    ...nodes
                ];

                break;
            }
        }

        /*
         * Filter out empty elements and,
         * where possible, identify actual
         * assistant content.
         */

        return messages
            .map(
                element => ({
                    element,
                    text:
                        (
                            element.innerText ||
                            element.textContent ||
                            ""
                        ).trim(),
                })
            )
            .filter(
                item =>
                    item.text.length > 0
            );
    }

    function getLastAssistantText() {

        const messages =
            getAssistantMessages();

        if (!messages.length) {
            return "";
        }

        return messages[
            messages.length - 1
        ].text;
    }

    // ------------------------------------------------------------
    // WAIT FOR ASSISTANT RESPONSE
    // ------------------------------------------------------------

    async function waitForAssistantResponse(
        previousText
    ) {

        const started =
            Date.now();

        let lastText = "";
        let stableSince = 0;

        while (
            Date.now() - started <
            RESPONSE_TIMEOUT_MS
        ) {

            await sleep(500);

            const current =
                getLastAssistantText();

            if (!current) {
                continue;
            }

            /*
             * We require the response to differ
             * from the previous assistant message.
             */

            if (
                current === previousText
            ) {
                continue;
            }

            if (
                current !== lastText
            ) {

                lastText = current;
                stableSince =
                    Date.now();

                continue;
            }

            /*
             * Text has stopped changing.
             * Treat it as complete after STABLE_MS.
             */

            if (
                Date.now() -
                stableSince >=
                STABLE_MS
            ) {

                return current;
            }
        }

        throw new Error(
            "Timed out waiting for ChatGPT response."
        );
    }

    // ------------------------------------------------------------
    // PROCESS ORCHESTRATOR REQUEST
    // ------------------------------------------------------------

    async function processRequest(
        request
    ) {

        if (processing) {
            return;
        }

        processing = true;

        project1Trace(
            "REQUEST_RECEIVED",
            request && request.id
                ? "request_id=" + request.id
                : "request_id=missing"
        );

        try {

            const payload =
                request.payload || {};

            const prompt =
                String(
                    payload.prompt ||
                    payload.task ||
                    ""
                ).trim();

            if (!prompt) {
                throw new Error(
                    "Relay request contains empty prompt."
                );
            }

            console.log(
                "[PROJECT-1] Received task:",
                prompt
            );

            const input =
                getPromptElement();

            project1Trace(
                "PROMPT_FOUND",
                input
                    ? "element_found"
                    : "element_missing"
            );

            if (!input) {
                throw new Error(
                    "ChatGPT prompt input not found."
                );
            }

            const previousText =
                getLastAssistantText();

            /*
             * Insert the complete Gemma-generated
             * message into the visible ChatGPT input.
             */

            setPromptValue(
                input,
                prompt
            );

            project1Trace(
                "PROMPT_SET",
                "prompt_value_written"
            );

            await sleep(300);

            const sendButton =
                getSendButton();

            project1Trace(
                "SEND_ATTEMPT",
                sendButton
                    ? "send_button"
                    : "keyboard_fallback"
            );

            if (sendButton) {

                sendButton.click();

            } else {

                /*
                 * Fallback: submit with Enter.
                 */

                input.dispatchEvent(
                    new KeyboardEvent(
                        "keydown",
                        {
                            bubbles: true,
                            cancelable: true,
                            key: "Enter",
                            code: "Enter",
                        }
                    )
                );
            }

            console.log(
                "[PROJECT-1] Prompt sent to visible ChatGPT."
            );

            project1Trace(
                "WAITING_RESPONSE",
                "waitForAssistantResponse_entered"
            );

            const result =
                await waitForAssistantResponse(
                    previousText
                );

            console.log(
                "[PROJECT-1] ChatGPT response received:",
                result
            );

            project1Trace(
                "ASSISTANT_RESPONSE_FOUND",
                "response_detected"
            );

            project1Trace(
                "RESPONSE_POST_ATTEMPT",
                "POST /browser/response"
            );

            await authenticatedFetch(
                "/browser/response",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        request_id:
                            request.id,
                        response:
                            result,
                        metadata: {
                            source:
                                "chatgpt_web_dom",
                            bridge_version:
                                "4.8",
                        },
                    }),
                }
            );

            console.log(
                "[PROJECT-1] Response returned to relay."
            );

            project1Trace(
                "RESPONSE_POST_COMPLETE",
                "POST completed"
            );

        } catch (error) {

            console.error(
                "[PROJECT-1] Request failed:",
                error
            );

            project1Trace(
                "PROCESS_ERROR",
                String(error)
            );

            /*
             * Return the error through the same
             * response channel so the orchestrator
             * never waits forever.
             */

            try {

                await authenticatedFetch(
                    "/browser/response",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                        body:
                            JSON.stringify({
                                request_id:
                                    request.id,
                                response:
                                    "[PROJECT-1 browser bridge error] " +
                                    String(
                                        error
                                    ),
                                metadata: {
                                    source:
                                        "chatgpt_web_dom",
                                    bridge_version:
                                        "4.8",
                                    error:
                                        true,
                                },
                            }),
                    }
                );

            } catch (
                responseError
            ) {

                console.error(
                    "[PROJECT-1] Could not return error:",
                    responseError
                );
            }

        } finally {

            processing = false;
        }
    }

    // ------------------------------------------------------------
    // UTILITY
    // ------------------------------------------------------------

    function sleep(ms) {

        return new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    ms
                )
        );
    }

    // ------------------------------------------------------------
    // START
    // ------------------------------------------------------------

    async function initialize() {

        await loadConfiguration();

        console.log(
            "[PROJECT-1] Browser Chat Bridge v4.8 loaded."
        );

        console.log(
            "[PROJECT-1] Relay:",
            relayUrl
        );

        /*
         * Immediate heartbeat.
         */

        await pollRelay();

        /*
         * Continuous polling.
         */

        setInterval(
            pollRelay,
            HEARTBEAT_MS
        );
    }

    initialize();

})();
