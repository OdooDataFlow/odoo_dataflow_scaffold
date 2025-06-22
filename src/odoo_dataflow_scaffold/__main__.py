"""Command-line interface."""

import click


@click.command()
@click.version_option()
def main() -> None:
    """Odoo_Dataflow_Scaffold."""


if __name__ == "__main__":
    main(prog_name="odoo_dataflow_scaffold")  # pragma: no cover
