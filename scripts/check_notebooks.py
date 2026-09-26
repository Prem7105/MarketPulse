"""Execute notebook code cells as scripts after migrating and seeding."""

import json
from pathlib import Path

if __name__ == "__main__":
    for path in sorted(Path("notebooks").glob("*.ipynb")):
        document = json.loads(path.read_text())
        scope = {}
        for cell in document["cells"]:
            if cell["cell_type"] == "code":
                exec(compile("".join(cell["source"]), str(path), "exec"), scope)
        print(f"Executed: {path.name}")
