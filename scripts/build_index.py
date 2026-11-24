"""Rebuild the static homepage from the project catalog and shared templates."""
import json
import re
from datetime import date
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def template(name):
    return Template((ROOT / "templates" / name).read_text(encoding="utf-8"))


def validate_url(url):
    parts = urlsplit(url)
    if parts.scheme == "https" and parts.netloc:
        return
    path = (ROOT / parts.path).resolve()
    if (parts.scheme or parts.netloc or parts.path.startswith("/")
            or ROOT not in path.parents or not path.is_file()):
        raise ValueError(f"Invalid or missing project link: {url}")


def build():
    catalog = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
    tags = catalog["tags"]
    projects = catalog["projects"]
    seen_ids = set()
    for key in tags:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
            raise ValueError(f"Invalid tag ID: {key}")
    for project in projects:
        project_id = project["id"]
        if project_id in seen_ids:
            raise ValueError(f"Duplicate project ID: {project_id}")
        seen_ids.add(project_id)
        if not project["tags"] or set(project["tags"]) - tags.keys():
            raise ValueError(f"Missing or unknown filter tags for {project_id}")
        if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", project["publishedMonth"]):
            raise ValueError(f"Expected YYYY-MM for {project_id}")
        validate_url(project["url"])
        for link in project["links"]:
            validate_url(link["url"])

    listed = sorted((p for p in projects if p["listed"]),
                    key=lambda p: p["publishedMonth"], reverse=True)
    card = template("card.html")
    cards = []
    used_tags = set()
    for project in listed:
        used_tags.update(project["tags"])
        month = project["publishedMonth"]
        badges = [f'<span class="project-tag">{escape(label)}</span>'
                  for label in project["badges"]]
        links = [
            f'<a class="repo-link" href="{escape(link["url"])}" target="_blank" '
            f'rel="noopener noreferrer">{escape(link["label"])}</a>'
            for link in project["links"]
        ]
        cards.append(card.substitute(
            id=escape(project["id"]), url=escape(project["url"]),
            tags=" ".join(project["tags"]), title=escape(project["title"]),
            month=month, date_label=date.fromisoformat(month + "-01").strftime("%B %Y"),
            badges=" ".join(badges), description=escape(project["description"]),
            links="\n          ".join(links),
        ).rstrip())
    buttons = [
        f'      <button type="button" data-tag="{key}" aria-pressed="false">'
        f'{escape(label)}</button>' for key, label in tags.items() if key in used_tags
    ]
    page = template("home.html").substitute(cards="\n".join(cards), filter_buttons="\n".join(buttons))
    (ROOT / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build()
