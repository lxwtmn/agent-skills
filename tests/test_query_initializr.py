import contextlib
import http.client
import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "spring-boot-initializr" / "scripts"))

import query_initializr

METADATA = str(Path(__file__).resolve().parent / "fixtures" / "initializr-metadata.json")


def run(*arguments):
    output = io.StringIO()
    exit_code = 0
    with contextlib.redirect_stdout(output):
        try:
            query_initializr.main(["--from-file", METADATA, *arguments])
        except SystemExit as stop:
            exit_code = stop.code
    return exit_code, output.getvalue()


class VersionRangeTest(unittest.TestCase):

    def test_release_inside_half_open_range(self):
        self.assertTrue(query_initializr.version_in_range("4.2.0", "[4.0.0,4.3.0-M1)"))

    def test_upper_bound_is_exclusive(self):
        self.assertFalse(query_initializr.version_in_range("4.3.0-M1", "[4.0.0,4.3.0-M1)"))

    def test_snapshot_of_next_patch_is_above_previous_minor_range(self):
        self.assertFalse(query_initializr.version_in_range("4.2.1-SNAPSHOT", "[4.0.0,4.2.0-M1)"))

    def test_bare_version_means_that_version_or_newer(self):
        self.assertTrue(query_initializr.version_in_range("4.2.0", "4.2.0"))
        self.assertFalse(query_initializr.version_in_range("4.1.3", "4.2.0"))

    def test_qualifiers_order_milestone_candidate_snapshot_release(self):
        ordered = ["4.1.0-M1", "4.1.0-M2", "4.1.0-RC1", "4.1.0-SNAPSHOT", "4.1.0"]
        parsed = [query_initializr.parse_version(version) for version in ordered]
        self.assertEqual(parsed, sorted(parsed))

    def test_legacy_ids_compare_like_semver_ids(self):
        self.assertEqual(query_initializr.parse_version("4.2.0.RELEASE"),
                         query_initializr.parse_version("4.2.0"))
        self.assertEqual(query_initializr.parse_version("4.2.1.BUILD-SNAPSHOT"),
                         query_initializr.parse_version("4.2.1-SNAPSHOT"))

    def test_empty_range_accepts_everything(self):
        self.assertTrue(query_initializr.version_in_range("4.2.0", ""))

    def test_unparsable_range_is_unknown_rather_than_a_verdict(self):
        self.assertIsNone(query_initializr.version_in_range("4.2.0", "2.2.x"))


class ValidateCommandTest(unittest.TestCase):

    def test_known_compatible_ids_pass_against_service_default(self):
        exit_code, output = run("validate", "web,data-jpa,postgresql")
        self.assertEqual(exit_code, 0)
        self.assertIn("Checked against Spring Boot 4.2.0 (service default)", output)
        self.assertIn("All dependency IDs are valid.", output)

    def test_unknown_id_fails_with_suggestion(self):
        exit_code, output = run("validate", "web,jpa")
        self.assertEqual(exit_code, 1)
        self.assertIn("jpa  did you mean: data-jpa", output)

    def test_incompatible_id_fails_and_names_required_range(self):
        exit_code, output = run("validate", "web,session-data-mongodb")
        self.assertEqual(exit_code, 1)
        self.assertIn("Incompatible with Spring Boot 4.2.0", output)
        self.assertIn("requires Boot [4.0.0,4.1.0-M1)", output)

    def test_same_id_passes_for_a_boot_version_inside_its_range(self):
        exit_code, _ = run("validate", "web,session-data-mongodb", "--boot-version", "4.0.10")
        self.assertEqual(exit_code, 0)

    def test_minimum_version_dependency_fails_on_older_boot(self):
        exit_code, output = run("validate", "newcomer", "--boot-version", "4.1.3")
        self.assertEqual(exit_code, 1)
        self.assertIn("requires Boot 4.2.0", output)

    def test_boot_version_the_instance_does_not_offer_fails(self):
        exit_code, output = run("validate", "web", "--boot-version", "3.5.0")
        self.assertEqual(exit_code, 1)
        self.assertIn("Spring Boot 3.5.0 is not offered", output)

    def test_unparsable_range_is_reported_without_failing(self):
        exit_code, output = run("validate", "oddball")
        self.assertEqual(exit_code, 0)
        self.assertIn("compatibility could not be checked", output)


class FakeResponse:

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *details):
        return False

    def read(self):
        return self.body


class FetchMetadataTest(unittest.TestCase):

    def setUp(self):
        self.metadata = Path(METADATA).read_bytes()
        self.sleep = mock.patch.object(query_initializr.time, "sleep")
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def test_retries_when_the_response_breaks_off_mid_read(self):
        outcomes = [http.client.IncompleteRead(b"{", 100), FakeResponse(self.metadata)]
        with mock.patch.object(query_initializr.urllib.request, "urlopen", side_effect=outcomes) as urlopen:
            metadata = query_initializr.fetch_metadata("https://start.example.org")

        self.assertEqual(metadata["bootVersion"]["default"], "4.2.0")
        self.assertEqual(urlopen.call_count, 2)

    def test_gives_up_with_a_readable_message_after_repeated_failures(self):
        broken = http.client.IncompleteRead(b"{", 100)
        with mock.patch.object(query_initializr.urllib.request, "urlopen", side_effect=broken) as urlopen:
            with self.assertRaises(SystemExit) as stop:
                query_initializr.fetch_metadata("https://start.example.org")

        self.assertIn("broke off 3 times", str(stop.exception.code))
        self.assertEqual(urlopen.call_count, 3)

    def test_unreachable_host_fails_at_once_without_retry(self):
        unreachable = urllib.error.URLError("nodename nor servname provided")
        with mock.patch.object(query_initializr.urllib.request, "urlopen", side_effect=unreachable) as urlopen:
            with self.assertRaises(SystemExit) as stop:
                query_initializr.fetch_metadata("https://start.example.org")

        self.assertIn("Could not reach https://start.example.org/", str(stop.exception.code))
        self.assertEqual(urlopen.call_count, 1)


class ListingCommandsTest(unittest.TestCase):

    def test_versions_marks_service_defaults(self):
        _, output = run("versions")
        self.assertIn("4.2.0  (default)", output)
        self.assertIn("gradle-project  [Gradle - Groovy]  (default)", output)
        self.assertIn("17  (default)", output)

    def test_search_matches_id_name_and_description_case_insensitively(self):
        _, output = run("search", "POSTGRES")
        self.assertIn("postgresql  ->  PostgreSQL Driver", output)
        self.assertNotIn("data-jpa", output)

    def test_search_shows_compatibility_range(self):
        _, output = run("search", "session")
        self.assertIn("(Boot [4.0.0,4.1.0-M1))", output)

    def test_deps_filters_by_group_ignoring_case(self):
        _, output = run("deps", "sql")
        self.assertIn("data-jpa", output)
        self.assertNotIn("session-data-mongodb", output)

    def test_deps_with_unknown_group_lists_available_groups(self):
        _, output = run("deps", "nosuchgroup")
        self.assertIn("Available groups:", output)
        self.assertIn("- SQL", output)


if __name__ == "__main__":
    unittest.main()
