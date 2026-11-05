"""The repository's description, homepage and topics on GitHub: the words GitHub's search and topic pages find it by.

    python3 -I scripts/github_meta.py           shows what GitHub has now and what would change; sends nothing
    python3 -I scripts/github_meta.py --check   checks them against GitHub's limits, offline
    python3 -I scripts/github_meta.py --apply   sends them with gh

--apply edits the repository's public page, so it is run on purpose, like a push. The social preview picture
(assets/readme/social-preview.jpg, written by scripts/make_art.py) has no API; it is uploaded under Settings, Social
preview.
"""
import json
import re
import subprocess
import sys

REPO = "xt0n1-t3ch/Pawdori-Game"
HOMEPAGE = "https://pawdori.black-watch.net"
DESCRIPTION = ("🐾 Pawdori: a free virtual pet game for Android and the browser. Raise your pet with your family, play "
               "mini games and live races with friends, dress it up and decorate its room. Signed APK that updates "
               "itself. Mascota virtual en español e inglés.")
# What people search for, most specific first: the genre, the platform, then the words Spanish speakers use.
TOPICS = ["virtual-pet", "pet-game", "tamagotchi", "cozy-game", "casual-game", "family-game", "kids-game",
          "mini-games", "multiplayer", "mobile-game", "android-game", "android", "apk", "pwa", "game",
          "free-to-play", "mascota-virtual", "juego", "pawdori", "spanish"]


def problems():
    found = []
    if len(TOPICS) > 20:
        found.append(f"{len(TOPICS)} topics; GitHub takes 20")
    found += [f"topic {topic!r} is not lowercase letters, digits and hyphens of at most 50 characters"
              for topic in TOPICS if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", topic)]
    found += [f"topic {topic!r} is listed twice" for topic in sorted({t for t in TOPICS if TOPICS.count(t) > 1})]
    if len(DESCRIPTION) > 350:
        found.append(f"the description is {len(DESCRIPTION)} characters; GitHub takes 350")
    return found


def gh(*arguments, stdin=None):
    return subprocess.run(["gh", *arguments], input=stdin, capture_output=True, text=True, check=True).stdout


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("", "--check", "--apply"):
        sys.exit(__doc__)
    failures = problems()
    for failure in failures:
        print(f"FAIL {failure}")
    if failures:
        return 1
    if mode == "--check":
        print(f"PASS the description ({len(DESCRIPTION)} characters) and the {len(TOPICS)} topics fit GitHub's limits")
        return 0
    now = json.loads(gh("repo", "view", REPO, "--json", "description,homepageUrl,repositoryTopics"))
    topics_now = sorted(t["name"] for t in now.get("repositoryTopics") or [])
    print(f"description: {'same' if now['description'] == DESCRIPTION else 'changes'}")
    print(f"homepage:    {'same' if now['homepageUrl'] == HOMEPAGE else 'changes'}")
    print(f"topics:      {'same' if topics_now == sorted(TOPICS) else 'changes'}")
    if mode == "--apply":
        gh("repo", "edit", REPO, "--description", DESCRIPTION, "--homepage", HOMEPAGE)
        gh("api", "-X", "PUT", f"repos/{REPO}/topics", "--input", "-", stdin=json.dumps({"names": TOPICS}))
        print("applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
