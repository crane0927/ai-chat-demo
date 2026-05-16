import unittest

from repositories.session_repo import build_default_session_title


class SessionRepositoryTestCase(unittest.TestCase):
    def test_build_default_session_title_skips_existing_numbers(self) -> None:
        title = build_default_session_title(["会话 1", "会话 2", "会话 4"])

        self.assertEqual(title, "会话 3")

    def test_build_default_session_title_ignores_whitespace(self) -> None:
        title = build_default_session_title([" 会话 1 ", "会话 2"])

        self.assertEqual(title, "会话 3")


if __name__ == "__main__":
    unittest.main()
