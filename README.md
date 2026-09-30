# my-skills

> These are Ytang520's personal skills — custom-tailored to his machines, subscriptions, and workflow. They are published for reference and inspiration. Treat them as examples of what a skill can look like, then ask your own LLM to write skills for your exact needs. Avoid reusing other people's skills verbatim: they carry someone else's assumptions, paths, and credentials layout.

## Layout

One directory per skill. Each directory contains a `SKILL.md`.

## Skills

| Skill | Purpose |
| --- | --- |
| `arxiv` | Search arXiv by paper name, keyword, or arXiv id, and retrieve metadata and PDFs |
| `literature-review` | Run a staged AI literature review: collection, screening, close reading, and synthesis |
| google_scholar and their related skills | Search Google Scholar, including advanced search, citation tracking, full-text links, pagination, Zotero export, and environment checks |
| `xiaohongshu-chrome-devtools` | Extract visible Xiaohongshu notes, comments, and search results through Chrome DevTools |
| `China_travel_mcp_installation` | Install and configure the China travel-planning MCP |

## Installation

After cloning this repository, copy or symlink the skill directory you need into your agent's skills directory. For Claude Code:

```text
~/.claude/skills/<skill-name>
```

For the browser path, start from `chrome-path.example.txt` and create `chrome-path.txt` in the same directory. The skill writes that file after it finds a local browser.

## Acknowledgments

google_scholar and their related skills are based on [cookjohn/gs-skills](https://github.com/cookjohn/gs-skills).
