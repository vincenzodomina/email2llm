import argparse
import html
import re
import shutil
import subprocess
import sys
import unicodedata
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Sequence

__version__ = "0.1.0"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert EML messages into LLM-ready Markdown."
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Source .eml file; omit to scan the current directory",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Optional destination path; its directory and sanitized stem are used",
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete each source .eml only after conversion succeeds",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser.parse_args(argv)


def run_pandoc(source: str, input_format: str) -> str:
    result = subprocess.run(
        ["pandoc", f"--from={input_format}", "--to=gfm", "--wrap=none"],
        input=source,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def header_html(message: Message) -> str:
    subject = html.escape(str(message.get("Subject", "Untitled email")))
    fields = []
    for name in ("From", "Date", "To", "Cc"):
        value = message.get(name)
        if value:
            fields.append(f"<strong>{name}:</strong> {html.escape(str(value))}")
    return f"<h1>{subject}</h1>\n<p>{'<br>'.join(fields)}</p>"


def sanitize_filename(value: str, max_bytes: int = 180) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]+', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .-_") or "email"
    encoded = value.encode("utf-8")[:max_bytes]
    return encoded.decode("utf-8", errors="ignore").rstrip(" .-_") or "email"


def read_message(source: Path) -> Message:
    with source.open("rb") as stream:
        return BytesParser(policy=policy.default).parse(stream)


def destination_path(
    source: Path, requested_output: Path | None, message: Message
) -> Path:
    date_header = message.get("Date")
    try:
        sent_date = parsedate_to_datetime(str(date_header)) if date_header else None
    except (TypeError, ValueError):
        sent_date = None
    if sent_date is None:
        raise ValueError("email has no valid sent date")

    if requested_output:
        directory = requested_output.parent
        name = requested_output.stem
    else:
        directory = source.parent
        name = str(message.get("Subject", "Untitled email"))

    return directory / f"{sent_date:%Y%m%d}_{sanitize_filename(name)}.md"


def render_markdown(message: Message) -> str:
    body = message.get_body(preferencelist=("html", "plain"))
    if body is None:
        raise ValueError("email has no HTML or plain-text body")

    body_format = (
        "html-native_spans-native_divs"
        if body.get_content_type() == "text/html"
        else "markdown"
    )
    header = run_pandoc(header_html(message), "html")
    content = run_pandoc(body.get_content(), body_format)
    return f"{header}\n\n{content}\n"


def write_new_file(destination: Path, content: str) -> None:
    created = False
    try:
        with destination.open("x", encoding="utf-8") as stream:
            created = True
            stream.write(content)
    except OSError:
        if created:
            destination.unlink(missing_ok=True)
        raise


def convert_email(
    source: Path, requested_output: Path | None, delete_source: bool
) -> bool:
    if not source.is_file():
        print(f"error: input file not found: {source}", file=sys.stderr)
        return False

    try:
        message = read_message(source)
        destination = destination_path(source, requested_output, message)
        if not destination.parent.is_dir():
            raise ValueError(f"output directory not found: {destination.parent}")
        markdown = render_markdown(message)
        write_new_file(destination, markdown)
    except FileExistsError:
        print(f"error: output file already exists: {destination}", file=sys.stderr)
        return False
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f"error: {source}: {detail}", file=sys.stderr)
        return False

    if delete_source:
        try:
            source.unlink()
        except OSError as error:
            print(
                f"error: created {destination}, but could not delete {source}: {error}",
                file=sys.stderr,
            )
            return False

    print(destination)
    return True


def matching_markdown_exists(source: Path) -> bool:
    if source.with_suffix(".md").is_file():
        return True
    try:
        expected = destination_path(source, None, read_message(source))
    except (OSError, ValueError):
        return False
    return expected.is_file()


def batch_sources(directory: Path) -> list[Path]:
    sources = sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.casefold() == ".eml"
        ),
        key=lambda path: path.name.casefold(),
    )
    return [source for source in sources if not matching_markdown_exists(source)]


def confirm_batch(sources: Sequence[Path]) -> bool:
    print("EML files to convert:")
    for source in sources:
        print(f"  {source.name}")
    try:
        response = input("Proceed? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False
    return response.strip().casefold() in {"y", "yes"}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if shutil.which("pandoc") is None:
        print(
            "error: pandoc is required; install it with 'brew install pandoc'",
            file=sys.stderr,
        )
        return 1

    if args.input:
        return int(not convert_email(args.input, args.output, args.delete_source))

    sources = batch_sources(Path.cwd())
    if not sources:
        print("No unconverted .eml files found in the current directory.")
        return 0
    if not confirm_batch(sources):
        print("No files converted.")
        return 0

    failures = [
        source
        for source in sources
        if not convert_email(source, None, args.delete_source)
    ]
    if failures:
        print(f"error: {len(failures)} conversion(s) failed", file=sys.stderr)
        return 1
    return 0


def cli() -> None:
    raise SystemExit(main())
