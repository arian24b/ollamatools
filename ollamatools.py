from dataclasses import dataclass
from json import loads
from pathlib import Path
from subprocess import PIPE, Popen
from sys import platform
from zipfile import ZipFile

import typer

# Test commit for patch release


@dataclass
class CMDOutput:
    output_text: str
    error_text: str
    return_code: int

    def __str__(self) -> str:
        return f"Output Text: {self.output_text}\nError Text: {self.error_text}\nReturn Code: {self.return_code}"


MODELS_PATH = {
    "linux": Path("/usr/share/ollama/.ollama/models").expanduser(),
    "macos": Path("~/.ollama/models").expanduser(),
    "windows": Path("C:\\Users\\%USERNAME%\\.ollama\\models").expanduser(),
}
BACKUP_PATH = Path("~/Downloads/ollama_model_backups").expanduser()


def run_command(command: str | list) -> CMDOutput:
    process = Popen(
        command,
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
        stdin=PIPE,
        text=True,
        encoding="utf-8",
    )

    output_text, error_text = process.communicate()

    return CMDOutput(
        output_text=output_text.strip(),
        error_text=error_text.strip(),
        return_code=process.returncode,
    )


def check_ollama_installed() -> bool:
    result = run_command("which ollama")
    return result.return_code == 0


def ollama_version() -> str:
    result = run_command("ollama --version")
    return result.output_text.strip()


def create_backup(path_to_backup: list[Path], backup_path: Path) -> None:
    with ZipFile(backup_path, "w") as zfile:
        for file in path_to_backup:
            zfile.write(file)


def ollama_models_path() -> Path:
    match platform.lower():
        case "linux":
            return MODELS_PATH["linux"]
        case "darwin":
            return MODELS_PATH["macos"]
        case "win32":
            return MODELS_PATH["windows"]
        case _:
            msg = "Unsupported operating system"
            raise OSError(msg)


def models() -> list[str]:
    result = run_command("ollama list").output_text.strip().split("\n")
    return [line.split()[0] for line in result[1:]]


def update_models(model_names: list[str]) -> None:
    for model_name in model_names:
        run_command(f"ollama pull {model_name}")


def backup_models(backup_path: Path = BACKUP_PATH, model: str | None = None) -> None:
    models_path = ollama_models_path()
    backup_path = Path(backup_path)
    backup_path.mkdir(parents=True, exist_ok=True)

    for model in models():
        model_name, model_version = (
            model.split(":") if ":" in model else (model, "latest")
        )
        model_schema_path = (
            models_path
            / f"manifests/registry.ollama.ai/library/{model_name}/{model_version}"
        )
        model_layers = loads(Path(model_schema_path).read_bytes())["layers"]

        digests_path = [
            models_path / "blobs" / layer["digest"].replace(":", "-")
            for layer in model_layers
        ]
        digests_path.append(model_schema_path)

        archive_path = backup_path / f"{model_name}-{model_version}.zip"
        create_backup(digests_path, archive_path)


def restore_models(backup_path: Path) -> None:
    backup_path = Path(backup_path).expanduser()
    models_path = ollama_models_path()

    with ZipFile(backup_path, "r") as zfile:
        zfile.extractall(models_path)


app = typer.Typer(no_args_is_help=True)


def check_installation() -> None:
    if not check_ollama_installed():
        typer.echo(
            "Error: Ollama is not installed. Please install Ollama to proceed.",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def list() -> None:
    """List all installed Ollama models."""
    check_installation()
    model_list = models()

    if not model_list:
        typer.echo("No models installed.")
        return

    typer.echo("\nInstalled Models:")
    typer.echo("-" * 40)
    for model in model_list:
        typer.echo(f"  • {model}")
    typer.echo("-" * 40)
    typer.echo(f"\nTotal: {len(model_list)} model(s)")


@app.command()
def update(
    model: str = typer.Argument(
        None,
        help="Model name to update (updates all if not provided)",
    ),
) -> None:
    """Update one or all Ollama models."""
    check_installation()

    all_models = models()
    models_to_update = [model] if model else all_models

    if not models_to_update:
        typer.echo("No models to update.")
        return

    typer.echo(f"Updating {len(models_to_update)} model(s)...\n")
    update_models(models_to_update)
    typer.echo("\nUpdate complete.")


@app.command()
def backup(
    backup_path: Path = typer.Option(
        BACKUP_PATH,
        "--path",
        "-p",
        help="Directory to save backups (default: ~/Downloads/ollama_model_backups)",
    ),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to backup (backs up all if not provided)",
    ),
) -> None:
    """Backup Ollama models to a zip file."""
    check_installation()

    backup_path = Path(backup_path).expanduser()
    typer.echo(f"Backing up models to: {backup_path}")
    backup_models(backup_path, model)
    typer.echo("\nBackup complete.")


@app.command()
def restore(
    backup_path: Path = typer.Argument(
        ...,
        help="Path to backup zip file or directory",
    ),
) -> None:
    """Restore Ollama models from backup."""
    check_installation()

    backup_path = Path(backup_path).expanduser()
    if not backup_path.exists():
        typer.echo(f"Error: Backup path does not exist: {backup_path}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Restoring models from: {backup_path}")
    restore_models(backup_path)
    typer.echo("\nRestore complete.")


@app.command()
def version() -> None:
    """Show Ollama version."""
    check_installation()
    typer.echo(f"Ollama Version: {ollama_version()}")


@app.command()
def info() -> None:
    """Show Ollama installation information."""
    check_installation()
    typer.echo(f"Ollama Version: {ollama_version()}")
    typer.echo(f"Models Path: {ollama_models_path()}")
    typer.echo(f"Platform: {platform}")
    typer.echo(f"Installed Models: {len(models())}")


@app.command()
def check() -> None:
    """Check if Ollama is installed and accessible."""
    if check_ollama_installed():
        typer.echo("✓ Ollama is installed and accessible")
        typer.echo(f"  Version: {ollama_version()}")
        typer.echo(f"  Models: {len(models())}")
    else:
        typer.echo("✗ Ollama is not installed or not accessible", err=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
