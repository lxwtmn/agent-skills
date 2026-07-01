#!/usr/bin/env python3
"""
Query a Spring Initializr instance for its live capabilities.

This exists so the skill never has to hardcode Spring Boot versions, Java
versions, or dependency IDs -- all of which change frequently. It fetches the
metadata document the service exposes at its root and prints a compact,
human-readable summary, so you (Claude) can present real, current options to the
user and validate their choices before generating a project.

Only the Python standard library is used, so it runs anywhere Python 3 is
available. The default instance is https://start.spring.io but --base-url lets
you point at a company/enterprise instance.

Commands
--------
  versions                 Show default + available build tools, languages,
                           Spring Boot versions, Java versions, packaging.
  search <keyword>         Find dependencies whose id/name/description match a
                           keyword (case-insensitive). Use this to turn a user's
                           plain-language wish ("postgres", "security") into the
                           exact dependency IDs the API expects.
  validate <id1,id2,...>   Check that each dependency ID exists. Invalid IDs are
                           reported with close suggestions so you can correct
                           them before calling the API.
  deps [group]             List dependency IDs, optionally filtered to one group
                           (e.g. "SQL", "Web"). Omit the group to list all.

Options
-------
  --base-url URL   Initializr instance (default: https://start.spring.io)
  --from-file P    Load metadata from a local JSON file instead of the network.
                   Useful for offline work, caching, or testing.

Examples
--------
  python query_initializr.py versions
  python query_initializr.py search postgres
  python query_initializr.py validate web,data-jpa,security
  python query_initializr.py --base-url https://start.example.com deps SQL
"""

import argparse
import difflib
import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://start.spring.io"

# The service negotiates a vendor JSON media type. Newer instances speak higher
# versions; we ask for a few, best-first, and fall back to plain JSON. The
# document structure is stable across the v2.x line, so parsing is unaffected.
ACCEPT_HEADERS = [
    "application/vnd.initializr.v2.2+json",
    "application/vnd.initializr.v2.1+json",
    "application/json",
]


def fetch_metadata(base_url):
    """Return the parsed metadata dict, or exit with a clear message."""
    url = base_url.rstrip("/") + "/"
    last_error = None
    for accept in ACCEPT_HEADERS:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": "spring-boot-initializr-skill/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            return json.loads(raw)
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code == 406:  # this Accept not supported; try the next one
                continue
            body = ""
            try:
                body = error.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            hint = ""
            if "not in allowlist" in body or "host_not_allowed" in body:
                hint = (
                    "\nThe host is blocked by a network egress allowlist. Add "
                    f"'{_host(base_url)}' to the allowed hosts, or run this in an "
                    "environment with open internet access (e.g. your local machine)."
                )
            sys.exit(f"HTTP {error.code} fetching metadata from {url}: "
                     f"{body or error.reason}{hint}")
        except urllib.error.URLError as error:
            last_error = error
            sys.exit(
                f"Could not reach {url}: {error.reason}.\n"
                "If you are on a restricted network, allowlist the host or run "
                "in an environment that can reach the internet."
            )
        except json.JSONDecodeError:
            # Wrong media type slipped through; try the next Accept header.
            continue
    sys.exit(f"Failed to fetch or parse metadata from {url}: {last_error}")


def _host(base_url):
    rest = base_url.split("://", 1)[-1]
    return rest.split("/", 1)[0]


