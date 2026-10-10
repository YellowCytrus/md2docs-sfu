from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path

from sfu_converter.application import composition, heading_checks, metadata_check
from sfu_converter.application.style_check import validate_style
from sfu_converter.application.units import validate_unit_consistency
from sfu_converter.config import PathConfig, SIBFUConfig
from sfu_converter.domain.ast_nodes import BlockType, SourceSpan
from sfu_converter.domain.constants import DEFAULT_PROFILE_NAME
from sfu_converter.domain.diagnostics import Diagnostic, DiagnosticCodes, Severity
from sfu_converter.domain.formatting import FormattingProfile, RuleStatus, unsupported_rule_diagnostics
from sfu_converter.infrastructure.appendix import assign_appendix_letters
from sfu_converter.infrastructure.docx_validator import diagnostic_to_json
from sfu_converter.infrastructure.graphics import validate as validate_graphics
from sfu_converter.infrastructure.project_designation import validate_document_designations
from sfu_converter.parser import DEFAULT_SYNTAX_VERSION, get_parser
from sfu_converter.parser.syntax_spec import get_syntax_spec
from sfu_converter.registry import get_profile, iter_profiles
from sfu_converter.registry.coverage import build_rows, parser_support_for_rule, render_json, render_markdown
from sfu_converter.runtime_resources import packaged_template_exists


class ExitCodes:
    SUCCESS = 0
    WARNINGS_STRICT = 1
    VALIDATION_ERROR = 2
    MISSING_RESOURCE = 3
    WRITE_FAILURE = 4
    INTERNAL_ERROR = 5
    INVALID_USAGE = 64


class CliError(Exception):
    """Base class for structured CLI errors."""


class ProfileNotFoundError(CliError):
    def __init__(self, profile_name: str):
        self.profile_name = profile_name
        super().__init__(f"Unknown profile: {profile_name}")


class ConverterArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(ExitCodes.INVALID_USAGE, f"{self.prog}: error: {message}\n")


def create_parser() -> argparse.ArgumentParser:
    parser = ConverterArgumentParser(
        prog="sfu-converter",
        description="TXT to DOCX converter with SFU formatting standards",
    )
    _add_common_options(parser, include_defaults=True)

    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_p = subparsers.add_parser("convert", help="Convert TXT to DOCX")
    _add_common_options(convert_p, include_defaults=False)
    convert_p.add_argument("--input", required=True, type=Path)
    convert_p.add_argument("--output", required=True, type=Path)
    convert_p.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    convert_p.add_argument("--template", type=Path, default=None)
    convert_p.add_argument(
        "--template-mode",
        choices=["append", "preserve-prefix", "replace-body"],
        default="append",
    )
    convert_p.add_argument("--insert-after-page", type=int, default=None)
    convert_p.add_argument("--insert-at-bookmark", default=None)
    convert_p.add_argument("--syntax-version", type=int, choices=[1, 2], default=DEFAULT_SYNTAX_VERSION)
    convert_p.add_argument("--strict", action="store_true")
    convert_p.add_argument(
        "--skip-generated-front-matter",
        action="store_true",
        help="Skip generated title page and table of contents blocks",
    )
    convert_p.add_argument("--validate-output", action="store_true")
    convert_p.add_argument("--diagnostics", type=Path, default=None)
    convert_p.add_argument("--output-format", choices=["docx", "pptx"], default="docx")

    validate_p = subparsers.add_parser("validate-docx", help="Validate existing DOCX")
    _add_common_options(validate_p, include_defaults=False)
    validate_p.add_argument("--input", required=True, type=Path)
    validate_p.add_argument("--profile", default=DEFAULT_PROFILE_NAME)

    parse_p = subparsers.add_parser("parse", help="Parse TXT to AST")
    _add_common_options(parse_p, include_defaults=False)
    parse_p.add_argument("--input", required=True, type=Path)
    parse_p.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    parse_p.add_argument("--syntax-version", type=int, default=DEFAULT_SYNTAX_VERSION)
    parse_p.add_argument("--strict", action="store_true")

    lint_p = subparsers.add_parser("lint", help="Lint TXT syntax")
    _add_common_options(lint_p, include_defaults=False)
    lint_p.add_argument("--input", required=True, type=Path)
    lint_p.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    lint_p.add_argument("--syntax-version", type=int, default=DEFAULT_SYNTAX_VERSION)
    lint_p.add_argument("--strict", action="store_true")

    list_profiles_p = subparsers.add_parser("list-profiles", help="List formatting profiles")
    _add_common_options(list_profiles_p, include_defaults=False)
    list_profiles_p.add_argument("--profile", default=DEFAULT_PROFILE_NAME)

    explain_p = subparsers.add_parser("explain-syntax", help="Show TXT syntax")
    _add_common_options(explain_p, include_defaults=False)
    explain_p.add_argument("--syntax-version", type=int, choices=[1, 2], default=DEFAULT_SYNTAX_VERSION)

    schema_p = subparsers.add_parser("export-schema", help="Export JSON schemas")
    _add_common_options(schema_p, include_defaults=False)
    schema_p.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    schema_p.add_argument(
        "--schema",
        required=True,
        choices=["diagnostics", "ast", "profiles", "results", "coverage_matrix"],
    )

    interactive_p = subparsers.add_parser("interactive", help="Start interactive menu")
    _add_common_options(interactive_p, include_defaults=False)

    coverage_p = subparsers.add_parser("export-coverage", help="Export standard coverage matrix")
    coverage_p.add_argument("--format", choices=["md", "json"], default="md")

    agents_p = subparsers.add_parser("agents", help="Install skills into AI agents")
    agents_p.add_argument("action", nargs="?", choices=["install", "list"], default="install")
    agents_p.add_argument("--only", action="append", default=[], help="Install only for claude or codex")
    agents_p.add_argument("--all", dest="install_all", action="store_true", help="Install into all detected agents")
    agents_p.add_argument("--dry-run", action="store_true", help="Print commands without running them")

    return parser


