IMPORTANT_FILES = [
    "main.py", "app.py", "index.js", "server.js"
]

IMPORTANT_FOLDERS = [
    "routes", "controllers", "services", "models"
]

IGNORE = [
    "node_modules", "dist", "build", ".env", "__pycache__"
]


def is_important(path: str):
    if any(x in path for x in IGNORE):
        return False

    if any(path.endswith(f) for f in IMPORTANT_FILES):
        return True

    if any(folder in path for folder in IMPORTANT_FOLDERS):
        return True

    if path.endswith(".md") or path.endswith("requirements.txt"):
        return True

    return False
