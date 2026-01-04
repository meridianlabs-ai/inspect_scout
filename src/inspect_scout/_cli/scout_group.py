"""Custom Click group for scout CLI with default view behavior."""

from typing import Any

import click


class ScoutGroup(click.Group):
    """Custom group that launches viewer when a directory argument is given.

    This allows:
    - `scout` -> launches viewer with current directory
    - `scout ./scans` -> launches viewer with ./scans
    - `scout --port 8080 ./scans` -> launches viewer with options
    - `scout ./scans --port 8080` -> same, options after directory
    - `scout scan ...` -> runs scan subcommand
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Override parse_args to handle directory argument positioning.

        Reorders arguments so that options can appear before or after
        the directory argument when no subcommand is specified.

        Args:
            ctx: Click context.
            args: Command line arguments.

        Returns:
            Remaining arguments after parsing.
        """
        # If no args or first arg is a known subcommand, use default behavior
        if not args or args[0] in self.commands:
            return super().parse_args(ctx, args)

        # First arg is not a subcommand - need to reorder args
        # to put options before the directory argument
        dir_args: list[str] = []
        option_args: list[str] = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("-"):
                option_args.append(arg)
                i += 1
                # Check if this option takes a value (next arg doesn't start with -)
                if i < len(args) and not args[i].startswith("-"):
                    option_args.append(args[i])
                    i += 1
            else:
                dir_args.append(arg)
                i += 1

        # Reorder: options first, then directory argument
        reordered_args = option_args + dir_args
        return super().parse_args(ctx, reordered_args)

    def invoke(self, ctx: click.Context) -> Any:
        """Override invoke to handle default view behavior.

        When no subcommand is given, the directory argument (if any)
        is passed via ctx.args to the group callback.

        Args:
            ctx: Click context.

        Returns:
            Result of command invocation.
        """
        args = ctx.protected_args + ctx.args

        # If first arg is a subcommand, use default behavior
        if args and args[0] in self.commands:
            return super().invoke(ctx)

        # No subcommand - invoke the group callback with directory from args
        with ctx:
            ctx.invoked_subcommand = None
            ctx.args = args  # Pass directory as extra arg
            return ctx.invoke(self.callback or (lambda: None), **ctx.params)
