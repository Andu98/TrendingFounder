const express = require("express");

const PORT = 1234;
const NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
const API_KEY = process.env.NVIDIA_API_KEY; // Load from environment for security
const DEFAULT_MODEL = "meta/llama-3.1-8b-instruct";

const app = express();
app.use(express.json({ limit: "10mb" }));

// GET /v1/models
app.get("/v1/models", (_req, res) => {
  res.json({
    object: "list",
    data: [
      { id: DEFAULT_MODEL, object: "model", owned_by: "nvidia-nim" },
    ],
  });
});

// POST /v1/chat/completions — proxy to NVIDIA
app.post("/v1/chat/completions", async (req, res) => {
  try {
    const body = req.body;
    body.model = body.model || DEFAULT_MODEL;
    const isStream = body.stream === true;

    const response = await fetch(NVIDIA_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (isStream) {
      res.writeHead(response.status, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      });
      const reader = response.body.getReader();
      const pump = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) { res.end(); return; }
          res.write(value);
        }
      };
      pump().catch(err => {
        console.error("[proxy] Stream error:", err.message);
        res.end();
      });
      req.on("close", () => reader.cancel());
    } else {
      const data = await response.text();
      res.status(response.status).set("Content-Type", "application/json").send(data);
    }
  } catch (err) {
    console.error("[proxy] Error:", err.message);
    res.status(502).json({ error: { message: err.message } });
  }
});

app.listen(PORT, () => {
  console.log(`NVIDIA NIM proxy running on http://127.0.0.1:${PORT}/v1`);
  console.log(`Default model: ${DEFAULT_MODEL}`);
});
