from .base import *
def template_kind(spec_path: Path) -> str:
    text = spec_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        raise ValueError(f"{spec_path} missing frontmatter")
    end = text.find("\n---", 3)
    if end < 0:
        raise ValueError(f"{spec_path} has unclosed frontmatter")
    front = text[3:end].splitlines()
    for line in front:
        m = re.match(r"^kind\s*:\s*['\"]?([A-Za-z][A-Za-z0-9_-]*)", line)
        if m:
            return m.group(1)
    raise ValueError(f"{spec_path} frontmatter must declare kind")


def design_specs(root: Path) -> list[Path]:
    templates = root / "templates"
    found: list[Path] = []
    canonical = templates / "design_spec.md"
    if canonical.is_file():
        found.append(canonical)
    found.extend(sorted(templates.glob("design_spec.*.*.md")))
    if not found:
        legacy = root / "design_spec.md"
        if legacy.is_file():
            found.append(legacy)
    if not found:
        raise ValueError(f"template workspace has no design spec: {root}")
    return found


def build_template_options(project: Path) -> tuple[dict, dict[str, dict]]:
    confirm_dir = project / "confirm_ui"
    source = read_json(confirm_dir / "template_options.json")
    if source.get("schema_version") != 1 or source.get("phase") != "template":
        raise ValueError("template_options.json must be schema_version=1, phase=template")
    default_mode = source.get("default_mode")
    if default_mode not in {"free_design", "templates"}:
        raise ValueError("template_options.default_mode must be free_design or templates")
    roots_raw = source.get("explicit_workspace_roots")
    if not isinstance(roots_raw, list):
        raise ValueError("template_options.explicit_workspace_roots must be an array")

    library: dict[str, list] = {}
    candidates: dict[str, dict] = {}
    registered_roots: dict[str, dict] = {}
    index_contracts: dict[str, dict] = {}
    for kind, (dirname, indexname) in TEMPLATE_LIBRARY_CONFIG.items():
        kind_dir = (SKILL_DIR / "templates" / dirname).resolve()
        index = read_json(kind_dir / indexname)
        index_contracts[kind] = index
        group = []
        for template_id, meta in index.items():
            root = (kind_dir / template_id).resolve()
            spec = root / "templates" / "design_spec.md"
            if not root.is_dir() or not spec.is_file():
                raise ValueError(f"registered template is incomplete: {root}")
            declared = template_kind(spec)
            if declared != kind:
                raise ValueError(f"{spec} declares {declared}, expected {kind}")
            candidate = {
                "key": f"library:{kind}:{template_id}",
                "source": "library",
                "kind": kind,
                "id": template_id,
                "label": template_id,
                "summary": meta.get("summary", "") if isinstance(meta, dict) else "",
                "workspace_root": str(root),
            }
            group.append(candidate)
            candidates[candidate["key"]] = candidate
            registered_roots[str(root)] = candidate
        library[kind] = group

    explicit = []
    suggested: list[str] = []
    resolved_roots: list[Path] = []
    seen_roots = set()
    for raw in roots_raw:
        root = Path(raw).expanduser()
        if not root.is_absolute():
            raise ValueError(f"explicit template root must be absolute: {raw}")
        root = root.resolve()
        if str(root) in seen_roots:
            raise ValueError(f"duplicate explicit template root: {root}")
        seen_roots.add(str(root)); resolved_roots.append(root)
        if str(root) in registered_roots:
            suggested.append(registered_roots[str(root)]["key"])
            continue
        specs = [(p, template_kind(p)) for p in design_specs(root)]
        kinds = [kind for _p, kind in specs]
        if len(kinds) != len(set(kinds)):
            raise ValueError(f"explicit root exposes duplicate kinds: {root}")
        root_hash = hashlib.sha256(str(root).encode()).hexdigest()
        for _spec, kind in specs:
            c = {
                "key": f"explicit:{root_hash}:{kind}",
                "source": "explicit",
                "kind": kind,
                "label": root.name or str(root),
                "workspace_root": str(root),
            }
            explicit.append(c); candidates[c["key"]] = c; suggested.append(c["key"])

    preselected = suggested if len(resolved_roots) == 1 else []
    response = {
        "schema_version": 1,
        "phase": "template",
        "default_mode": default_mode,
        "library": library,
        "explicit": explicit,
        "preselected_keys": preselected,
    }
    if isinstance(source.get("lang"), str):
        response["lang"] = source["lang"].strip()
    response["options_sha256"] = digest({
        "schema_version": 1,
        "phase": "template",
        "default_mode": default_mode,
        "lang": response.get("lang"),
        "explicit_workspace_roots": [str(p) for p in resolved_roots],
        "library_indexes": index_contracts,
        "library": library,
        "explicit": explicit,
        "preselected_keys": preselected,
    })
    return response, candidates
