import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from log_reader import discover_logs, read_logs


class LogReaderTests(unittest.TestCase):
    def test_only_active_logs_in_root_are_projects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            history = root / "historico"
            history.mkdir()
            (root / "alpha_control.log").touch()
            (root / "alpha_control.log.2026-10-31").touch()
            (history / "alpha_control.log.2026-10-31").touch()
            (root / "control.log").touch()
            (root / "unrelated.log").touch()
            projects = discover_logs(root)
            self.assertEqual(list(projects), ["alpha", "control.log"])
            self.assertIsInstance(projects["alpha"], Path)

    def test_reads_old_lines_and_raw_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "alpha_control.log"
            path.write_text(
                "2000-01-01 05:30:07,523 | INFO | legacy record\n"
                "2026-10-31 05:30:08,105 | ERROR | backup failed\n"
                "line without timestamp\n",
                encoding="utf-8",
            )
            os.utime(path, None)
            result = read_logs(temporary, project="alpha", level="INFO", query="LEGACY")
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["entries"][0]["message"], "legacy record")
            self.assertEqual(result["entries"][0]["display_time"], "2000-01-01 05:30:07,523")
            raw = read_logs(temporary, project="alpha", level="RAW")
            self.assertEqual(raw["entries"][0]["message"], "line without timestamp")

    def test_entire_active_file_is_reachable_through_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "control.log"
            start = datetime(2000, 1, 1)
            path.write_text("".join(
                f"{(start + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} | INFO | line {i}\n"
                for i in range(2001)
            ), encoding="utf-8")
            result = read_logs(temporary, project="control.log", page=41)
            self.assertEqual(result["total"], 2001)
            self.assertEqual(result["page"], 41)
            self.assertEqual(result["entries"][0]["message"], "line 0")


if __name__ == "__main__":
    unittest.main()
