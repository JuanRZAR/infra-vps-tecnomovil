"""API mínima de ejemplo para probar el VPS: GET /health y GET /."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            cuerpo = {"status": "ok"}
        elif self.path == "/":
            cuerpo = {"proyecto": "ejemplo", "mensaje": "El VPS funciona v2"}
        else:
            self.send_error(404)
            return
        datos = json.dumps(cuerpo).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Manejador).serve_forever()
