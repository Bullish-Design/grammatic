from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "log_writer.py"

spec = importlib.util.spec_from_file_location("log_writer", SCRIPT)
assert spec is not None and spec.loader is not None
log_writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log_writer)


class TestLogWriter:
    def test_build_log_generation(self) -> None:
        (ROOT / "grammars" / "test" / "src").mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "build",
                "--grammar",
                "test",
                "--commit",
                "abc123",
                "--repo-url",
                "https://example.com/test",
                "--so-path",
                "build/test.so",
                "--build-time",
                "1234",
                "--tree-sitter-version",
                "0.21.0",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["event_type"] == "build"
        assert log_entry["grammar"] == "test"
        assert log_entry["commit"] == "abc123"
        assert log_entry["repo_url"] == "https://example.com/test"
        assert log_entry["so_path"] == str((ROOT / "build" / "test.so").resolve())
        assert log_entry["build_success"] is True
        assert log_entry["build_time_ms"] == 1234
        assert log_entry["compiler"] == "gcc"
        assert log_entry["tree_sitter_version"] == "0.21.0"

    def test_build_log_generation_with_cpp_scanner(self, tmp_path: Path) -> None:
        grammar_dir = ROOT / "grammars" / "test" / "src"
        grammar_dir.mkdir(parents=True, exist_ok=True)
        scanner_cc = grammar_dir / "scanner.cc"
        scanner_cc.write_text("// scanner")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(ROOT),
                    "build",
                    "--grammar",
                    "test",
                    "--commit",
                    "abc123",
                    "--repo-url",
                    "https://example.com/test",
                    "--so-path",
                    str(tmp_path / "build" / "test.so"),
                    "--build-time",
                    "1234",
                    "--tree-sitter-version",
                    "0.21.0",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=ROOT,
            )

            log_entry = json.loads(result.stdout)
            assert log_entry["compiler"] == "g++"
        finally:
            scanner_cc.unlink(missing_ok=True)

    def test_build_log_generation_with_c_scanner(self, tmp_path: Path) -> None:
        grammar_dir = ROOT / "grammars" / "test" / "src"
        grammar_dir.mkdir(parents=True, exist_ok=True)
        scanner_c = grammar_dir / "scanner.c"
        scanner_c.write_text("/* scanner */")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(ROOT),
                    "build",
                    "--grammar",
                    "test",
                    "--commit",
                    "abc123",
                    "--repo-url",
                    "https://example.com/test",
                    "--so-path",
                    str(tmp_path / "build" / "test.so"),
                    "--build-time",
                    "1234",
                    "--tree-sitter-version",
                    "0.21.0",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=ROOT,
            )

            log_entry = json.loads(result.stdout)
            assert log_entry["compiler"] == "gcc"
        finally:
            scanner_c.unlink(missing_ok=True)

    def test_parse_log_generation(self, tmp_path: Path) -> None:
        parse_result = tmp_path / "parse.json"
        parse_result.write_text((ROOT / "tests" / "fixtures" / "sample_parse.json").read_text())

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "parse",
                "--grammar",
                "test",
                "--source",
                "tests/fixtures/sample.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["event_type"] == "parse"
        assert log_entry["grammar"] == "test"
        assert log_entry["source_file"] == str((ROOT / "tests" / "fixtures" / "sample.py").resolve())
        assert log_entry["node_count"] == 3
        assert log_entry["has_errors"] is False
        assert log_entry["parse_time_ms"] == 12
        assert log_entry["root_node_type"] == "source_file"

    def test_error_node_detection(self, tmp_path: Path) -> None:
        parse_result = tmp_path / "parse_errors.json"
        parse_result.write_text((ROOT / "tests" / "fixtures" / "sample_parse_with_errors.json").read_text())

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "parse",
                "--grammar",
                "test",
                "--source",
                "tests/fixtures/bad.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "8",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["has_errors"] is True

    def test_node_counting(self, tmp_path: Path) -> None:
        parse_result = tmp_path / "nested_parse.json"
        parse_result.write_text(
            json.dumps(
                {
                    "root_node": {
                        "type": "source",
                        "children": [
                            {"type": "a", "children": []},
                            {
                                "type": "b",
                                "children": [
                                    {"type": "c", "children": []},
                                    {"type": "d", "children": []},
                                ],
                            },
                        ],
                    }
                }
            )
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.txt",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "5",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["node_count"] == 5

    def test_grammar_version_lookup(self, tmp_path: Path, monkeypatch) -> None:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        (logs_dir / "builds.jsonl").write_text(json.dumps({"grammar": "test", "commit": "xyz789"}) + "\n")

        parse_result = tmp_path / "parse.json"
        parse_result.write_text(json.dumps({"root_node": {"type": "module", "children": []}}))

        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(tmp_path),
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["grammar_version"] == "xyz789"

    def test_missing_builds_log(self, tmp_path: Path, monkeypatch) -> None:
        parse_result = tmp_path / "parse.json"
        parse_result.write_text(json.dumps({"root_node": {"type": "module", "children": []}}))

        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(tmp_path),
                "parse",
                "--grammar",
                "test",
                "--source",
                "test.py",
                "--parse-result",
                str(parse_result),
                "--parse-time",
                "12",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_entry = json.loads(result.stdout)
        assert log_entry["grammar_version"] == "unknown"

    def test_parse_with_non_root_working_directory(self, tmp_path: Path) -> None:
        logs_dir = ROOT / "logs"
        logs_dir.mkdir(exist_ok=True)
        builds_log = logs_dir / "builds.jsonl"
        original = builds_log.read_text() if builds_log.exists() else None

        nested_cwd = tmp_path / "nested" / "dir"
        nested_cwd.mkdir(parents=True)

        try:
            builds_log.write_text(json.dumps({"grammar": "test", "commit": "nonroot123"}) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root",
                    str(ROOT),
                    "parse",
                    "--grammar",
                    "test",
                    "--source",
                    "tests/fixtures/sample.py",
                    "--parse-result",
                    "tests/fixtures/sample_parse.json",
                    "--parse-time",
                    "12",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=nested_cwd,
            )

            log_entry = json.loads(result.stdout)
            assert log_entry["grammar_version"] == "nonroot123"
            assert log_entry["source_file"] == str((ROOT / "tests" / "fixtures" / "sample.py").resolve())
        finally:
            if original is None:
                builds_log.unlink(missing_ok=True)
            else:
                builds_log.write_text(original)


class TestLogValidation:
    def test_valid_jsonl_format(self) -> None:
        (ROOT / "grammars" / "test" / "src").mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "build",
                "--grammar",
                "test",
                "--commit",
                "abc",
                "--repo-url",
                "https://example.com",
                "--so-path",
                "test.so",
                "--build-time",
                "100",
                "--tree-sitter-version",
                "0.21.0",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) == 1
        json.loads(lines[0])

    def test_append_to_log_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test.jsonl"

        for i in range(3):
            (ROOT / "grammars" / f"test{i}" / "src").mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as handle:
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--project-root",
                        str(ROOT),
                        "build",
                        "--grammar",
                        f"test{i}",
                        "--commit",
                        f"commit{i}",
                        "--repo-url",
                        "https://example.com",
                        "--so-path",
                        "test.so",
                        "--build-time",
                        "100",
                        "--tree-sitter-version",
                        "0.21.0",
                    ],
                    stdout=handle,
                    check=True,
                    cwd=ROOT,
                )

        with log_file.open(encoding="utf-8") as handle:
            entries = [json.loads(line) for line in handle]

        assert len(entries) == 3
        assert entries[0]["grammar"] == "test0"
        assert entries[2]["grammar"] == "test2"
