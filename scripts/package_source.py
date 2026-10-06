"""Bundle reviewed Git-index files, excluding secrets, runtime and uploaded data."""
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
output = ROOT.parent / "LitWeaver-AI-source.zip"
files = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
files = [name for name in files if name]
if not files:
    raise SystemExit("Stage the reviewed project files before packaging")
for name in files:
    if name in (".env", ".streamlit/secrets.toml") or any(part in (".venv", "tmp", ".git") for part in Path(name).parts):
        raise SystemExit("Unexpected private/runtime file in package manifest")
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
    for name in files:
        path = ROOT / name
        if not path.is_symlink() and path.is_file():
            bundle.write(path, "litweaver-ai/" + name)
print(f"Packaged {len(files)} reviewed files: {output}")
