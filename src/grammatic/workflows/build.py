from __future__ import annotations

import platform

from pydantic import ValidationError as PydanticValidationError

from grammatic.contracts import BuildRequest, BuildResult, Diagnostic
from grammatic.errors import ArtifactMissingError, ValidationError
from grammatic.workspace import WorkshopLayout

from .common import append_build_log, now_ms, run, run_checked


def platform_ldflag() -> str:
    system = platform.system()
    if system == "Linux":
        return "-shared"
    if system == "Darwin":
        return "-dynamiclib"
    raise ValidationError(f"Unsupported platform: {system}")


def handle_build(request: BuildRequest) -> BuildResult:
    started = now_ms()
    try:
        layout = WorkshopLayout(repo_root=request.repo_root)
        workspace = layout.for_grammar(request.grammar)
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError(str(exc)) from exc

    parser_c = workspace.src_dir / "parser.c"
    if not parser_c.is_file():
        raise ArtifactMissingError(
            f"Generated parser not found: {parser_c}. Run 'just generate {request.grammar}' first"
        )

    scanner_cc = workspace.src_dir / "scanner.cc"
    scanner_c = workspace.src_dir / "scanner.c"
    compiler = "g++" if scanner_cc.is_file() else "gcc"
    scanner = scanner_cc if scanner_cc.is_file() else scanner_c if scanner_c.is_file() else None

    workspace.build_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        compiler,
        platform_ldflag(),
        "-fPIC",
        "-O2",
        f"-I{workspace.src_dir}",
        str(parser_c),
    ]
    if scanner is not None:
        cmd.append(str(scanner))
    cmd.extend(["-o", str(workspace.so_path)])

    run_result = run_checked(cmd, message=f"Failed to build grammar '{request.grammar}'")
    duration = now_ms() - started

    if not workspace.so_path.is_file():
        raise ArtifactMissingError(f"Build completed but expected artifact is missing: {workspace.so_path}")

    commit_result = run(["git", "rev-parse", "HEAD"], cwd=workspace.grammar_dir)
    url_result = run(["git", "config", "--get", "remote.origin.url"], cwd=workspace.grammar_dir)
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
    repo_url = url_result.stdout.strip() if url_result.returncode == 0 else "unknown"
    append_build_log(layout, request.grammar, commit, repo_url, workspace.so_path, duration)

    diagnostics: list[Diagnostic] = []
    if run_result.stdout.strip():
        diagnostics.append(Diagnostic(level="info", message=run_result.stdout.strip()))
    if run_result.stderr.strip():
        diagnostics.append(Diagnostic(level="info", message=run_result.stderr.strip()))

    return BuildResult(
        status="ok",
        grammar=request.grammar,
        artifact_path=workspace.so_path,
        compiler=compiler,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
