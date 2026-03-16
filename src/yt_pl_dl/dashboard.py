from __future__ import annotations

import os
import secrets
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from yt_pl_dl.config import Settings, load_settings
from yt_pl_dl.state import StateStore


APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
security = HTTPBasic(auto_error=False)
app = FastAPI(title="yt-pl-dl dashboard")


def get_settings() -> Settings:
    return load_settings()


def require_auth(
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    username = settings.dashboard_basic_auth_username
    password = settings.dashboard_basic_auth_password

    if not username and not password:
        return "anonymous"

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    username_ok = secrets.compare_digest(credentials.username, username or "")
    password_ok = secrets.compare_digest(credentials.password, password or "")
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def systemd_property(unit: str, property_name: str) -> str:
    result = run_command(["systemctl", "show", unit, f"--property={property_name}", "--value"])
    return result.stdout.strip() if result.returncode == 0 else ""


def service_snapshot(unit: str) -> dict[str, str]:
    return {
        "unit": unit,
        "active": systemd_property(unit, "ActiveState") or "unknown",
        "sub": systemd_property(unit, "SubState") or "unknown",
        "result": systemd_property(unit, "Result") or "unknown",
        "state_change": systemd_property(unit, "StateChangeTimestamp") or "n/a",
    }


def timer_snapshot(unit: str) -> dict[str, str]:
    snapshot = {
        "unit": unit,
        "active": systemd_property(unit, "ActiveState") or "unknown",
        "next": "n/a",
        "last": "n/a",
    }

    result = run_command(["systemctl", "list-timers", "--all", "--no-pager", "--no-legend"])
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if unit not in line:
                continue
            parts = line.split()
            if len(parts) >= 10:
                # NEXT LEFT LAST PASSED UNIT ACTIVATES
                snapshot["next"] = " ".join(parts[0:5])
                snapshot["last"] = " ".join(parts[5:9])
                return snapshot

    next_from_show = systemd_property(unit, "NextElapseUSecRealtime")
    last_from_show = systemd_property(unit, "LastTriggerUSec")
    if next_from_show:
        snapshot["next"] = next_from_show
    if last_from_show:
        snapshot["last"] = last_from_show
    return snapshot


def tail_log(log_file: Path, lines: int = 50) -> str:
    if not log_file.exists():
        return ""
    content = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def recent_worker_journal(lines: int = 120) -> str:
    result = run_command(["journalctl", "-u", "yt-pl-dl.service", "-n", str(lines), "--no-pager"])
    if result.returncode != 0:
        return ""
    return result.stdout


def cookies_snapshot(settings: Settings, recent_output: str) -> dict[str, str | bool]:
    path = settings.yt_cookies_path
    if path is None:
        return {
            "configured": False,
            "status": "missing",
            "label": "Not configured",
            "reason": "YT_COOKIES_PATH is not set.",
            "path": "n/a",
            "updated_at": "n/a",
            "size": "n/a",
        }

    if not path.exists():
        return {
            "configured": True,
            "status": "missing",
            "label": "Missing",
            "reason": "Cookie file does not exist.",
            "path": str(path),
            "updated_at": "n/a",
            "size": "0 B",
        }

    file_size = path.stat().st_size
    modified_at = path.stat().st_mtime
    lowered_output = recent_output.lower()

    if file_size == 0:
        status_name = "missing"
        label = "Empty"
        reason = "Cookie file is empty."
    elif "sign in to confirm you’re not a bot" in lowered_output or "login_required" in lowered_output:
        status_name = "warning"
        label = "Refresh needed"
        reason = "Recent yt-dlp runs hit YouTube login or bot-check responses."
    else:
        status_name = "ok"
        label = "Looks usable"
        reason = "Cookie file exists and recent logs do not show login-required failures."

    return {
        "configured": True,
        "status": status_name,
        "label": label,
        "reason": reason,
        "path": str(path),
        "updated_at": str(datetime.fromtimestamp(modified_at).astimezone().replace(microsecond=0)),
        "size": f"{file_size} B",
    }


def write_cookies_file(path: Path, content: str) -> tuple[bool, str]:
    normalized = content.strip()
    if not normalized:
        return False, "Cookies content is empty."

    if "# Netscape HTTP Cookie File" not in normalized and ".youtube.com" not in normalized:
        return False, "Cookies content does not look like an exported cookies.txt file."

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(normalized + "\n", encoding="utf-8")
    os.chmod(temp_path, 0o600)
    temp_path.replace(path)
    os.chmod(path, 0o600)
    return True, "Cookies file updated."


def trigger_run_now() -> tuple[bool, str]:
    result = run_command(["systemctl", "start", "yt-pl-dl.service"])
    if result.returncode == 0:
        return True, "Run triggered."
    error = (result.stderr or result.stdout or "Failed to start service").strip()
    return False, error


def delete_local_file(store: StateStore, video_id: str) -> tuple[bool, str]:
    row = store.get_processed_video(video_id)
    if not row:
        return False, "Video not found."

    local_path = row[4]
    if not local_path:
        return False, "Local file path is empty."

    path = Path(local_path)
    if path.exists():
        path.unlink()
    store.clear_local_path(video_id)
    return True, "Local file deleted."


@app.get("/")
def dashboard_page(
    request: Request,
    _: str = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    store = StateStore(settings.state_db_path)
    store.init_db()
    recent_journal = recent_worker_journal()
    recent_log = tail_log(settings.log_file_path)

    videos = [
        {
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "discovered_at": discovered_at,
            "local_path": local_path,
        }
        for video_id, title, channel, discovered_at, local_path in store.list_processed()
    ]

    context = {
        "request": request,
        "videos": videos,
        "video_count": len(videos),
        "sync_target": settings.sync_target or "n/a",
        "worker_service": service_snapshot("yt-pl-dl.service"),
        "provider_service": service_snapshot("bgutil-pot-provider.service"),
        "tailscale_service": service_snapshot("tailscaled.service"),
        "worker_timer": timer_snapshot("yt-pl-dl.timer"),
        "cookies": cookies_snapshot(settings, f"{recent_log}\n{recent_journal}"),
        "log_text": recent_log,
        "flash_message": request.query_params.get("message", ""),
        "flash_error": request.query_params.get("error", ""),
    }
    return templates.TemplateResponse("dashboard.html", context)


@app.post("/actions/run-now")
def run_now(_: str = Depends(require_auth)) -> RedirectResponse:
    ok, message = trigger_run_now()
    query = f"message={message}" if ok else f"error={message}"
    return RedirectResponse(url=f"/?{query}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/videos/{video_id}/delete-local")
def delete_local(
    video_id: str,
    _: str = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    store = StateStore(settings.state_db_path)
    store.init_db()
    ok, message = delete_local_file(store, video_id)
    query = f"message={message}" if ok else f"error={message}"
    return RedirectResponse(url=f"/?{query}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/actions/update-cookies")
def update_cookies(
    cookies_text: str = Form(...),
    _: str = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if settings.yt_cookies_path is None:
        return RedirectResponse(
            url="/?error=YT_COOKIES_PATH is not configured.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    ok, message = write_cookies_file(settings.yt_cookies_path, cookies_text)
    query = f"message={message}" if ok else f"error={message}"
    return RedirectResponse(url=f"/?{query}", status_code=status.HTTP_303_SEE_OTHER)


def main() -> int:
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "yt_pl_dl.dashboard:app",
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
