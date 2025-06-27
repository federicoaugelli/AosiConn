from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <title>Trading Dashboard</title>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"/>
      <link href=\"https://fonts.googleapis.com/css?family=Montserrat:400,600&display=swap\" rel=\"stylesheet\">
      <style>
        body {
          background: #e0e5ec;
          font-family: 'Montserrat', sans-serif;
        }
        .neumorph {
          box-shadow: 9px 9px 16px #b2b6be, -9px -9px 16px #ffffff;
          background: #e0e5ec;
          border-radius: 20px;
          padding: 30px;
          margin: 40px auto;
          max-width: 900px;
        }
        h2 { color: #727481; margin-bottom: 24px; }
        .section {
          margin-bottom: 36px;
        }
        .info-block { margin-bottom: 1em; }
        .info-block span { font-weight: 600; color: #888;}
        button {
          background: #e0e5ec;
          border: none;
          border-radius: 12px;
          box-shadow:  5px 5px 10px #babecc,
                      -5px -5px 10px #fff;
          padding: 10px 20px;
          margin-top: 12px;
          font-size: 1em;
          color: #31344b;
          transition: 0.2s;
          cursor: pointer;
        }
        button:hover {
          box-shadow:  2px 2px 5px #babecc,
                      -2px -2px 5px #fff;
        }
        pre {
          background: #e0e5ec;
          box-shadow: 2px 2px 4px #babecb,-2px -2px 4px #fff;
          border-radius: 8px;
          padding: 1em;
        }
      </style>
    </head>
    <body>
      <div class=\"neumorph\">
        <h2>🚀 Trading Dashboard</h2>
        <div class=\"section\" id=\"status\">
          <h3>Status</h3>
          <div class=\"info-block\" id=\"status-data\">Loading...</div>
        </div>
        <div class=\"section\" id=\"exchanges\">
          <h3>Exchanges</h3>
          <div class=\"info-block\" id=\"exchanges-data\">Loading...</div>
        </div>
        <div class=\"section\" id=\"api-keys\">
          <h3>API Keys</h3>
          <div class=\"info-block\" id=\"keys-data\">Loading...</div>
        </div>
        <div class=\"section\" id=\"threads\">
          <h3>Threads</h3>
          <div class=\"info-block\" id=\"threads-data\">Loading...</div>
        </div>
        <div class=\"section\" id=\"statistics\">
          <h3>Statistics</h3>
          <div class=\"info-block\" id=\"stats-data\">Loading...</div>
        </div>
        <button onclick=\"refreshDashboard()\">🔄 Refresh</button>
      </div>
      <script>
        async function fetchEndpoint(endpoint, options) {
          try {
            let res = await fetch(endpoint, options);
            return await res.json();
          } catch (e) {
            return {error: e.toString()};
          }
        }

        async function refreshDashboard() {
          document.getElementById(\"status-data\").textContent = \"Loading...\";
          document.getElementById(\"exchanges-data\").textContent = \"Loading...\";
          document.getElementById(\"keys-data\").textContent = \"Loading...\";
          document.getElementById(\"threads-data\").textContent = \"Loading...\";
          document.getElementById(\"stats-data\").textContent = \"Loading...\";

          // 1. Status
          let status = await fetchEndpoint(\"/\");
          document.getElementById(\"status-data\").textContent = JSON.stringify(status, null, 2);

          // 2. Exchanges
          let exchanges = await fetchEndpoint(\"/exchange/list/\");
          document.getElementById(\"exchanges-data\").textContent = (exchanges.exchanges || []).join(", ");

          // 3. API Keys
          let keys = await fetchEndpoint(\"/key/\");
          if (keys.detail || keys.error) {
            document.getElementById(\"keys-data\").textContent = \"Login required or unavailable\";
          } else {
            document.getElementById(\"keys-data\").textContent = JSON.stringify(keys, null, 2);
          }

          // 4. Threads
          let threads = await fetchEndpoint(\"/thread/\");
          document.getElementById(\"threads-data\").textContent = JSON.stringify(threads, null, 2);

          // 5. Stats
          let stats = await fetchEndpoint(\"/stats/\");
          document.getElementById(\"stats-data\").textContent = JSON.stringify(stats, null, 2);
        }
        refreshDashboard();
      </script>
    </body>
    </html>
    """