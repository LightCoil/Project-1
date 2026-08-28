chrome.storage.local.get(
["relayUrl","token"],
data => {
document.getElementById("relay").textContent =
data.relayUrl || "http://127.0.0.1:8767";
document.getElementById("token").textContent =
data.token ? "configured" : "missing";
});