def _add_common_options(parser: argparse.ArgumentParser, include_defaults: bool) -> None:
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text" if include_defaults else argparse.SUPPRESS,
        help="Output format",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False if include_defaults else argparse.SUPPRESS,
        help="Suppress non-essential stderr output",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False if include_defaults else argparse.SUPPRESS,
        help="Disable ANSI color output",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path(".") if include_defaults else argparse.SUPPRESS,
        help="Base directory for relative paths",
    )


def make_json_result(command: str, ok: bool, **kwargs) -> dict:
    return {
        "ok": ok,
        "command": command,
        **kwargs,
        "diagnostics": kwargs.get("diagnostics", []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    handlers = {
        "convert": cmd_convert,
        "validate-docx": cmd_validate_docx,
        "interactive": cmd_interactive,
        "parse": cmd_parse,
        "lint": cmd_lint,
        "list-profiles": cmd_list_profiles,
        "explain-syntax": cmd_explain_syntax,
        "export-schema": cmd_export_schema,
        "export-coverage": cmd_export_coverage,
        "agents": cmd_agents,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return ExitCodes.INVALID_USAGE
    return handler(args)


def cmd_convert(args) -> int:
    from sfu_converter.converter import TextToDocxConverter
    from sfu_converter.validator import StyleValidator

    if getattr(args, "output_format", "docx") == "pptx":
        return _cmd_convert_pptx(args)

    start = time.time()
    profile = _resolve_profile_arg(args, "convert")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    input_path = _resolve_path(args.workdir, args.input)
    output_path = _resolve_path(args.workdir, args.output)

    if not input_path.exists():
        _emit_missing_resource(args, "convert", "MISSING_INPUT", f"File not found: {input_path}")
        return ExitCodes.MISSING_RESOURCE

    if args.template is not None and not _template_exists(args.workdir, args.template):
        _emit_missing_resource(
            args,
            "convert",
            "MISSING_TEMPLATE",
            f"Template not found: {args.template}",
        )
        return ExitCodes.MISSING_RESOURCE

    try:
        converter = TextToDocxConverter(SIBFUConfig, str(args.workdir))
        converter.convert_file(
            input_path,
            output_path,
            template=args.template,
            template_mode=args.template_mode,
            insert_after_page=args.insert_after_page,
            insert_at_bookmark=args.insert_at_bookmark,
            syntax_version=args.syntax_version,
            strict=args.strict,
            skip_generated_front_matter=args.skip_generated_front_matter,
            profile=profile,
        )
    except OSError as exc:
        _emit_write_failure(args, "convert", str(exc))
        return ExitCodes.WRITE_FAILURE

    diagnostics = [
        diagnostic
        for diagnostic in converter.diagnostics
        if diagnostic.code != DiagnosticCodes.FORMAT_RULE_NOT_SUPPORTED
    ]
    if args.validate_output:
        validator = StyleValidator(SIBFUConfig, profile=profile)
        is_valid = validator.validate_file(str(output_path))
        raw_validation_diagnostics = getattr(validator, "diagnostics", None)
        if raw_validation_diagnostics is not None:
            diagnostics.extend(raw_validation_diagnostics)
        elif not is_valid:
            diagnostics.extend(_diagnostics_from_report(validator.get_report()))

    exit_code = _exit_code_from_diagnostics(diagnostics, strict=args.strict)
    diagnostics_json = _diagnostics_to_json(diagnostics)

    duration_ms = int((time.time() - start) * 1000)
    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "convert",
                    exit_code == ExitCodes.SUCCESS,
                    inputs={"input": str(input_path), "profile": args.profile},
                    outputs={"docx": str(output_path)},
                    profile=profile.name,
                    syntaxVersion=args.syntax_version,
                    durationMs=duration_ms,
                    diagnostics=diagnostics_json,
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(f"Profile: {profile.display_name}")
        print(f"Converted: {input_path} -> {output_path}")
    return exit_code


def _cmd_convert_pptx(args) -> int:
    from sfu_converter.infrastructure.pptx_renderer import PptxRenderer

    start = time.time()
    profile = _resolve_profile_arg(args, "convert")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    parser = _resolve_parser_arg(args, "convert")
    if parser is None:
        return ExitCodes.MISSING_RESOURCE

    input_path = _resolve_path(args.workdir, args.input)
    output_path = _resolve_path(args.workdir, args.output)

    if not input_path.exists():
        _emit_missing_resource(args, "convert", "MISSING_INPUT", f"File not found: {input_path}")
        return ExitCodes.MISSING_RESOURCE

    source = input_path.read_text(encoding="utf-8")
    result = parser.parse(source, filename=str(input_path))
    document, appendix_diagnostics = assign_appendix_letters(result.document)
    diagnostics = list(result.diagnostics)
    diagnostics.extend(appendix_diagnostics)
    diagnostics.extend(unsupported_rule_diagnostics(profile, component="renderer"))
    diagnostics.extend(composition.validate(document, profile))
    diagnostics.extend(metadata_check.run(document, profile))
    diagnostics.extend(validate_document_designations(document, profile))
    diagnostics.extend(heading_checks.run(document, profile))
    diagnostics.extend(validate_graphics(document, profile))
    diagnostics.extend(validate_style(document))
    diagnostics.extend(validate_unit_consistency(document))

    try:
        diagnostics.extend(PptxRenderer().render_to_file(document, profile, str(output_path)))
    except OSError as exc:
        _emit_write_failure(args, "convert", str(exc))
        return ExitCodes.WRITE_FAILURE

    diagnostics_json = _diagnostics_to_json(diagnostics)
    exit_code = _exit_code_from_diagnostics(diagnostics, strict=args.strict)
    duration_ms = int((time.time() - start) * 1000)
    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "convert",
                    exit_code == ExitCodes.SUCCESS,
                    inputs={"input": str(input_path), "profile": args.profile},
                    outputs={"pptx": str(output_path)},
                    profile=profile.name,
                    syntaxVersion=args.syntax_version,
                    durationMs=duration_ms,
                    diagnostics=diagnostics_json,
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(f"Profile: {profile.display_name}")
        print(f"Converted: {input_path} -> {output_path}")
    return exit_code


def cmd_validate_docx(args) -> int:
    from sfu_converter.validator import StyleValidator

    profile = _resolve_profile_arg(args, "validate-docx")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    input_path = _resolve_path(args.workdir, args.input)
    if not input_path.exists():
        _emit_missing_resource(
            args,
            "validate-docx",
            "MISSING_INPUT",
            f"File not found: {input_path}",
        )
        return ExitCodes.MISSING_RESOURCE

    validator = StyleValidator(SIBFUConfig, profile=profile)
    is_valid = validator.validate_file(str(input_path))
    report = validator.get_report()
    raw_diagnostics = getattr(validator, "diagnostics", None)
    if raw_diagnostics is not None:
        diagnostics = _diagnostics_to_json(raw_diagnostics)
    else:
        diagnostics = _validation_diagnostics(report)

    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "validate-docx",
                    is_valid,
                    inputs={"input": str(input_path), "profile": profile.name},
                    profile=profile.name,
                    diagnostics=diagnostics,
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(f"Profile: {profile.display_name}")
        if is_valid:
            print(f"Validation passed: {input_path}")
        else:
            print(f"Validation failed: {input_path}")
            for err in report["error_list"]:
                print(f"  ERROR: {err}")

    return ExitCodes.SUCCESS if is_valid else ExitCodes.VALIDATION_ERROR


def cmd_parse(args) -> int:
    start = time.time()
    profile = _resolve_profile_arg(args, "parse")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    parser = _resolve_parser_arg(args, "parse")
    if parser is None:
        return ExitCodes.MISSING_RESOURCE

    input_path = _resolve_path(args.workdir, args.input)
    if not input_path.exists():
        _emit_missing_resource(
            args,
            "parse",
            "MISSING_INPUT",
            f"File not found: {input_path}",
        )
        return ExitCodes.MISSING_RESOURCE

    source = input_path.read_text(encoding="utf-8")
    result = parser.parse(source, filename=str(input_path))
    exit_code = _exit_code_from_diagnostics(result.diagnostics, strict=args.strict)
    duration_ms = int((time.time() - start) * 1000)

    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "parse",
                    exit_code == ExitCodes.SUCCESS,
                    inputs={"input": str(input_path)},
                    outputs={},
                    profile=profile.name,
                    syntaxVersion=args.syntax_version,
                    ast=_ast_to_json(result.document),
                    durationMs=duration_ms,
                    diagnostics=_diagnostics_to_json(result.diagnostics),
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(json.dumps(_ast_to_json(result.document), ensure_ascii=False, indent=2))
    return exit_code


def cmd_lint(args) -> int:
    start = time.time()
    profile = _resolve_profile_arg(args, "lint")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    parser = _resolve_parser_arg(args, "lint")
    if parser is None:
        return ExitCodes.MISSING_RESOURCE

    input_path = _resolve_path(args.workdir, args.input)
    if not input_path.exists():
        _emit_missing_resource(
            args,
            "lint",
            "MISSING_INPUT",
            f"File not found: {input_path}",
        )
        return ExitCodes.MISSING_RESOURCE

    source = input_path.read_text(encoding="utf-8")
    result = parser.parse(source, filename=str(input_path))
    document, appendix_diagnostics = assign_appendix_letters(result.document)
    diagnostics = list(result.diagnostics)
    diagnostics.extend(appendix_diagnostics)
    diagnostics.extend(unsupported_rule_diagnostics(profile, component="renderer"))
    diagnostics.extend(unsupported_rule_diagnostics(profile, component="validator"))
    diagnostics.extend(composition.validate(document, profile))
    diagnostics.extend(metadata_check.run(document, profile))
    diagnostics.extend(validate_document_designations(document, profile))
    diagnostics.extend(heading_checks.run(document, profile))
    diagnostics.extend(validate_graphics(document, profile))
    diagnostics.extend(validate_style(document))
    diagnostics.extend(validate_unit_consistency(document))
    exit_code = _exit_code_from_diagnostics(diagnostics, strict=args.strict)
    diagnostics_json = _diagnostics_to_json(diagnostics)
    duration_ms = int((time.time() - start) * 1000)

    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "lint",
                    exit_code == ExitCodes.SUCCESS,
                    inputs={"input": str(input_path), "profile": profile.name},
                    outputs={},
                    profile=profile.name,
                    syntaxVersion=args.syntax_version,
                    durationMs=duration_ms,
                    diagnostics=diagnostics_json,
                    summary=_diagnostic_summary(diagnostics),
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        _print_text_diagnostics(diagnostics)
    return exit_code


def cmd_list_profiles(args) -> int:
    profile = _resolve_profile_arg(args, "list-profiles")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    profiles = [_profile_to_json(item) for item in iter_profiles()]
    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "list-profiles",
                    True,
                    profile=profile.name,
                    profiles=profiles,
                    total=len(profiles),
                    diagnostics=[],
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        for profile_data in profiles:
            print(f"{profile_data['name']}: {profile_data['displayName']}")
    return ExitCodes.SUCCESS


def cmd_export_coverage(args) -> int:
    rows = build_rows()
    if args.format == "json":
        print(render_json(rows), end="")
    else:
        print(render_markdown(rows), end="")
    return ExitCodes.SUCCESS


def cmd_agents(args) -> int:
    from sfu_converter import agents

    return agents.run_agents(
        args.action,
        only=tuple(args.only),
        install_all=args.install_all,
        dry_run=args.dry_run,
        emit=print,
    )


def cmd_export_schema(args) -> int:
    profile = _resolve_profile_arg(args, "export-schema")
    if profile is None:
        return ExitCodes.MISSING_RESOURCE

    schema = _load_schema(args.schema)
    if args.format == "json":
        print(json.dumps(schema, ensure_ascii=False))
    elif not args.quiet:
        print(f"Schema: {args.schema} (profile: {profile.name})")
        print(json.dumps(schema, ensure_ascii=False, indent=2))
    return ExitCodes.SUCCESS


def cmd_interactive(args) -> int:
    from sfu_converter.main import main as legacy_main

    legacy_main()
    return ExitCodes.SUCCESS


def cmd_explain_syntax(args) -> int:
    spec = get_syntax_spec(args.syntax_version)
    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    "explain-syntax",
                    True,
                    syntaxVersion=spec["syntaxVersion"],
                    blocks=spec["blocks"],
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(f"Syntax version {spec['syntaxVersion']}")
        for block in spec["blocks"]:
            print(f"{block['name']}: {block['description']}")
            print(f"  Marker: {block['marker']}")
            print(f"  Example: {block['example']}")
    return ExitCodes.SUCCESS


def cmd_not_implemented(args) -> int:
    print("Not yet implemented", file=sys.stderr)
    return ExitCodes.INTERNAL_ERROR


def _resolve_profile_arg(args, command: str) -> FormattingProfile | None:
    try:
        return _resolve_profile(args.profile)
    except ProfileNotFoundError as exc:
        _emit_missing_resource(
            args,
            command,
            DiagnosticCodes.MISSING_PROFILE,
            str(exc),
        )
        return None


def _resolve_profile(name: str) -> FormattingProfile:
    try:
        return get_profile(name)
    except KeyError as exc:
        raise ProfileNotFoundError(name) from exc


def _resolve_parser_arg(args, command: str):
    try:
        return get_parser(args.syntax_version, strict=getattr(args, "strict", False))
    except ValueError:
        _emit_missing_resource(
            args,
            command,
            "UNKNOWN_SYNTAX_VERSION",
            f"Unsupported syntax version: {args.syntax_version}",
        )
        return None


def _exit_code_from_diagnostics(diagnostics: list[Diagnostic], *, strict: bool = False) -> int:
    if _has_errors(diagnostics):
        return ExitCodes.VALIDATION_ERROR
    if strict and any(diagnostic.severity is Severity.WARNING for diagnostic in diagnostics):
        return ExitCodes.WARNINGS_STRICT
    return ExitCodes.SUCCESS


def _has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(diagnostic.severity in (Severity.ERROR, Severity.FATAL) for diagnostic in diagnostics)


def _diagnostics_to_json(diagnostics: list[Diagnostic]) -> list[dict[str, object]]:
    return [diagnostic_to_json(diagnostic) for diagnostic in diagnostics]


def _diagnostics_from_report(report) -> list[Diagnostic]:
    diagnostics = []
    diagnostics.extend(
        Diagnostic("VALIDATION_ERROR", message, Severity.ERROR)
        for message in report["error_list"]
    )
    diagnostics.extend(
        Diagnostic("VALIDATION_WARNING", message, Severity.WARNING)
        for message in report["warning_list"]
    )
    return diagnostics


def _print_text_diagnostics(diagnostics: list[Diagnostic]) -> None:
    for diagnostic in diagnostics:
        print(
            f"{diagnostic.severity.value.upper()}: {diagnostic.code}: {diagnostic.message}",
            file=sys.stderr,
        )


def _profile_to_json(profile: FormattingProfile) -> dict[str, object]:
    renderer_unsupported = [
        rule.id for rule in profile.rules if rule.renderer_status is RuleStatus.NOT_SUPPORTED
    ]
    validator_unsupported = [
        rule.id for rule in profile.rules if rule.validator_status is RuleStatus.NOT_SUPPORTED
    ]
    support = _profile_support(profile)
    return {
        "name": profile.name,
        "displayName": profile.display_name,
        "sourceDocs": sorted(profile.source_docs),
        "ruleCount": len(profile.rules),
        "rendererSupport": sum(rule.renderer_status is RuleStatus.IMPLEMENTED for rule in profile.rules),
        "validatorSupport": sum(rule.validator_status is RuleStatus.IMPLEMENTED for rule in profile.rules),
        "unsupportedRendererRuleIds": sorted(renderer_unsupported),
        "unsupportedValidatorRuleIds": sorted(validator_unsupported),
        "support": support,
        "ruleSupport": _profile_rule_support(profile),
        "requiredMetadata": _required_metadata(profile),
        "titlePageForm": _title_page_form(profile),
    }


def _profile_support(profile: FormattingProfile) -> dict[str, object]:
    return {
        "parserSupport": sum(parser_support_for_rule(rule) for rule in profile.rules),
        "renderer": _status_counts(rule.renderer_status for rule in profile.rules),
        "validator": _status_counts(rule.validator_status for rule in profile.rules),
    }


def _profile_rule_support(profile: FormattingProfile) -> list[dict[str, object]]:
    return [
        {
            "ruleId": rule.id,
            "parserSupport": parser_support_for_rule(rule),
            "rendererStatus": rule.renderer_status.value,
            "validatorStatus": rule.validator_status.value,
        }
        for rule in sorted(profile.rules, key=lambda item: item.id)
    ]


def _status_counts(statuses) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status in statuses:
        counts[status.value] = counts.get(status.value, 0) + 1
    return counts


def _required_metadata(profile: FormattingProfile) -> list[str]:
    fields = set()
    for rule in profile.rules:
        if rule.id.endswith(".metadata.required") or ".metadata.required" in rule.id:
            fields.update(rule.parameters.get("required_metadata", ()))
    return sorted(fields)


def _title_page_form(profile: FormattingProfile) -> str | None:
    for rule in sorted(profile.rules, key=lambda item: item.id):
        if ".title_page." in rule.id and "form" in rule.parameters:
            return str(rule.parameters["form"])
    return None


def _ast_to_json(value):
    from sfu_converter.domain.ast_nodes import Document

    if isinstance(value, Document):
        return {
            "type": BlockType.DOCUMENT.name,
            "blocks": [_ast_to_json(block) for block in value.blocks],
            "syntax_version": value.syntax_version,
            "metadata": _ast_to_json(value.metadata),
            "source_file": value.source_file,
        }
    if isinstance(value, SourceSpan):
        return {
            "line_start": value.line_start,
            "line_end": value.line_end,
            "col_start": value.col_start,
            "col_end": value.col_end,
            "filename": value.filename,
        }
    if is_dataclass(value):
        payload = {"type": _node_type_name(value)}
        for field in fields(value):
            payload[field.name] = _ast_to_json(getattr(value, field.name))
        return payload
    if isinstance(value, Enum):
        return {"name": value.name, "value": value.value}
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _ast_to_json(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_ast_to_json(item) for item in value]
    return value


_BLOCK_TYPE_BY_NODE = {
    "Paragraph": BlockType.PARAGRAPH,
    "Heading": BlockType.HEADING,
    "Table": BlockType.TABLE,
    "Figure": BlockType.FIGURE,
    "Formula": BlockType.FORMULA,
    "List": BlockType.LIST,
    "ListItem": BlockType.LIST_ITEM,
    "PageBreak": BlockType.PAGE_BREAK,
    "StructuralSection": BlockType.STRUCTURAL_SECTION,
    "Appendix": BlockType.APPENDIX,
    "BibliographyEntry": BlockType.BIBLIOGRAPHY_ENTRY,
    "RawBlock": BlockType.RAW_BLOCK,
    "TableCaption": BlockType.TABLE_CAPTION,
    "FigureCaption": BlockType.FIGURE_CAPTION,
    "Metadata": BlockType.METADATA,
    "TableOfContents": BlockType.TABLE_OF_CONTENTS,
    "TitlePage": BlockType.TITLE_PAGE,
    "Reference": BlockType.REFERENCE,
    "DrawingSheet": BlockType.DRAWING_SHEET,
    "Poster": BlockType.POSTER,
    "SlideDeck": BlockType.SLIDE_DECK,
    "Slide": BlockType.SLIDE,
}


def _node_type_name(value) -> str:
    node_name = value.__class__.__name__.removesuffix("Node")
    block_type = _BLOCK_TYPE_BY_NODE.get(node_name)
    if block_type is not None:
        return block_type.name
    return _camel_to_snake(node_name)


def _camel_to_snake(value: str) -> str:
    chars = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def _diagnostic_summary(diagnostics: list[Diagnostic]) -> dict[str, int]:
    return {
        "errors": sum(diagnostic.severity in (Severity.ERROR, Severity.FATAL) for diagnostic in diagnostics),
        "warnings": sum(diagnostic.severity is Severity.WARNING for diagnostic in diagnostics),
        "infos": sum(diagnostic.severity is Severity.INFO for diagnostic in diagnostics),
    }


def _load_schema(name: str) -> dict[str, object]:
    path = Path(__file__).with_name("cli_schemas") / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_path(workdir: Path, path: Path) -> Path:
    return path if path.is_absolute() else workdir / path


def _template_exists(workdir: Path, template: Path) -> bool:
    if template.is_absolute():
        return template.exists()
    candidates = (
        workdir / PathConfig.TEMPLATES_DIR / template,
        workdir / template,
        template,
    )
    return any(candidate.exists() for candidate in candidates) or packaged_template_exists(template)


def _emit_missing_resource(args, command: str, code: str, message: str) -> None:
    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    command,
                    False,
                    diagnostics=[_simple_diagnostic_json(code, message)],
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(f"Error: {message}", file=sys.stderr)


def _emit_write_failure(args, command: str, message: str) -> None:
    if args.format == "json":
        print(
            json.dumps(
                make_json_result(
                    command,
                    False,
                    diagnostics=[_simple_diagnostic_json("WRITE_FAILURE", message)],
                ),
                ensure_ascii=False,
            )
        )
    elif not args.quiet:
        print(f"Error: {message}", file=sys.stderr)


def _validation_diagnostics(report):
    if "diagnostics" in report:
        return report["diagnostics"]

    diagnostics = []
    diagnostics.extend(
        {"code": "VALIDATION_ERROR", "message": message, "severity": "error"} for message in report["error_list"]
    )
    diagnostics.extend(
        {"code": "VALIDATION_WARNING", "message": message, "severity": "warning"} for message in report["warning_list"]
    )
    return diagnostics


def _simple_diagnostic_json(code: str, message: str) -> dict[str, object]:
    return {
        "code": code,
        "severity": Severity.ERROR.value,
        "message": message,
        "ruleId": None,
        "source": {
            "document": None,
            "section": None,
            "lineStart": None,
            "lineEnd": None,
        },
        "data": {},
    }


if __name__ == "__main__":
    raise SystemExit(main())
