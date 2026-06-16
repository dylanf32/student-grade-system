"""
ANSI color codes for terminal styling.

Isolated in its own module so that:
- Colors can be disabled globally for non-ANSI terminals.
- Other modules import ``Colors.GREEN`` instead of raw escape codes.
"""

import os


class Colors:
    """ANSI escape sequences for colored console output."""

    # ── Standard Foreground Colors ───────────────────────────────────────
    HEADER    = "\033[95m"
    BLUE      = "\033[94m"
    CYAN      = "\033[96m"
    GREEN     = "\033[92m"
    YELLOW    = "\033[93m"
    RED       = "\033[91m"
    MAGENTA   = "\033[35m"
    WHITE     = "\033[97m"

    # ── Style Modifiers ──────────────────────────────────────────────────
    BOLD      = "\033[1m"
    DIM       = "\033[2m"
    ITALIC    = "\033[3m"
    UNDERLINE = "\033[4m"
    END       = "\033[0m"

    # ── Background Colors (for badge/pill effects) ───────────────────────
    BG_GREEN   = "\033[42m"
    BG_CYAN    = "\033[46m"
    BG_BLUE    = "\033[44m"
    BG_YELLOW  = "\033[43m"
    BG_RED     = "\033[41m"
    BG_MAGENTA = "\033[45m"
    BG_WHITE   = "\033[47m"
    BG_DARK    = "\033[40m"

    # ── 256-Color Foreground (for richer palettes) ───────────────────────
    INDIGO    = "\033[38;5;99m"
    TEAL      = "\033[38;5;43m"
    ORANGE    = "\033[38;5;208m"
    PINK      = "\033[38;5;213m"
    LIME      = "\033[38;5;118m"
    SKY       = "\033[38;5;117m"
    LAVENDER  = "\033[38;5;183m"
    GOLD      = "\033[38;5;220m"

    # ── 256-Color Backgrounds ────────────────────────────────────────────
    BG_INDIGO   = "\033[48;5;99m"
    BG_TEAL     = "\033[48;5;30m"
    BG_DEEP     = "\033[48;5;234m"
    BG_CHARCOAL = "\033[48;5;236m"
    BG_SLATE    = "\033[48;5;238m"

    @staticmethod
    def enable_windows_ansi() -> None:
        """Enables ANSI escape processing on Windows terminals."""
        if os.name == "nt":
            os.system("")  # triggers VT100 mode on Windows 10+

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Wraps ``text`` in the given color code.

        Args:
            text:  The string to colorize.
            color: One of the class-level color attributes.

        Returns:
            The colored string.
        """
        return f"{color}{text}{cls.END}"

    @classmethod
    def badge(cls, text: str, fg: str, bg: str) -> str:
        """Creates a colored badge/pill effect.

        Args:
            text: The badge label.
            fg:   Foreground color code.
            bg:   Background color code.

        Returns:
            A string with foreground + background color.
        """
        return f"{bg}{fg}{cls.BOLD} {text} {cls.END}"

    @classmethod
    def success(cls, text: str) -> str:
        """Returns text in green (success)."""
        return cls.colorize(text, cls.GREEN)

    @classmethod
    def error(cls, text: str) -> str:
        """Returns text in red (error)."""
        return cls.colorize(text, cls.RED)

    @classmethod
    def warning(cls, text: str) -> str:
        """Returns text in yellow (warning)."""
        return cls.colorize(text, cls.YELLOW)

    @classmethod
    def info(cls, text: str) -> str:
        """Returns text in cyan (info)."""
        return cls.colorize(text, cls.CYAN)
