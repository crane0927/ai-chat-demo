from types import SimpleNamespace
import unittest

from db import errors as db_errors


class ExecuteWriteErrorTestCase(unittest.TestCase):
    def test_execute_write_returns_operation_result(self) -> None:
        result = db_errors.execute_write(
            operation=lambda: 42,
            error_cls=RuntimeError,
            generic_message="写入失败",
        )

        self.assertEqual(result, 42)

    def test_execute_write_maps_unique_violation_to_specific_error(self) -> None:
        class FakeUniqueViolation(Exception):
            pass

        class DuplicateNameError(RuntimeError):
            pass

        original_psycopg = db_errors.psycopg
        db_errors.psycopg = SimpleNamespace(
            errors=SimpleNamespace(UniqueViolation=FakeUniqueViolation)
        )
        try:
            with self.assertRaises(DuplicateNameError) as context:
                db_errors.execute_write(
                    operation=lambda: (_ for _ in ()).throw(FakeUniqueViolation("dup")),
                    error_cls=RuntimeError,
                    generic_message="写入失败",
                    duplicate_error_cls=DuplicateNameError,
                    duplicate_message="名称重复",
                )
        finally:
            db_errors.psycopg = original_psycopg

        self.assertEqual(str(context.exception), "名称重复")

    def test_execute_write_wraps_generic_exception(self) -> None:
        with self.assertRaises(RuntimeError) as context:
            db_errors.execute_write(
                operation=lambda: (_ for _ in ()).throw(ValueError("bad")),
                error_cls=RuntimeError,
                generic_message="写入失败",
            )

        self.assertEqual(str(context.exception), "写入失败")


if __name__ == "__main__":
    unittest.main()
