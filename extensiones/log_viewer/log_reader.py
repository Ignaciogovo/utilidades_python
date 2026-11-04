"""Descubrimiento y lectura de los logs de control de utils/error_system."""

from datetime import datetime
from pathlib import Path

PAGE_SIZE = 50
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


def _project_for(path):
    name = path.name
    if name == "control.log":
        return "control.log"
    if name.endswith("_control.log"):
        return name[:-len("_control.log")] or "control.log"
    return None


def discover_logs(directory):
    projects = {}
    try:
        for path in Path(directory).iterdir():
            if path.is_symlink() or not path.is_file():
                continue
            project = _project_for(path)
            if project:
                projects[project] = path
    except OSError:
        return {}
    return dict(sorted(projects.items()))


def _parse_line(line, project, file_time):
    text = line.rstrip("\r\n")
    parts = text.split(" | ", 2)
    try:
        if len(parts) != 3:
            raise ValueError
        timestamp = datetime.strptime(parts[0], _TIMESTAMP_FORMAT)
        level, message = parts[1].upper(), parts[2]
        sort_time = timestamp
        display_time = timestamp.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    except ValueError:
        timestamp, level, message = None, "RAW", text
        sort_time, display_time = file_time, "—"
    return {
        "timestamp": timestamp,
        "sort_time": sort_time,
        "display_time": display_time,
        "level": level,
        "message": message,
        "project": project,
    }


def read_logs(directory, project=None, level=None, query="", date_from=None, date_to=None, page=1):
    projects = discover_logs(directory)
    selected = [projects.get(project)] if project else list(projects.values())
    matches = []
    needle = query.strip().casefold()

    # ponytail: paginate the active file in memory; stream pages if log size becomes material.
    for path in selected:
        if path is None:
            continue
        try:
            file_time = datetime.fromtimestamp(path.stat().st_mtime)
            with path.open(encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    entry = _parse_line(line, _project_for(path), file_time)
                    event_time = entry["timestamp"] or file_time
                    if date_from and event_time.date() < date_from:
                        continue
                    if date_to and event_time.date() > date_to:
                        continue
                    if level and entry["level"] != level:
                        continue
                    if needle and needle not in entry["message"].casefold():
                        continue

                    matches.append(entry)
        except OSError:
            continue

    matches.sort(key=lambda entry: entry["sort_time"], reverse=True)
    pages = max(1, (len(matches) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 1), pages)
    start = (page - 1) * PAGE_SIZE
    return {
        "projects": list(projects),
        "entries": matches[start:start + PAGE_SIZE],
        "total": len(matches),
        "page": page,
        "pages": pages,
    }
