
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>PROJECT-1</title>

<style>
html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background: #111;
    color: #eee;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

#top {
    height: 52px;
    background: #181818;
    display: flex;
    align-items: center;
    padding: 0 16px;
    box-sizing: border-box;
    border-bottom: 1px solid #333;
}

#title {
    font-size: 18px;
    font-weight: 600;
}

#status {
    margin-left: 20px;
    font-size: 13px;
    color: #7ee787;
}

#browser {
    position: absolute;
    left: 0;
    right: 0;
    top: 52px;
    bottom: 0;
    border: 0;
    width: 100%;
    height: calc(100% - 52px);
}

#login {
    position: absolute;
    z-index: 10;
    right: 16px;
    top: 12px;
    background: #2d6cdf;
    color: white;
    padding: 8px 13px;
    border-radius: 6px;
    font-size: 13px;
}
</style>
</head>

<body>

<div id="top">
    <div id="title">
        PROJECT-1
    </div>

    <div id="status">
        Virtual Chromium
    </div>
</div>

<div id="login">
    ChatGPT: login inside browser
</div>

<iframe
    id="browser"
    src="/browser/"
    allow="clipboard-read; clipboard-write"
></iframe>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML

@app.get("/browser/", response_class=HTMLResponse)
async def browser():

    # noVNC entrypoint
    return """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>PROJECT-1 Browser</title>
<style>
html,body {
    margin:0;
    width:100%;
    height:100%;
    overflow:hidden;
}
iframe {
    border:0;
    width:100%;
    height:100%;
}
</style>
</head>
<body>
<iframe src="http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale"></iframe>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="warning"
    )
