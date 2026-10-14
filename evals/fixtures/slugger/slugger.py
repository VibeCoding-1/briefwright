"""Tiny slug utility: the eval MVP artifact."""


def slugify(text):
    text = text.lower().strip()
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    return "".join(out)
