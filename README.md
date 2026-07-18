# email2llm

Convert exported `.eml` messages into clean, LLM-ready Markdown. The output includes the subject, sender, sent date, recipients, and the original HTML or plain-text message body. Attachments remain separate.

## Requirements

- Python 3.10+
- Pandoc

## Install

```bash
./install.sh
```

The installer creates an isolated environment at `~/.email2llm/.venv` and links the `email2llm` command into `~/.local/bin`.

If the command is not found afterward, add this to your shell configuration:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

Convert one message:

```bash
email2llm message.eml
```

The output is written beside the source as:

```text
YYYYMMDD_Sanitized email subject.md
```

Choose another output directory or base name:

```bash
email2llm message.eml ./notes/custom-name.md
```

Delete the EML only after conversion succeeds:

```bash
email2llm --delete-source message.eml
```

Run without an input path to list and convert all unconverted EML files in the current directory after one confirmation:

```bash
email2llm
email2llm --delete-source
```

Batch mode skips an EML when either a same-stem Markdown file or its generated output already exists. Existing Markdown files are never overwritten.

## Development

```bash
python3 -m unittest discover -s tests -v
```
