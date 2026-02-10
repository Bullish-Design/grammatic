# Grammatic Development Roadmap

## Overview

This roadmap breaks Grammatic development into 7 phases, each with clear boundaries, independent test suites, and minimal cross-phase dependencies. Each phase can be completed and verified before moving to the next.

## Phase Dependency Graph

```
Phase 1: Foundation
    â"‚
    â"œâ"€â"€â"€> Phase 2: Build System
    â"‚        â"‚
    â"‚        â""â"€â"€â"€> Phase 3: Logging
    â"‚                 â"‚
    â""â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"´â"€â"€â"€> Phase 4: Core Justfile
                         â"‚
                         â""â"€â"€â"€> Phase 5: Parse & Test
                                  â"‚
                                  â""â"€â"€â"€> Phase 6: Queries
                                           â"‚
                                           â""â"€â"€â"€> Phase 7: Developer UX
```

## Phase Summary

### Phase 1: Foundation & Data Models
**Duration:** 1-2 days  
**Files:** 8 files  
**Tests:** 15 tests  

Creates project structure, environment configuration, and Pydantic models. Zero runtime dependencies.

**Key Deliverables:**
- `devenv.nix` with all tools
- `pyproject.toml` for UV workspace
- Pydantic models for logs
- Base test infrastructure

**Validation:** `pytest tests/test_models.py -v`

---

### Phase 2: Grammar Build System
**Duration:** 2-3 days  
**Files:** 5 files  
**Tests:** 12 tests  

Implements bash compilation script with platform detection and scanner handling.

**Key Deliverables:**
- `scripts/build_grammar.sh`
- Test fixtures with minimal grammars
- Compiler detection logic

**Validation:** `pytest tests/test_build_script.py -v`

---

### Phase 3: Logging Infrastructure
**Duration:** 2 days  
**Files:** 4 files  
**Tests:** 14 tests  

Creates UV-based log writer with JSONL output and Pydantic validation.

**Key Deliverables:**
- `scripts/log_writer.py`
- Node counting logic
- ERROR detection
- Grammar version lookup

**Validation:** `pytest tests/test_log_writer.py -v`

---

### Phase 4: Core Justfile Targets
**Duration:** 3-4 days  
**Files:** 2 files  
**Tests:** 18 tests  

Orchestrates workflow with justfile targets for init, add-grammar, generate, build.

**Key Deliverables:**
- `justfile` with core targets
- Git submodule integration
- Build logging integration

**Validation:** `pytest tests/test_justfile_core.py -v`

---

### Phase 5: Parse & Test Integration
**Duration:** 2-3 days  
**Files:** 6 files  
**Tests:** 12 tests  

Adds parse target, corpus test runner, and integration tests.

**Key Deliverables:**
- Parse target with logging
- test-grammar target
- Sample fixtures
- Corpus test examples

**Validation:** `pytest tests/test_parse.py -v`

---

### Phase 6: Query & Analysis
**Duration:** 2 days  
**Files:** 3 files  
**Tests:** 16 tests  

Implements jq-based queries for log analysis and metrics.

**Key Deliverables:**
- Log query targets
- Metrics computation
- Export functionality
- Complex query script

**Validation:** `pytest tests/test_queries.py -v`

---

### Phase 7: Developer Experience
**Duration:** 2-3 days  
**Files:** 4 files  
**Tests:** 12 tests + 1 integration  

Polishes workflow with watch mode, templates, and diagnostics.

**Key Deliverables:**
- Watch mode
- Grammar template generator
- list-grammars and info targets
- grammar_doctor script
- Pre-commit hooks

**Validation:** `pytest tests/test_developer_ux.py tests/test_full_workflow.py -v`

---

## Milestones

### Milestone 1: Basic Functionality (Phases 1-3)
**Target:** 5-7 days  
**Outcome:** Can compile grammars and log events  
**Demo:** Build tree-sitter-python, verify logs

### Milestone 2: Workflow Integration (Phase 4)
**Target:** 8-11 days  
**Outcome:** Complete justfile workflow  
**Demo:** `just rebuild python` works end-to-end

### Milestone 3: Testing & Analysis (Phases 5-6)
**Target:** 12-15 days  
**Outcome:** Parse testing and log queries working  
**Demo:** Run corpus tests, query metrics

### Milestone 4: Production Ready (Phase 7)
**Target:** 16-18 days  
**Outcome:** Full developer experience  
**Demo:** Create custom grammar with watch mode

---

## Testing Strategy

### Unit Tests
Each phase includes unit tests for its components:
- Models: Pydantic validation
- Scripts: Bash/Python logic
- Justfile: Recipe execution

### Integration Tests
Phase 4+ includes integration tests:
- Multi-step workflows
- Tool composition
- Log generation and querying

### Full Workflow Test
Phase 7 includes end-to-end test:
- Create grammar from template
- Build and test
- Query results
- Verify all artifacts

