import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "spring-boot-testing" / "scripts"))

import slowest_tests


def write_report(directory, class_name, seconds, tests=1):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"TEST-{class_name}.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuite name="{class_name}" tests="{tests}" time="{seconds}"></testsuite>\n',
        encoding="utf-8",
    )


def run(*arguments):
    output = io.StringIO()
    exit_code = 0
    with contextlib.redirect_stdout(output):
        try:
            slowest_tests.main(list(arguments))
        except SystemExit as stop:
            exit_code = stop.code
    return exit_code, output.getvalue()


class SlowestTestsTest(unittest.TestCase):

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.root = Path(self.workspace.name)

    def tearDown(self):
        self.workspace.cleanup()

    def test_ranks_classes_by_time_with_share_of_total(self):
        reports = self.root / "target" / "surefire-reports"
        write_report(reports, "com.acme.FastTest", "10.0", tests=4)
        write_report(reports, "com.acme.SlowTest", "30.0", tests=2)

        _, output = run(str(self.root))

        self.assertIn("2 test classes, 6 tests, 40.0 s in total", output)
        self.assertLess(output.index("com.acme.SlowTest"), output.index("com.acme.FastTest"))
        self.assertIn("75.0%  com.acme.SlowTest", output)

    def test_reads_surefire_failsafe_and_gradle_reports_as_separate_runs(self):
        write_report(self.root / "target" / "surefire-reports", "com.acme.UnitTest", "1.0")
        write_report(self.root / "target" / "failsafe-reports", "com.acme.OrderIT", "5.0")
        write_report(self.root / "build" / "test-results" / "integrationTest", "com.acme.GradleIT", "4.0")

        _, output = run(str(self.root))

        self.assertIn("50.0%  failsafe  (classes: 1)", output)
        self.assertIn("40.0%  integrationTest  (classes: 1)", output)
        self.assertIn("10.0%  surefire  (classes: 1)", output)

    def test_names_the_module_in_a_multi_module_build(self):
        write_report(self.root / "orders" / "target" / "surefire-reports", "com.acme.OrderTest", "2.0")
        write_report(self.root / "billing" / "target" / "surefire-reports", "com.acme.BillingTest", "2.0")

        _, output = run(str(self.root))

        self.assertIn("orders:surefire", output)
        self.assertIn("billing:surefire", output)

    def test_top_limits_the_listing_and_says_what_is_left_out(self):
        reports = self.root / "target" / "surefire-reports"
        for index in range(5):
            write_report(reports, f"com.acme.Test{index}", f"{index + 1}.0")

        _, output = run(str(self.root), "--top", "2")

        self.assertIn("Slowest 2 classes:", output)
        self.assertIn("3 more classes are not listed", output)
        self.assertNotIn("com.acme.Test0", output)

    def test_ignores_xml_that_is_not_a_test_suite(self):
        reports = self.root / "target" / "surefire-reports"
        write_report(reports, "com.acme.RealTest", "3.0")
        (reports / "TEST-broken.xml").write_text("<testsuite", encoding="utf-8")
        (reports / "TEST-other.xml").write_text("<report/>", encoding="utf-8")

        _, output = run(str(self.root))

        self.assertIn("1 test classes", output)

    def test_fails_with_a_hint_when_there_are_no_reports(self):
        exit_code, _ = run(str(self.root))

        self.assertIn("No test reports found", str(exit_code))
        self.assertIn("Run the tests first", str(exit_code))


if __name__ == "__main__":
    unittest.main()