def load_metadata(args):
    if args.from_file:
        try:
            with open(args.from_file, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            sys.exit(f"Metadata file not found: {args.from_file}")
        except json.JSONDecodeError as error:
            sys.exit(f"Metadata file is not valid JSON ({args.from_file}): {error}")
    return fetch_metadata(args.base_url)


def select_field(meta, key):
    """Return (default_id, [(id, name), ...]) for a single-select capability."""
    node = meta.get(key, {}) or {}
    default = node.get("default")
    values = [(v.get("id"), v.get("name", v.get("id"))) for v in node.get("values", [])]
    return default, values


def walk_dependencies(meta):
    """Flatten the dependency hierarchy into a list of dependency dicts.

    Written defensively: anything carrying an 'id' + 'name' is treated as a
    dependency; anything with a 'name' and a list of 'values' but no 'id' is a
    group whose name we carry down. This survives minor schema shifts.
    """
    found = []

    def visit(node, group):
        if isinstance(node, dict):
            if "id" in node and "name" in node:
                found.append({
                    "id": node["id"],
                    "name": node.get("name", ""),
                    "description": node.get("description", ""),
                    "versionRange": (node.get("versionRange")
                                     or node.get("compatibilityRange") or ""),
                    "group": group or "",
                })
                return
            next_group = node.get("name", group)
            for child in node.get("values", []) or []:
                visit(child, next_group)
        elif isinstance(node, list):
            for item in node:
                visit(item, group)

    visit(meta.get("dependencies", {}), None)
    return found


def cmd_versions(meta):
    build_default, build_values = select_field(meta, "type")
    lang_default, lang_values = select_field(meta, "language")
    boot_default, boot_values = select_field(meta, "bootVersion")
    java_default, java_values = select_field(meta, "javaVersion")
    pack_default, pack_values = select_field(meta, "packaging")

    def fmt(default, values, limit=None):
        shown = values if limit is None else values[:limit]
        lines = []
        for ident, name in shown:
            marker = "  (default)" if ident == default else ""
            label = f"{ident}" if ident == name else f"{ident}  [{name}]"
            lines.append(f"    - {label}{marker}")
        if limit is not None and len(values) > limit:
            lines.append(f"    ... and {len(values) - limit} more")
        return "\n".join(lines)

    print("Build tool / project type:")
    print(fmt(build_default, build_values))
    print("\nLanguage:")
    print(fmt(lang_default, lang_values))
    print("\nSpring Boot version:")
    print(fmt(boot_default, boot_values, limit=12))
    print("\nJava version:")
    print(fmt(java_default, java_values))
    print("\nPackaging:")
    print(fmt(pack_default, pack_values))

    text_defaults = {
        key: (meta.get(key, {}) or {}).get("default")
        for key in ("groupId", "artifactId", "name", "description",
                    "packageName", "version")
    }
    print("\nText field defaults:")
    for key, value in text_defaults.items():
        if value is not None:
            print(f"    - {key}: {value}")


def cmd_search(meta, keyword):
    keyword = keyword.lower()
    matches = [
        dep for dep in walk_dependencies(meta)
        if keyword in dep["id"].lower()
        or keyword in dep["name"].lower()
        or keyword in dep["description"].lower()
    ]
    if not matches:
        print(f"No dependencies match '{keyword}'.")
        print("Try a broader term, or run 'deps' to list everything.")
        return
    print(f"{len(matches)} dependency match(es) for '{keyword}':\n")
    for dep in matches:
        rng = f"  (Boot {dep['versionRange']})" if dep["versionRange"] else ""
        group = f"  [{dep['group']}]" if dep["group"] else ""
        print(f"  {dep['id']}  ->  {dep['name']}{group}{rng}")
        if dep["description"]:
            print(f"      {dep['description']}")


def cmd_validate(meta, ids_arg):
    requested = [i.strip() for i in ids_arg.split(",") if i.strip()]
    all_deps = walk_dependencies(meta)
    known = {dep["id"] for dep in all_deps}
    valid, invalid = [], []
    for ident in requested:
        (valid if ident in known else invalid).append(ident)
    if valid:
        print("Valid:")
        for ident in valid:
            name = next((d["name"] for d in all_deps if d["id"] == ident), "")
            print(f"  {ident}  ({name})")
    if invalid:
        print("\nInvalid (not offered by this instance):")
        for ident in invalid:
            suggestions = difflib.get_close_matches(ident, sorted(known), n=3, cutoff=0.4)
            hint = f"  did you mean: {', '.join(suggestions)}" if suggestions else ""
            print(f"  {ident}{hint}")
    if not invalid:
        print("\nAll dependency IDs are valid.")
    else:
        sys.exit(1)  # signal failure so the caller can stop before generating


def cmd_deps(meta, group_filter):
    deps = walk_dependencies(meta)
    if group_filter:
        wanted = group_filter.lower()
        deps = [d for d in deps if d["group"].lower() == wanted]
        if not deps:
            groups = sorted({d["group"] for d in walk_dependencies(meta) if d["group"]})
            print(f"No group named '{group_filter}'. Available groups:")
            for name in groups:
                print(f"  - {name}")
            return
    current = None
    for dep in sorted(deps, key=lambda d: (d["group"], d["id"])):
        if dep["group"] != current:
            current = dep["group"]
            print(f"\n[{current or 'Ungrouped'}]")
        print(f"  {dep['id']}  ->  {dep['name']}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Query a Spring Initializr instance for live capabilities.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"Initializr instance (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--from-file", default=None,
                        help="Load metadata from a local JSON file instead of the network.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("versions", help="Show available build tools, versions, etc.")
    search = sub.add_parser("search", help="Search dependencies by keyword.")
    search.add_argument("keyword")
    validate = sub.add_parser("validate", help="Validate a comma-separated list of dependency IDs.")
    validate.add_argument("ids")
    deps = sub.add_parser("deps", help="List dependency IDs, optionally by group.")
    deps.add_argument("group", nargs="?", default=None)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    meta = load_metadata(args)
    if args.command == "versions":
        cmd_versions(meta)
    elif args.command == "search":
        cmd_search(meta, args.keyword)
    elif args.command == "validate":
        cmd_validate(meta, args.ids)
    elif args.command == "deps":
        cmd_deps(meta, args.group)


if __name__ == "__main__":
    main()
