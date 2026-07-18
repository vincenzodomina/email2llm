import os
import tempfile
import unittest
from contextlib import redirect_stdout
from email.message import EmailMessage
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import email2llm


def write_email(path: Path, subject: str = "Quarterly / Review?") -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "Sender <sender@example.com>"
    message["To"] = "Recipient <recipient@example.com>"
    message["Date"] = "Wed, 15 Jul 2026 14:59:04 +0000"
    message.set_content("Hello team.\n\n- First item\n")
    message.add_alternative(
        "<p>Hello team.</p><ul><li>First item</li></ul>", subtype="html"
    )
    path.write_bytes(message.as_bytes())


class Email2LlmTests(unittest.TestCase):
    def test_single_conversion_uses_date_and_sanitized_subject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "message.eml"
            write_email(source)

            self.assertEqual(email2llm.main([str(source)]), 0)

            output = Path(directory) / "20260715_Quarterly Review.md"
            self.assertTrue(output.is_file())
            self.assertTrue(source.is_file())
            markdown = output.read_text(encoding="utf-8")
            self.assertIn("# Quarterly / Review?", markdown)
            self.assertIn("**From:** Sender", markdown)
            self.assertIn("- First item", markdown)

    def test_delete_source_runs_only_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "message.eml"
            write_email(source)

            self.assertEqual(email2llm.main(["--delete-source", str(source)]), 0)

            self.assertFalse(source.exists())
            self.assertTrue(
                (Path(directory) / "20260715_Quarterly Review.md").is_file()
            )

    def test_batch_mode_confirms_once_and_skips_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.eml"
            second = root / "second.eml"
            write_email(first, "First")
            write_email(second, "Second")
            (root / "second.md").write_text("existing", encoding="utf-8")
            previous_directory = Path.cwd()
            try:
                os.chdir(root)
                with patch("builtins.input", return_value="yes") as confirmation:
                    with redirect_stdout(StringIO()):
                        exit_code = email2llm.main([])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 0)
            confirmation.assert_called_once()
            self.assertTrue((root / "20260715_First.md").is_file())
            self.assertFalse((root / "20260715_Second.md").exists())


if __name__ == "__main__":
    unittest.main()
