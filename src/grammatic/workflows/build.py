from __future__ import annotations

import platform

from grammatic.contracts import BuildRequest, BuildResult, Diagnostic
from grammatic.workspace import WorkshopLayout

from .common import append_build_log, now_ms, run


def platform_ldflag() -> str:
    system = platform.system()
    if system == "Linux":
        return "-shared"
    if system == "Darwin":
        return "-dynamiclib"
    raise ValueError(f"Unsupported platform: {system}")


def handle_build(request: BuildRequest) -> BuildResult:
    started = now_ms()
    layout = WorkshopLayout(repo_root=request.repo_root)
    workspace = layout.for_grammar(request.grammar)
    parser_c = workspace.src_dir / "parser.c"
    if not parser_c.is_file():
        return BuildResult(
            status="error",
            grammar=request.grammar,
            artifact_path=workspace.so_path,
            compiler="gcc",
            duration_ms=now_ms() - started,
            diagnostics=[
                Diagnostic(level="error", message=f"Error: {parser_c} not found"),
                Diagnostic(level="error", message=f"Run 'tree-sitter generate' in {workspace.grammar_dir} first"),
            ],
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

    run_result = run(cmd)
    duration = now_ms() - started
    diagnostics: list[Diagnostic] = []
    if run_result.stdout.strip():
        diagnostics.append(Diagnostic(level="info", message=run_result.stdout.strip()))
    if run_result.stderr.strip():
        diagnostics.append(Diagnostic(level="info" if run_result.returncode == 0 else "error", message=run_result.stderr.strip()))

    if run_result.returncode == 0 and workspace.so_path.is_file():
        commit_result = run(["git", "rev-parse", "HEAD"], cwd=workspace.grammar_dir)
        url_result = run(["git", "config", "--get", "remote.origin.url"], cwd=workspace.grammar_dir)
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
        repo_url = url_result.stdout.strip() if url_result.returncode == 0 else "unknown"
        append_build_log(layout, request.grammar, commit, repo_url, workspace.so_path, duration)

    return BuildResult(
        status="ok" if run_result.returncode == 0 and workspace.so_path.is_file() else "error",
        grammar=request.grammar,
        artifact_path=workspace.so_path,
        compiler=compiler,
        duration_ms=duration,
        diagnostics=diagnostics,
    )
