import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_data_provenance import validate


class DataProvenanceTest(unittest.TestCase):
    def test_repository_manifest_is_complete_and_current(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(validate(root), [])

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        observed = root / "data/observed"
        observed.mkdir(parents=True)
        data_file = observed / "sample.csv"
        data_file.write_text("year,value\n2026,1\n", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "datasets": {
                "example": {
                    "provider": "Example provider",
                    "source_urls": ["https://example.test/data"],
                    "license": "Example terms",
                    "redistribution": "Allowed with attribution",
                    "citation": "Example provider (2026)",
                }
            },
            "files": {
                "data/observed/sample.csv": {
                    "dataset": "example",
                    "recorded_on": "2026-09-18",
                    "date_basis": "downloaded",
                    "transformation": "None",
                    "sha256": hashlib.sha256(data_file.read_bytes()).hexdigest(),
                }
            },
        }
        manifest_file = observed / "PROVENANCE.json"
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        return temporary, root, manifest_file

    def test_unregistered_file_fails(self):
        temporary, root, _ = self._fixture()
        self.addCleanup(temporary.cleanup)
        (root / "data/observed/new.csv").write_text("new\n", encoding="utf-8")
        self.assertIn(
            "unregistered observed file: data/observed/new.csv",
            validate(root),
        )

    def test_checksum_mismatch_fails(self):
        temporary, root, _ = self._fixture()
        self.addCleanup(temporary.cleanup)
        (root / "data/observed/sample.csv").write_text("changed\n", encoding="utf-8")
        self.assertTrue(
            any("checksum mismatch" in error for error in validate(root)),
            validate(root),
        )

    def test_missing_license_fails(self):
        temporary, root, manifest_file = self._fixture()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["datasets"]["example"]["license"] = ""
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn(
            "dataset 'example'.license must be a non-empty string",
            validate(root),
        )


if __name__ == "__main__":
    unittest.main()
