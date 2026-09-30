#!/usr/bin/env python3
"""Parse Google Scholar BibTeX into Zotero-friendly JSON.

Input can be a BibTeX file path argument or stdin. Output is a JSON array by
default because the export skill can batch multiple records before pushing.
"""

import json
import re
import sys
from pathlib import Path


TYPE_MAP = {
    "article": "journalArticle",
    "inproceedings": "conferencePaper",
    "conference": "conferencePaper",
    "book": "book",
    "incollection": "bookSection",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
}


def split_entries(text):
    entries = []
    index = 0
    while True:
        start = text.find("@", index)
        if start == -1:
            break

        brace_start = text.find("{", start)
        if brace_start == -1:
            break

        depth = 0
        end = brace_start
        while end < len(text):
            char = text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    entries.append(text[start:end + 1])
                    index = end + 1
                    break
            end += 1
        else:
            break

    return entries


def parse_fields(entry_body):
    fields = {}
    position = 0
    while position < len(entry_body):
        match = re.search(r"([A-Za-z][\w-]*)\s*=", entry_body[position:])
        if not match:
            break

        key = match.group(1).lower()
        value_start = position + match.end()
        while value_start < len(entry_body) and entry_body[value_start].isspace():
            value_start += 1

        if value_start >= len(entry_body):
            break

        delimiter = entry_body[value_start]
        if delimiter == "{":
            depth = 1
            value_end = value_start + 1
            while value_end < len(entry_body) and depth:
                if entry_body[value_end] == "{":
                    depth += 1
                elif entry_body[value_end] == "}":
                    depth -= 1
                value_end += 1
            raw_value = entry_body[value_start + 1:value_end - 1]
        elif delimiter == '"':
            value_end = value_start + 1
            escaped = False
            while value_end < len(entry_body):
                char = entry_body[value_end]
                if char == '"' and not escaped:
                    break
                escaped = char == "\\" and not escaped
                if char != "\\":
                    escaped = False
                value_end += 1
            raw_value = entry_body[value_start + 1:value_end]
            value_end += 1
        else:
            value_end = value_start
            while value_end < len(entry_body) and entry_body[value_end] not in ",\n":
                value_end += 1
            raw_value = entry_body[value_start:value_end]

        fields[key] = clean_value(raw_value)
        position = value_end + 1

    return fields


def clean_value(value):
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip().strip(",")


def parse_authors(author_value):
    if not author_value:
        return []

    creators = []
    for name in re.split(r"\s+and\s+", author_value):
        name = clean_value(name)
        if not name:
            continue

        if "," in name:
            last_name, first_name = [part.strip() for part in name.split(",", 1)]
        else:
            parts = name.rsplit(" ", 1)
            first_name = parts[0] if len(parts) == 2 else ""
            last_name = parts[1] if len(parts) == 2 else name

        creators.append({
            "lastName": last_name,
            "firstName": first_name,
            "creatorType": "author",
        })

    return creators


def parse_entry(entry):
    header = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,", entry, re.DOTALL)
    if not header:
        return None

    entry_type = header.group(1).lower()
    entry_key = header.group(2).strip()
    body = entry[header.end():entry.rfind("}")]
    fields = parse_fields(body)

    item = {
        "itemType": TYPE_MAP.get(entry_type, "journalArticle"),
        "title": fields.get("title", ""),
        "creators": parse_authors(fields.get("author", "")),
        "publicationTitle": fields.get("journal") or fields.get("booktitle", ""),
        "date": fields.get("year", ""),
        "volume": fields.get("volume", ""),
        "issue": fields.get("number", ""),
        "pages": fields.get("pages", ""),
        "publisher": fields.get("publisher", ""),
        "DOI": fields.get("doi", ""),
        "url": fields.get("url", ""),
        "language": "en",
        "libraryCatalog": "Google Scholar",
        "extra": f"Google Scholar BibTeX key: {entry_key}",
        "attachments": [],
    }

    return item


def main():
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    items = [item for item in (parse_entry(entry) for entry in split_entries(text)) if item]
    json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
