#!/usr/bin/env python3
import argparse
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPORT_GLOBS = [
    "**/target/surefire-reports/TEST-*.xml",
    "**/target/failsafe-reports/TEST-*.xml",
    "**/build/test-results/**/TEST-*.xml",
]


def find_reports(root):
    found = set()
    for pattern in REPORT_GLOBS:
        found.update(root.glob(pattern))
    return sorted(found)


def read_suite(path, root):
    try:
        suite = ElementTree.parse(path).getroot()
    except ElementTree.ParseError:
        return None
    if suite.tag != "testsuite":
        return None
    return {
        "name": suite.get("name", path.stem),
        "seconds": float(suite.get("time", "0").replace(",", "") or 0),
        "tests": int(suite.get("tests", "0") or 0),
        "run": report_run(path.relative_to(root)),
    }


def report_run(relative):
    parts = relative.parts
    if "test-results" in parts:
        module = Path(*parts[: parts.index("build")])
        kind = parts[parts.index("test-results") + 1]
    else:
        module = relative.parent.parent.parent
        kind = relative.parent.name.replace("-reports", "")
    return kind if str(module) == "." else f"{module}:{kind}"


def share(part, total):
    return f"{100 * part / total:5.1f}%" if total else "    -"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="List the slowest test classes from the JUnit XML reports of the "
                    "last Maven (Surefire, Failsafe) or Gradle test run, with each "
                    "class's share of the total test time.",
    )
    parser.add_argument("root", nargs="?", default=".",
                        help="Project directory to search (default: current directory).")
    parser.add_argument("--top", type=int, default=15,
                        help="Number of classes to list (default: 15).")
    args = parser.parse_args(argv)

    root = Path(args.root)
    suites = [suite for suite in (read_suite(path, root) for path in find_reports(root)) if suite]
    if not suites:
        sys.exit(
            f"No test reports found under {root.resolve()}.\n"
            "Run the tests first (./mvnw test, ./mvnw verify or ./gradlew test); the "
            "reports are written to target/surefire-reports, target/failsafe-reports "
            "or build/test-results."
        )
    total = sum(suite["seconds"] for suite in suites)
    tests = sum(suite["tests"] for suite in suites)
    print(f"{len(suites)} test classes, {tests} tests, {total:.1f} s in total\n")

    runs = {}
    for suite in suites:
        runs.setdefault(suite["run"], []).append(suite)
    if len(runs) > 1:
        print("Per run:")
        for run, members in sorted(runs.items(), key=lambda item: -sum(s["seconds"] for s in item[1])):
            seconds = sum(s["seconds"] for s in members)
            print(f"  {seconds:8.1f} s  {share(seconds, total)}  {run}  (classes: {len(members)})")
        print()

    ranked = sorted(suites, key=lambda suite: -suite["seconds"])
    shown = ranked[: args.top]
    print(f"Slowest {len(shown)} classes:")
    for suite in shown:
        print(f"  {suite['seconds']:8.1f} s  {share(suite['seconds'], total)}  "
              f"{suite['name']}  ({suite['tests']} tests, {suite['run']})")
    covered = sum(suite["seconds"] for suite in shown)
    if len(ranked) > len(shown):
        print(f"\nThese {len(shown)} classes account for {share(covered, total).strip()} "
              f"of the total; {len(ranked) - len(shown)} more classes are not listed.")
    print("\nTimes are per class as the test engine reports them. In each JVM the first "
          "class that needs a Spring context also pays for starting it.")


if __name__ == "__main__":
    main()