### Test Organization
```
tests/
â"œâ"€â"€ test_models.py           # Phase 1
â"œâ"€â"€ test_build_script.py     # Phase 2
â"œâ"€â"€ test_log_writer.py       # Phase 3
â"œâ"€â"€ test_justfile_core.py    # Phase 4
â"œâ"€â"€ test_parse.py            # Phase 5
â"œâ"€â"€ test_queries.py          # Phase 6
â"œâ"€â"€ test_developer_ux.py     # Phase 7
â"œâ"€â"€ test_full_workflow.py    # Phase 7
â""â"€â"€ fixtures/
    â"œâ"€â"€ minimal_grammar/
    â"œâ"€â"€ scanner_grammar/
    â""â"€â"€ sample_*.{py,txt}
```

---

## Implementation Guidelines

### For Each Phase:

1. **Read phase document thoroughly**
   - Understand deliverables
   - Review acceptance criteria
   - Note dependencies

2. **Create files in order**
   - Start with data/config files
   - Then scripts/logic
   - Finally tests

3. **Test incrementally**
   - Run tests after each file
   - Fix issues immediately
   - Don't proceed until tests pass

4. **Verify acceptance criteria**
   - Check off each criterion
   - Run full test suite
   - Test manually if needed

5. **Commit before next phase**
   - Clean git state
   - Descriptive commit message
   - Tag milestone commits

### Best Practices:

**File Creation:**
- Always include filepath in first line comment
- Use UV script format for Python
- Follow 120 char line limit
- Keep functions/methods small

**Testing:**
- Write tests before implementation when possible
- Use descriptive test names
- Test error cases, not just happy path
- Prefer integration tests for workflow validation

**Git Hygiene:**
- One phase = one or more logical commits
- Don't mix phases in single commit
- Test before committing
- Use feature branches if desired

---

## Risk Mitigation

### Potential Issues:

1. **Platform differences** (Phase 2)
   - Mitigation: Test on Linux and macOS
   - Fallback: Docker container for consistency

2. **Git submodule complexity** (Phase 4)
   - Mitigation: Test with real tree-sitter repos
   - Fallback: Allow local grammar directories

3. **JSONL corruption** (Phase 3)
   - Mitigation: Validate before/after writes
   - Fallback: Implement file locking or SQLite

4. **Tree-sitter version changes** (All phases)
   - Mitigation: Lock versions in devenv.nix
   - Fallback: Version compatibility matrix

---

## Success Criteria

### Phase Complete When:
- [ ] All files created per spec
- [ ] All tests pass
- [ ] Acceptance criteria met
- [ ] Manual testing successful
- [ ] Code committed to git

### Milestone Complete When:
- [ ] All phases in milestone complete
- [ ] Demo scenario works end-to-end
- [ ] Documentation updated
- [ ] No known blocking issues

### Project Complete When:
- [ ] All 7 phases complete
- [ ] Full workflow test passes
- [ ] README reflects actual functionality
- [ ] Can create, build, test custom grammar
- [ ] Logs queryable and exportable

---

## Post-Completion

### Documentation:
- Update README with real examples
- Add CONTRIBUTING.md
- Document known limitations
- Create example grammar tutorial

### Distribution:
- Tag v0.1.0 release
- Package as devenv module
- Share on tree-sitter Discussions
- Write blog post

### Future Work:
- SQLite log backend
- Grammar catalog/registry
- VSCode extension
- Windows support
- Web UI for log visualization

---

## Quick Reference

### Phase Artifacts:
1. Foundation: `devenv.nix`, `pyproject.toml`, models
2. Build System: `build_grammar.sh`
3. Logging: `log_writer.py`
4. Core Justfile: `justfile` (core targets)
5. Parse/Test: `justfile` (parse, test targets)
6. Queries: `justfile` (query targets), `query_logs.py`
7. Developer UX: `justfile` (ux targets), `grammar_doctor.py`

### Test Commands:
```bash
# Per phase
pytest tests/test_models.py -v           # Phase 1
pytest tests/test_build_script.py -v     # Phase 2
pytest tests/test_log_writer.py -v       # Phase 3
pytest tests/test_justfile_core.py -v    # Phase 4
pytest tests/test_parse.py -v            # Phase 5
pytest tests/test_queries.py -v          # Phase 6
pytest tests/test_developer_ux.py -v     # Phase 7
pytest tests/test_full_workflow.py -v    # Integration

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/grammatic --cov-report=html
```

### Just Targets by Phase:
```bash
# Phase 4: Core
just init
just add-grammar NAME URL
just generate GRAMMAR
just build GRAMMAR
just rebuild GRAMMAR
just clean
just clean-all

# Phase 5: Parse/Test
just parse GRAMMAR FILE
just test-grammar GRAMMAR
just test GRAMMAR

# Phase 6: Queries
just query-builds [N]
just query-builds-for GRAMMAR
just query-parses [N]
just query-failures
just query-parses-for GRAMMAR
just build-success-rate GRAMMAR
just avg-parse-time GRAMMAR
just export-logs OUTPUT
just validate-logs

# Phase 7: Developer UX
just watch GRAMMAR
just new-grammar NAME
just list-grammars
just info GRAMMAR
just doctor GRAMMAR
just help
```
