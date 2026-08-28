
const DEFAULT_RELAY = "http://127.0.0.1:8767";
const HEARTBEAT_MS = 2000;

let relayUrl = DEFAULT_RELAY;
let bridgeToken = "";

let lastRequestId = null;

async function loadConfiguration() {
    try {
        const data = await chrome.storage.local.get([
            "relayUrl",
            "token"
        ]);

        relayUrl = String(
            data.relayUrl || DEFAULT_RELAY
        ).replace(/\/+$/, "");

        bridgeToken = String(
            data.token || ""
        ).trim();

    } catch (error) {
        console.debug(
            "[PROJECT-1] configuration error",
            error
        );
    }
}

async function authenticatedFetch(path, options = {}) {
    await loadConfiguration();

    const headers = new Headers(
        options.headers || {}
    );

    headers.set("Cache-Control", "no-cache");
    headers.set("Pragma", "no-cache");

    if (bridgeToken) {
        headers.set(
            "X-Bridge-Token",
            bridgeToken
        );
    }

    return fetch(
        relayUrl + path,
        {
            ...options,
            headers,
            cache: "no-store"
        }
    );
}

async function heartbeat() {
    try {
        const response =
            await authenticatedFetch(
                "/browser/heartbeat",
                {
                    method: "GET"
                }
            );

        if (!response.ok) {
            console.debug(
                "[PROJECT-1] heartbeat HTTP",
                response.status
            );
        }

    } catch (error) {
        console.debug(
            "[PROJECT-1] heartbeat error",
            error
        );
    }
}

async function pollRequests() {
    try {
        const response =
            await authenticatedFetch(
                "/browser/poll",
                {
                    method: "GET"
                }
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        if (
            !data ||
            !data.ok ||
            !data.pending ||
            !data.request
        ) {
            return;
        }

        const request = data.request;

        if (
            !request.id ||
            request.id === lastRequestId
        ) {
            return;
        }

        lastRequestId = request.id;

        const tabs =
            await chrome.tabs.query({
                url: [
                    "https://chatgpt.com/*",
                    "https://chat.openai.com/*"
                ]
            });

        let delivered = false;

        for (const tab of tabs) {
            if (!tab.id) {
                continue;
            }

            try {
                await chrome.tabs.sendMessage(
                    tab.id,
                    {
                        type: "PROJECT1_RELAY_REQUEST",
                        request: request
                    }
                );

                console.log(
                    "[PROJECT-1] REQUEST DELIVERED",
                    request.id
                );

                delivered = true;
                break;

            } catch (error) {
                console.debug(
                    "[PROJECT-1] tab delivery error",
                    error
                );
            }
        }

        if (!delivered) {
            console.debug(
                "[PROJECT-1] no ChatGPT content script accepted request"
            );
        }

    } catch (error) {
        console.debug(
            "[PROJECT-1] poll error",
            error
        );
    }
}

async function browserHeartbeatFromTab() {
    await heartbeat();
}

chrome.runtime.onMessage.addListener(
    (message, sender, sendResponse) => {

        if (
            message &&
            message.type === "PROJECT1_CONTENT_READY"
        ) {
            browserHeartbeatFromTab();

            sendResponse({
                ok: true
            });

            return true;
        }

        return false;
    }
);

chrome.alarms.onAlarm.addListener(
    async alarm => {

        if (alarm.name === "project1_tick") {
            await heartbeat();
            await pollRequests();
        }
    }
);

chrome.runtime.onStartup.addListener(
    async () => {
        await loadConfiguration();
        await heartbeat();
    }
);

chrome.runtime.onInstalled.addListener(
    async () => {

        await loadConfiguration();

        chrome.alarms.create(
            "project1_tick",
            {
                periodInMinutes: 0.0334
            }
        );

        await heartbeat();
    }
);

(async () => {

    await loadConfiguration();

    chrome.alarms.create(
        "project1_tick",
        {
            periodInMinutes: 0.0334
        }
    );

    await heartbeat();

    await pollRequests();

})();
