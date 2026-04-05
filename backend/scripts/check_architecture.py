from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ARCHITECTURE = ROOT / "docs" / "product-architecture.md"
AGENTS_DOC = ROOT / "AGENTS.md"
ROUTE_CATALOG = ROOT / "docs" / "fastapi-route-catalog.md"
ROUTER_DIR = ROOT / "backend" / "app" / "routers"
REPOSITORY_DIR = ROOT / "backend" / "app" / "repositories"
SQL_DDL = ROOT / "sql" / "ddl_research_ledger_v2.sql"

HTTP_METHODS = {"get", "post", "patch", "put", "delete"}


def extract_authority_sources(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    match = re.search(r"## 1\.1 权威事实来源(?P<body>.*?)(?:\n## |\Z)", content, re.S)
    if not match:
        raise ValueError(f"authority section not found in {path.relative_to(ROOT)}")
    body = match.group("body")
    return re.findall(r"^\d+\.\s+`([^`]+)`", body, flags=re.M)


def parse_catalog_routes(path: Path) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        method = cells[0].strip("`")
        route_path = cells[1].strip("`")
        if method.upper() not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
            continue
        routes.add((method.upper(), route_path))
    return routes


def combine_path(prefix: str, route_path: str) -> str:
    if not prefix:
        return route_path
    if not route_path:
        return prefix
    return f"{prefix.rstrip('/')}/{route_path.lstrip('/')}"


def parse_router_routes(router_dir: Path) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path in sorted(router_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        router_prefixes: dict[str, str] = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            if not isinstance(func, ast.Name) or func.id != "APIRouter":
                continue
            prefix = ""
            for keyword in node.value.keywords:
                if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    prefix = keyword.value.value
            router_prefixes[node.targets[0].id] = prefix

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if not isinstance(func, ast.Attribute):
                    continue
                if not isinstance(func.value, ast.Name):
                    continue
                router_name = func.value.id
                method = func.attr.lower()
                if router_name not in router_prefixes or method not in HTTP_METHODS:
                    continue
                if not decorator.args:
                    continue
                first_arg = decorator.args[0]
                if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                    continue
                full_path = combine_path(router_prefixes[router_name], first_arg.value)
                routes.add((method.upper(), full_path))
    return routes


def extract_sql_tables(path: Path) -> set[str]:
    content = path.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS dr_os\.([a-z_]+)\s*\(", content))


def parse_repository_stores(repository_dir: Path) -> dict[str, tuple[str, ...]]:
    stores: dict[str, tuple[str, ...]] = {}
    for path in sorted(repository_dir.glob("*.py")):
        if path.name in {"__init__.py", "base.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for statement in node.body:
                if not isinstance(statement, ast.Assign):
                    continue
                for target in statement.targets:
                    if not isinstance(target, ast.Name) or target.id != "store_names":
                        continue
                    if not isinstance(statement.value, (ast.Tuple, ast.List)):
                        continue
                    values: list[str] = []
                    for item in statement.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            values.append(item.value)
                    stores[node.name] = tuple(values)
    return stores


def main() -> int:
    failures: list[str] = []

    product_sources = extract_authority_sources(PRODUCT_ARCHITECTURE)
    agent_sources = extract_authority_sources(AGENTS_DOC)
    if product_sources != agent_sources:
        failures.append(
            "authority_sources: AGENTS.md does not match docs/product-architecture.md ordering"
        )

    documented_routes = parse_catalog_routes(ROUTE_CATALOG)
    implemented_routes = parse_router_routes(ROUTER_DIR)
    missing_routes = sorted(documented_routes - implemented_routes)
    extra_routes = sorted(implemented_routes - documented_routes)
    if missing_routes:
        failures.extend(f"missing_route: {method} {route_path}" for method, route_path in missing_routes)
    if extra_routes:
        failures.extend(f"undocumented_route: {method} {route_path}" for method, route_path in extra_routes)

    sql_tables = extract_sql_tables(SQL_DDL)
    repository_stores = parse_repository_stores(REPOSITORY_DIR)
    ownership: dict[str, list[str]] = defaultdict(list)
    for repository_name, stores in repository_stores.items():
        for store in stores:
            ownership[store].append(repository_name)
            if store not in sql_tables:
                failures.append(f"unknown_store: {repository_name} declares non-DDL store {store}")
    for store, repositories in sorted(ownership.items()):
        if len(repositories) > 1:
            failures.append(f"duplicate_store_owner: {store} owned by {', '.join(sorted(repositories))}")

    if failures:
        print("Architecture drift detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Architecture check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
