import sys
from pathlib import Path

import pypdf
import yaml

_HERE = Path(__file__).parent


def load_our_profile(
    products_yaml_path: Path,
    our_profile_dir: Path,
) -> tuple[str, list[str]]:
    """Load our product catalog and any persona/context docs from our_profile/.

    Returns (combined_text, files_loaded). Combined text is fed directly into
    the analysis prompt. Tolerates missing or empty directories gracefully.
    """
    sections: list[str] = []
    files_loaded: list[str] = []

    # Always load the products YAML first
    try:
        data = yaml.safe_load(products_yaml_path.read_text(encoding="utf-8"))
        products_text = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        sections.append(f"=== {products_yaml_path.name.upper()} ===\n{products_text}")
        files_loaded.append(products_yaml_path.name)
    except Exception as exc:
        print(f"[profile_loader] Could not load {products_yaml_path}: {exc}", file=sys.stderr)

    # Load all .yaml and .md files from our_profile/ (YAML first, then Markdown)
    if our_profile_dir.exists():
        yaml_files = sorted(our_profile_dir.glob("*.yaml")) + sorted(our_profile_dir.glob("*.yml"))
        md_files = sorted(our_profile_dir.glob("*.md"))
        for path in yaml_files + md_files:
            if path.name.startswith(".") or path.name.lower() == "readme.md":
                continue
            try:
                content = path.read_text(encoding="utf-8")
                sections.append(f"=== {path.name.upper()} ===\n{content}")
                files_loaded.append(path.name)
            except Exception as exc:
                print(f"[profile_loader] Could not load {path}: {exc}", file=sys.stderr)

    # Load all .pdf files from our_profile/
    if our_profile_dir.exists():
        for path in sorted(our_profile_dir.glob("*.pdf")):
            if path.name.startswith("."):
                continue
            try:
                reader = pypdf.PdfReader(str(path))
                pages = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(f"[Page {i + 1}]\n{text.strip()}")
                if pages:
                    content = "\n\n".join(pages)
                    sections.append(f"=== {path.name.upper()} ===\n{content}")
                    files_loaded.append(path.name)
            except Exception as exc:
                print(f"[profile_loader] Could not load {path}: {exc}", file=sys.stderr)

    combined_text = "\n\n".join(sections)
    return combined_text, files_loaded
