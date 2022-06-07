from textwrap import dedent

from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor


class TestExecutor:
    def test_error_messages(self):
        def do_without_args() -> None:
            raise PrecommitError("Function did not have arguments")

        def do_with_positional_args(some_list: list) -> None:
            list_content = ", ".join(some_list)
            raise PrecommitError(f"\nList contains {list_content}")

        def do_with_keyword_args(text: str) -> None:
            raise PrecommitError(f"Text is {text}")

        def no_error() -> None:
            pass

        executor = Executor()
        executor(do_without_args)
        executor(do_with_positional_args, ["one", "two", "three"])
        executor(do_with_keyword_args, "given as positional argument")
        executor(do_with_keyword_args, text="given as key-word argument")
        executor(no_error)
        assert executor.error_messages == [
            "Function did not have arguments",
            "\nList contains one, two, three",
            "Text is given as positional argument",
            "Text is given as key-word argument",
        ]

        merged_message = executor.merge_messages()
        expected_message = dedent(
            """
            Function did not have arguments
            --------------------
            List contains one, two, three
            --------------------
            Text is given as positional argument
            --------------------
            Text is given as key-word argument
            """
        ).strip()
        assert merged_message == expected_message
