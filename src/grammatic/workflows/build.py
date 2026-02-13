from __future__ import annotations

import platform

from grammatic.contracts import BuildRequest, BuildResult, Diagnostic
from grammatic.errors import (
    ArtifactMissingError,
    GrammaticError,
    SubprocessExecutionError,
    ValidationError,
    bounded_output_excerpt,
)
from grammatic.event_logs import append_build_event, build_event
from grammatic.preflight import (
    ensure_required_paths_for_build,
    ensure_tools_for_build,
    resolve_grammar_workspace,
)

from .common import detect_compiler, now_ms, run, run_checked, tree_sitter_version


def platform_ldflag() -> str:
    system = platform.system()
    if system == "Linux":
        return "-shared"
    if system == "Darwin":
        return "-dynamiclib"
    raise ValidationError(f"Unsupported platform: {system}")


def _resolve_git_metadata(workspace) -> tuple[str, str]:
    commit_result = run(["git", "rev-parse", "HEAD"], cwd=workspace.grammar_dir)
    url_result = run(["git", "config", "--get", "remote.origin.url"], cwd=workspace.grammar_dir)
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
    repo_url = url_result.stdout.strip() if url_result.returncode == 0 else "unknown"
    return commit, repo_url


def _failure_diagnostic(exc: Exception) -> tuple[str, list[Diagnostic], str | None]:
    error_code = type(exc).__name__.upper()
    if isinstance(exc, SubprocessExecutionError):
        excerpt = exc.excerpt()
        command = " ".join(exc.command)
        diagnostics = [
            Diagnostic(level="error", message=str(exc)),
            Diagnostic(level="error", message=f"command: {command}"),
        ]
        if excerpt:
            diagnostics.append(Diagnostic(level="error", message=f"output excerpt: {excerpt}"))
    else:
        excerpt = bounded_output_excerpt(str(exc), "")
        diagnostics = [Diagnostic(level="error", message=str(exc))]
    return error_code, diagnostics, excerpt


def handle_build(request: BuildRequest) -> BuildResult:
    started = now_ms()
    layout, workspace = resolve_grammar_workspace(request.repo_root, request.grammar)

    parser_c = workspace.src_dir / "parser.c"
    scanner_cc = workspace.src_dir / "scanner.cc"
    scanner_c = workspace.src_dir / "scanner.c"
    compiler = "g++" if scanner_cc.is_file() else "gcc"
    scanner = scanner_cc if scanner_cc.is_file() else scanner_c if scanner_c.is_file() else None

    ensure_tools_for_build(workspace)
    commit, repo_url = _resolve_git_metadata(workspace)

    try:
        ensure_required_paths_for_build(workspace)

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

        diagnostics: list[Diagnostic] = []
        if run_result.stdout.strip():
            diagnostics.append(Diagnostic(level="info", message=run_result.stdout.strip()))
        if run_result.stderr.strip():
            diagnostics.append(Diagnostic(level="info", message=run_result.stderr.strip()))

        append_build_event(
            layout,
            build_event(
                grammar=request.grammar,
                commit=commit,
                repo_url=repo_url,
                so_path=workspace.so_path,
                compiler=compiler,
                tree_sitter_version=tree_sitter_version(),
                status="success",
                duration_ms=duration,
                diagnostics=diagnostics,
            ),
        )

        return BuildResult(
            status="ok",
            grammar=request.grammar,
            artifact_path=workspace.so_path,
            compiler=compiler,
            duration_ms=duration,
            diagnostics=diagnostics,
        )
    except GrammaticError as exc:
        duration = now_ms() - started
        error_code, diagnostics, stderr_excerpt = _failure_diagnostic(exc)
        append_build_event(
            layout,
            build_event(
                grammar=request.grammar,
                commit=commit,
                repo_url=repo_url,
                so_path=workspace.so_path,
                compiler=detect_compiler(workspace.grammar_dir),
                tree_sitter_version=tree_sitter_version(),
                status="failure",
                duration_ms=duration,
                diagnostics=diagnostics,
                error_code=error_code,
                stderr_excerpt=stderr_excerpt,
            ),
        )
        raise

