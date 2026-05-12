import os
import json
import shutil
import mimetypes
import socket
import cgi
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

CONFIG_FILE = Path(__file__).parent / "nas_config.json"
INDEX_FILE  = Path(__file__).parent / "index.html"

DEFAULT_CONFIG = {
    "storage_dir": str(Path.home() / "storage"),
    "port": 8080,
    "max_upload_mb": 4096,
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

config  = load_config()
STORAGE = Path(config["storage_dir"])
STORAGE.mkdir(parents=True, exist_ok=True)

def format_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"

def safe_path(rel: str) -> Path:
    target = (STORAGE / unquote(rel.lstrip("/"))).resolve()
    if not str(target).startswith(str(STORAGE.resolve())):
        raise PermissionError("Path traversal blocked")
    return target

def file_type(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}:
        return "video"
    if ext in {".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".opus"}:
        return "audio"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico"}:
        return "image"
    if ext in {".pdf"}:
        return "pdf"
    if ext in {".doc", ".docx"}:
        return "word"
    if ext in {".xls", ".xlsx", ".csv"}:
        return "excel"
    if ext in {".ppt", ".pptx"}:
        return "ppt"
    if ext in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}:
        return "archive"
    if ext in {".txt", ".md", ".log", ".ini", ".cfg"}:
        return "text"
    if ext in {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
               ".java", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".go",
               ".rs", ".sh", ".bat", ".ps1", ".yaml", ".yml"}:
        return "code"
    if ext in {".exe", ".msi", ".dmg", ".deb", ".rpm"}:
        return "exe"
    if ext in {".iso"}:
        return "iso"
    if ext in {".apk", ".ipa"}:
        return "apk"
    return "file"

def is_previewable(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}:
        return "image"
    if ext in {".mp4", ".mkv", ".webm", ".mov"}:
        return "video"
    if ext in {".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a"}:
        return "audio"
    if ext in {".txt", ".md", ".log", ".py", ".js", ".ts", ".html",
               ".css", ".json", ".xml", ".csv", ".yaml", ".yml",
               ".sh", ".bat", ".ini", ".cfg", ".c", ".cpp", ".h"}:
        return "text"
    return ""

def get_disk_usage(path: Path):
    try:
        u = shutil.disk_usage(path)
        return {"total": u.total, "used": u.used, "free": u.free,
                "pct": round(u.used / u.total * 100, 1)}
    except Exception:
        return {"total": 0, "used": 0, "free": 0, "pct": 0}

def list_dir(path: Path):
    items = []
    try:
        for entry in sorted(path.iterdir(),
                            key=lambda e: (e.is_file(), e.name.lower())):
            try:
                stat = entry.stat()
            except Exception:
                continue
            rel = str(entry.relative_to(STORAGE)).replace("\\", "/")
            items.append({
                "name":      entry.name,
                "path":      rel,
                "is_dir":    entry.is_dir(),
                "size":      stat.st_size if entry.is_file() else 0,
                "size_human": format_bytes(stat.st_size) if entry.is_file() else "—",
                "modified":  datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y"),
                "type":      "folder" if entry.is_dir() else file_type(entry.name),
                "preview":   is_previewable(entry.name) if entry.is_file() else "",
            })
    except PermissionError:
        pass
    return items

def search_files(query: str):
    results = []
    q = query.lower()
    for f in STORAGE.rglob("*"):
        if q in f.name.lower() and len(results) < 200:
            try:
                stat = f.stat()
                results.append({
                    "name":       f.name,
                    "path":       str(f.relative_to(STORAGE)).replace("\\", "/"),
                    "is_dir":     f.is_dir(),
                    "size_human": format_bytes(stat.st_size) if f.is_file() else "—",
                    "modified":   datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y"),
                    "type":       "folder" if f.is_dir() else file_type(f.name),
                    "preview":    is_previewable(f.name) if f.is_file() else "",
                })
            except Exception:
                pass
    return results

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        method = args[0].split()[0] if args else "?"
        path   = args[0].split()[1] if args else "?"
        code   = args[1] if len(args) > 1 else "?"
        if not path.startswith("/api/"):
            return
       # print(f"[{ts}] {method} {path}  →  {code}")    ~  only remove # if you care about the status code logs!

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",  "no-cache")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def send_err(self, msg, status=400):
        self.send_json({"error": msg}, status)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        parsed = urlparse(self.path)
        p  = parsed.path
        qs = parse_qs(parsed.query)

        if p in ("/", ""):
            self.serve_index()
        elif p == "/api/ls":
            self.api_ls(qs)
        elif p == "/api/file":
            self.api_file(qs)
        elif p == "/api/download":
            self.api_download(qs)
        elif p == "/api/stats":
            self.api_stats()
        elif p == "/api/recent":
            self.api_recent()
        elif p == "/api/search":
            self.api_search(qs)
        elif p == "/api/config":
            self.api_config_get()
        else:
            self.send_err("Not found", 404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/upload":
            self.api_upload()
        elif p == "/api/mkdir":
            self.api_mkdir()
        elif p == "/api/rename":
            self.api_rename()
        elif p == "/api/config":
            self.api_config_set()
        else:
            self.send_err("Not found", 404)

    def do_DELETE(self):
        p = urlparse(self.path).path
        if p == "/api/delete":
            self.api_delete()
        else:
            self.send_err("Not found", 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Allow", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def serve_index(self):
        if not INDEX_FILE.exists():
            msg = (b"<h2>index.html not found</h2>"
                   b"<p>Put index.html in the same folder as main.py</p>")
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        body = INDEX_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",   "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",  "no-cache")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def api_ls(self, qs):
        rel = qs.get("path", [""])[0]
        try:
            target = safe_path(rel)
            if not target.is_dir():
                self.send_err("Not a directory"); return
            self.send_json(list_dir(target))
        except Exception as e:
            self.send_err(str(e))

    def api_file(self, qs):
        rel = qs.get("path", [""])[0]
        try:
            target = safe_path(rel)
            if not target.is_file():
                self.send_err("Not a file", 404); return
            mime, _ = mimetypes.guess_type(str(target))
            mime = mime or "application/octet-stream"
            size = target.stat().st_size
            range_hdr = self.headers.get("Range")
            if range_hdr:
                try:
                    parts = range_hdr.replace("bytes=", "").split("-")
                    start = int(parts[0]) if parts[0] else 0
                    end   = int(parts[1]) if len(parts) > 1 and parts[1] else size - 1
                    end   = min(end, size - 1)
                    length = end - start + 1
                    self.send_response(206)
                    self.send_header("Content-Type",   mime)
                    self.send_header("Content-Range",  f"bytes {start}-{end}/{size}")
                    self.send_header("Accept-Ranges",  "bytes")
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    with open(target, "rb") as f:
                        f.seek(start)
                        remaining = length
                        while remaining > 0:
                            chunk = f.read(min(65536, remaining))
                            if not chunk: break
                            try:
                                self.wfile.write(chunk)
                            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                                return
                            remaining -= len(chunk)
                    return
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type",   mime)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges",  "bytes")
            self.end_headers()
            with open(target, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk: break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        return
        except Exception as e:
            try:
                self.send_err(str(e), 404)
            except Exception:
                pass

    def api_download(self, qs):
        rel = qs.get("path", [""])[0]
        try:
            target = safe_path(rel)
            if not target.is_file():
                self.send_err("Not a file", 404); return
            mime, _ = mimetypes.guess_type(str(target))
            mime = mime or "application/octet-stream"
            size = target.stat().st_size
            safe_name = target.name.encode("ascii", "replace").decode()
            self.send_response(200)
            self.send_header("Content-Type",        mime)
            self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
            self.send_header("Content-Length",      str(size))
            self.end_headers()
            with open(target, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk: break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        return
        except Exception as e:
            try:
                self.send_err(str(e), 404)
            except Exception:
                pass

    def api_stats(self):
        disk = get_disk_usage(STORAGE)
        total_files = total_folders = 0
        for f in STORAGE.rglob("*"):
            if f.is_file():   total_files   += 1
            elif f.is_dir():  total_folders += 1
        self.send_json({
            **disk,
            "total_human":   format_bytes(disk["total"]),
            "used_human":    format_bytes(disk["used"]),
            "free_human":    format_bytes(disk["free"]),
            "total_files":   total_files,
            "total_folders": total_folders,
        })

    def api_recent(self):
        files = []
        for f in STORAGE.rglob("*"):
            if f.is_file():
                try:
                    files.append((f.stat().st_mtime, f))
                except Exception:
                    pass
        files.sort(reverse=True)
        result = []
        for mtime, f in files[:20]:
            try:
                stat = f.stat()
                result.append({
                    "name":       f.name,
                    "path":       str(f.relative_to(STORAGE)).replace("\\", "/"),
                    "is_dir":     False,
                    "size_human": format_bytes(stat.st_size),
                    "modified":   datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y"),
                    "type":       file_type(f.name),
                    "preview":    is_previewable(f.name),
                })
            except Exception:
                pass
        self.send_json(result)

    def api_search(self, qs):
        q = qs.get("q", [""])[0].strip()
        if len(q) < 2:
            self.send_json([]); return
        self.send_json(search_files(q))

    def api_config_get(self):
        cfg = load_config()
        self.send_json({"storage_dir": cfg["storage_dir"], "port": cfg["port"]})

    def api_config_set(self):
        data = self.read_json()
        cfg  = load_config()
        if "storage_dir" in data and data["storage_dir"].strip():
            cfg["storage_dir"] = data["storage_dir"].strip()
        if "port" in data:
            try:
                cfg["port"] = int(data["port"])
            except Exception:
                pass
        save_config(cfg)
        self.send_json({"ok": True})

    def api_upload(self):
        ct     = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        max_b  = config.get("max_upload_mb", 4096) * 1024 * 1024
        if length > max_b:
            self.send_err(f"Too large (max {config['max_upload_mb']} MB)", 413); return
        if "multipart/form-data" not in ct:
            self.send_err("Expected multipart/form-data"); return
        try:
            fs = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST",
                         "CONTENT_TYPE":   ct,
                         "CONTENT_LENGTH": str(length)},
            )
            file_item = fs["file"]
            path_val  = fs.getvalue("path", "")
            dest_dir  = safe_path(path_val)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / file_item.filename
            with open(dest, "wb") as out:
                out.write(file_item.file.read())
            print(f"[UPLOAD] {file_item.filename}  ({format_bytes(dest.stat().st_size)})")
            self.send_json({"ok": True, "name": file_item.filename,
                            "size": dest.stat().st_size})
        except Exception as e:
            self.send_err(str(e), 500)

    def api_mkdir(self):
        data = self.read_json()
        rel  = data.get("path", "")
        name = data.get("name", "").strip()
        if not name or any(c in name for c in r'/\:*?"<>|'):
            self.send_err("Invalid folder name"); return
        try:
            target = safe_path(rel) / name
            target.mkdir(exist_ok=True)
            print(f"[MKDIR]  {target}")
            self.send_json({"ok": True})
        except Exception as e:
            self.send_err(str(e))

    def api_delete(self):
        data = self.read_json()
        rel  = data.get("path", "")
        try:
            target = safe_path(rel)
            if not target.exists():
                self.send_err("Not found", 404); return
            if target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
            print(f"[DELETE] {target}")
            self.send_json({"ok": True})
        except Exception as e:
            self.send_err(str(e))

    def api_rename(self):
        data     = self.read_json()
        rel      = data.get("path", "")
        new_name = data.get("new_name", "").strip()
        if not new_name or any(c in new_name for c in r'/\:*?"<>|'):
            self.send_err("Invalid name"); return
        try:
            target = safe_path(rel)
            dest   = target.parent / new_name
            target.rename(dest)
            print(f"[RENAME] {target.name}  →  {new_name}")
            self.send_json({"ok": True})
        except Exception as e:
            self.send_err(str(e))

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    cfg     = load_config()
    port    = cfg["port"]
    storage = Path(cfg["storage_dir"])
    storage.mkdir(parents=True, exist_ok=True)
    ip = get_local_ip()

    server = HTTPServer(("0.0.0.0", port), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    os.system('cls')

    print()
    print("━" * 54)
    print("  6p6t's Storage Service  —  running")
    print("━" * 54)
    print(f"  Local      →  http://localhost:{port}")
    print(f"  Network    →  http://{ip}:{port}   ← share this")
    print(f"  Storage    →  {storage}")
    print()
    print("  Open the Network URL on any device on your WiFi")
    print("  Ctrl+C to stop")
    print("━" * 54)
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped. Goodbye.")
        server.server_close()
        os.system('cls')
