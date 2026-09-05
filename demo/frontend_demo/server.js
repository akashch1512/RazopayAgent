const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 5173;
const ROOT = __dirname;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
};

http
  .createServer((req, res) => {
    const urlPath = decodeURIComponent(req.url.split("?")[0]);
    let filePath = path.join(ROOT, urlPath);

    const hasExtension = path.extname(filePath) !== "";
    if (!hasExtension) {
      filePath = path.join(ROOT, "index.html");
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        fs.readFile(path.join(ROOT, "index.html"), (err2, fallback) => {
          if (err2) {
            res.writeHead(404);
            res.end("Not found");
            return;
          }
          res.writeHead(200, { "Content-Type": MIME[".html"] });
          res.end(fallback);
        });
        return;
      }
      const ext = path.extname(filePath);
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      res.end(data);
    });
  })
  .listen(PORT, () => {
    console.log(`Frontend demo running at http://localhost:${PORT}`);
  });
