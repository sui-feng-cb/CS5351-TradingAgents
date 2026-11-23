"""The CLI's shared rich console, kept import-light.

Importing this module pulls in only ``rich``; the heavy analysis/graph/model SDK
imports stay out of the CLI start-up path so a read-only command such as
``manifest query`` starts without loading them.
"""

from rich.console import Console

console = Console()
