<div align="center">

# 6p6t's Storage Service

Modern self-hosted local NAS web server built with pure Python.

<img src="https://img.shields.io/badge/python-3.9+-black?style=for-the-badge&logo=python">
<img src="https://img.shields.io/badge/frontend-HTML%20%2F%20CSS%20%2F%20JS-black?style=for-the-badge">
<img src="https://img.shields.io/badge/platform-windows-black?style=for-the-badge">

</div>

---

## Overview

6p6t's Storage Service is a lightweight self-hosted NAS-style file manager designed for local networks.

It provides a modern responsive web interface for uploading, browsing, previewing, searching, downloading, and managing files directly from your PC.

Built entirely using Python standard libraries with no backend dependencies required.

---

# Features

- Modern responsive UI
- Mobile and desktop support
- File upload system
- Folder creation
- File renaming
- File deletion
- Real-time file previews
- Image preview support
- Video streaming support
- Audio playback support
- Text/code preview support
- Search system
- Recent files dashboard
- Storage statistics
- Local network access
- Zero database required
- Pure Python backend

---

# Preview Support

Supported previews include:

| Type | Support |
|------|---------|
| Images | ✅ |
| Videos | ✅ |
| Audio | ✅ |
| Text Files | ✅ |
| Code Files | ✅ |

---

# Tech Stack

## Backend

- Python
- `http.server`
- JSON configuration
- Local filesystem APIs

## Frontend

- HTML5
- CSS3
- Vanilla JavaScript

---

# Installation

## Clone Repository

```bash
git clone https://github.com/i6p6t/6p6t-storage-service
cd 6p6t-storage-service
```

---

# Run Server

```bash
python main.py
```

---

# Default Configuration

```json
{
  "storage_dir": "storage",
  "port": 8080,
  "max_upload_mb": 4096
}
```

Configuration is automatically generated on first launch.

---

# Accessing the NAS

After starting the server:

```text
http://localhost:8080
```

For other devices on your WiFi:

```text
http://YOUR_LOCAL_IP:8080
```

---

# API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/ls` | List directory |
| `/api/file` | Stream file |
| `/api/download` | Download file |
| `/api/upload` | Upload file |
| `/api/mkdir` | Create folder |
| `/api/delete` | Delete item |
| `/api/rename` | Rename item |
| `/api/search` | Search files |
| `/api/stats` | Storage statistics |

---

# Project Structure

```text
.
├── main.py
├── index.html
├── nas_config.json
└── storage/
```

---

# UI Features

- Responsive sidebar
- Grid/List file views
- Smooth animations
- Modern dark theme
- Toast notifications
- Drag & drop uploads
- File type icons
- Mobile optimized layout

---

# Security Notes

- Path traversal protection included
- Local network intended usage
- No external cloud services
- Files stay on your machine

---

# TODO

Planned features for future updates.

- [ ] Multi-file download support
- [ ] Multi-file delete support
- [ ] Shareable file/folder links
- [ ] Password protected folders
- [ ] Better media streaming
- [ ] File upload progress improvements
- [ ] Authentication system

---

# Credits

Developed by **6p6t**

Made with ❤️ using Python

---

# License

MIT License
