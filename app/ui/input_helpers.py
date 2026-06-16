"""
Input helpers — safe, validated console input functions.

These are the ONLY functions that call ``input()``.
The rest of the app never reads stdin directly.
"""

from app.ui.colors import Colors


class InputHelper:
    """Console input utilities with built-in validation loops."""

    @staticmethod
    def get_int(prompt: str) -> int:
        """Repeatedly prompts until a valid integer is entered.

        Args:
            prompt: The message shown to the user.

        Returns:
            A valid integer.
        """
        C = Colors
        while True:
            try:
                return int(input(f"  {C.INDIGO}{C.BOLD}▸{C.END} {C.WHITE}{prompt}{C.END}"))
            except ValueError:
                print(f"  {C.BG_RED}{C.WHITE}{C.BOLD} ✘ {C.END} {C.RED}Please enter a valid number.{C.END}")

    @staticmethod
    def get_str(prompt: str) -> str:
        """Repeatedly prompts until a non-empty string is entered.

        Args:
            prompt: The message shown to the user.

        Returns:
            A non-empty stripped string.
        """
        C = Colors
        while True:
            value = input(f"  {C.INDIGO}{C.BOLD}▸{C.END} {C.WHITE}{prompt}{C.END}").strip()
            if value:
                return value
            print(f"  {C.BG_RED}{C.WHITE}{C.BOLD} ✘ {C.END} {C.RED}Input cannot be empty.{C.END}")

    @staticmethod
    def pause() -> None:
        """Waits for the user to press Enter before continuing."""
        C = Colors
        print()
        input(f"  {C.DIM}{'─' * 40}{C.END}\n  {C.SKY}Press {C.WHITE}{C.BOLD}Enter{C.END}{C.SKY} to continue...{C.END} ")
