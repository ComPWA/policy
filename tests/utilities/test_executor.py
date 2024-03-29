from textwrap import dedent

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import Executor


class TestExecutor:
    def test_error_messages(self):
        def do_without_args() -> None:
            msg = "Function did not have arguments"
            raise PrecommitError(msg)

        def do_with_positional_args(some_list: list) -> None:
            list_content = ", ".join(some_list)
            msg = f"\nList contains {list_content}"
            raise PrecommitError(msg)

        def do_with_keyword_args(text: str) -> None:
            msg = f"Text is {text}"
            raise PrecommitError(msg)

        def no_error() -> None:
            pass

        with Executor(raise_exception=False) as do:
            do(do_without_args)
            do(do_with_positional_args, ["one", "two", "three"])
            do(do_with_keyword_args, "given as positional argument")
            do(do_with_keyword_args, text="given as key-word argument")
            do(no_error)
            assert do.error_messages == (
                "Function did not have arguments",
                "\nList contains one, two, three",
                "Text is given as positional argument",
                "Text is given as key-word argument",
            )
            merged_message = do.merge_messages()

        expected_message = """
            Function did not have arguments
            --------------------
            List contains one, two, three
            --------------------
            Text is given as positional argument
            --------------------
            Text is given as key-word argument
            """
        expected_message = dedent(expected_message).strip()
        assert merged_message == expected_message
