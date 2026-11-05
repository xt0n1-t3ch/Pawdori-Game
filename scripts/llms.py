"""Writes llms.txt and llms-full.txt, the map of Pawdori for language models and coding agents (llmstxt.org).

    python3 -I scripts/llms.py           writes both files from the two README pages
    python3 -I scripts/llms.py --check   fails when either file is out of date or a linked file is missing

llms.txt is the short index: the name, a one-paragraph summary, the facts a model needs first, then links to the raw
Markdown on GitHub. llms-full.txt holds the text of both pages, with every picture replaced by its description. Both
carry facts and links only; nothing in them is phrased as an instruction.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/xt0n1-t3ch/Pawdori-Game"
RAW = "https://raw.githubusercontent.com/xt0n1-t3ch/Pawdori-Game/main/"

SUMMARY = ("Pawdori is a free virtual pet game for Android and the browser, in English and Spanish, for players 13 and "
           "up. Players adopt a pet, feed, bathe, cuddle and put it to bed, raise it with up to six family members "
           "and friends, play six mini games, You or Me? and the live Pet Race, and dress the pet and decorate its "
           "room. This repository publishes the signed Android APKs; the APK updates itself.")

FACTS = [
    f"Download: the latest signed APK is at {REPO}/releases/latest (file pawdori-<version>.apk, about 28 MB). "
    "It needs Android 10 or newer and an internet connection.",
    "Browser: the same game, as an installable PWA, is at https://app.pawdori.black-watch.net (Chrome 111+, "
    "Safari 16.4+). The website is https://pawdori.black-watch.net.",
    "Updates: the app reads latest.json from the latest release, shows the notes in the player's language, checks "
    "the APK's SHA-256 and signature, then opens Android's installer. Some versions are required.",
    "Signing: package com.pawdori.app; signing certificate SHA-256 BA:93:A4:A1:CA:42:94:70:86:81:B2:AD:BB:02:7E:4B:"
    "27:90:F7:D1:E2:6D:FA:48:E6:FB:24:66:B0:66:D0:92, also published in "
    "https://pawdori.black-watch.net/.well-known/assetlinks.json.",
    "Pets: 14 species (Mochi Bun, Puddin Cat, Nori Fox, Bubble Axolotl, Maple Bear, Pebble Penguin, Taro Panda, "
    "Honey Hamster, Sprout Frog, Cloud Sheep, Cocoa Otter, Starlight Dragon, Biscuit Pup, Pepper Pup), each with five "
    "growth stages.",
    "Mini games: Cozy Maze, Memory Match, Snack Catch, Bubble Pop, Rhythm Groom and Guess Answers (solo or "
    "challenge), You or Me? (challenge) and Pet Race (live).",
    "Money: free to play. Pawdori Premium is an optional subscription; there are no paid random rewards, and "
    "rewarded ads are optional. Coins, rewards and progress are decided on the server.",
    "Pawdori is made by xt0n1 (XT0N1.T3CH). The game, its art and characters are all rights reserved; the game's "
    "source code is private.",
]

DOCS = [
    ("Docs", "README (English)", "README.en.md", "what Pawdori is, screenshots, features, requirements, install, "
     "updates, security, releases, FAQ and credits"),
    ("Docs", "README (Spanish)", "README.md", "the same page in Spanish, the repository's main page"),
    ("Optional", "Citation", "CITATION.cff", "how to cite Pawdori"),
]


def picture_text(markdown):
    """`markdown` with HTML pictures turned into "(Picture: alt)", other tags dropped and blank runs collapsed."""
    text = re.sub(r"<!--.*?-->", "", markdown, flags=re.S)
    text = re.sub(r'<img[^>]*?alt="([^"]*)"[^>]*>', r"(Picture: \1)", text)
    text = re.sub(r"<h2[^>]*>\s*\(Picture: ([^)]*)\)\s*</h2>", r"## \1", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</?(?:p|a|div|table|tr|td|sub|b|strong|summary|details)[^>]*>", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"^[ \t]+(?=\S)", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def index():
    lines = ["# Pawdori", "", f"> {SUMMARY}", "", "Key facts:", ""]
    lines += [f"- {fact}" for fact in FACTS]
    sections = []
    for section, *_ in DOCS:
        if section not in sections:
            sections.append(section)
    for section in sections:
        lines += ["", f"## {section}", ""]
        lines += [f"- [{name}]({RAW}{path}): {note}" for s, name, path, note in DOCS if s == section]
        if section == "Optional":
            lines.append(f"- [Everything above in one file]({RAW}llms-full.txt): the text of both pages")
    lines += ["", "## Releases", "", f"- [Latest release]({REPO}/releases/latest): the newest signed APK, its "
              ".sha256 file and latest.json", f"- [All releases]({REPO}/releases): every version with notes in "
              "English and Spanish"]
    return "\n".join(lines) + "\n"


def full():
    parts = ["# Pawdori, the full text", "", f"> {SUMMARY}", ""]
    for _, name, path, _ in DOCS:
        if not path.endswith(".md"):
            continue
        with open(os.path.join(ROOT, path)) as f:
            parts += ["---", "", f"Source: {path} ({name})", "", picture_text(f.read())]
    return "\n".join(parts)


def main():
    check = sys.argv[1:] == ["--check"]
    if sys.argv[1:] not in ([], ["--check"]):
        sys.exit(__doc__)
    missing = [path for _, _, path, _ in DOCS if not os.path.exists(os.path.join(ROOT, path))]
    if missing:
        sys.exit(f"FAIL linked files are missing: {', '.join(missing)}")
    stale = []
    for name, content in (("llms.txt", index()), ("llms-full.txt", full())):
        path = os.path.join(ROOT, name)
        if check:
            current = open(path).read() if os.path.exists(path) else None
            if current != content:
                stale.append(name)
        else:
            with open(path, "w") as f:
                f.write(content)
            print(f"{name}: {len(content)} characters")
    if stale:
        sys.exit(f"FAIL out of date: {', '.join(stale)}; run python3 -I scripts/llms.py")
    if check:
        print("PASS llms.txt and llms-full.txt match the pages")


if __name__ == "__main__":
    main()
