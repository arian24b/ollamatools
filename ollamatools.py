from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from json import loads
from os import cpu_count, getenv
from pathlib import Path
from subprocess import PIPE, Popen
from sys import argv, platform
from time import sleep
from zipfile import ZipFile

import typer


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
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024
LOG_FILE_BACKUPS = 5


def run_command(command: str | list[str]) -> CMDOutput:
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


def default_jobs() -> int:
    return min(4, cpu_count() or 1)


def resolve_jobs(value: int | None) -> int:
    jobs = default_jobs() if value is None else value
    return max(1, jobs)


def log_dir() -> Path:
    if platform.lower() == "darwin":
        return Path("~/Library/Logs/ollama-tool-cli").expanduser()
    if platform.lower() == "linux":
        base_dir = getenv("XDG_STATE_HOME") or "~/.local/state"
        return Path(base_dir).expanduser() / "ollama-tool-cli" / "logs"
    if platform.lower() == "win32":
        base_dir = getenv("LOCALAPPDATA") or getenv("APPDATA") or "~"
        return Path(base_dir).expanduser() / "ollama-tool-cli" / "Logs"
    return Path("~/Library/Logs/ollama-tool-cli").expanduser()


def rotate_log_file(file_path: Path) -> None:
    if not file_path.exists() or file_path.stat().st_size < LOG_FILE_MAX_BYTES:
        return

    for index in range(LOG_FILE_BACKUPS, 0, -1):
        rotated_path = file_path.with_suffix(f"{file_path.suffix}.{index}")
        previous_path = file_path if index == 1 else file_path.with_suffix(f"{file_path.suffix}.{index - 1}")
        if previous_path.exists():
            if rotated_path.exists():
                rotated_path.unlink()
            previous_path.rename(rotated_path)


def background_command_args() -> list[str]:
    args = []
    for arg in argv:
        if arg in {"--background", "-b"}:
            continue
        args.append(arg)
    return args


def spawn_background() -> None:
    command = background_command_args()
    log_path = log_dir()
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "ollama-tool-cli.log"
    rotate_log_file(log_file)

    stdout_handle = open(log_file, "a", encoding="utf-8")
    stderr_handle = stdout_handle

    if platform.lower() == "win32":
        creationflags = 0x00000008 | 0x00000200
        process = Popen(
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=PIPE,
            creationflags=creationflags,
            shell=False,
            text=True,
        )
    else:
        process = Popen(
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=PIPE,
            start_new_session=True,
            shell=False,
            text=True,
        )

    typer.echo(f"Running in background. PID: {process.pid}")
    typer.echo(f"Logs: {log_file}")
    raise typer.Exit(code=0)


def follow_log(file_path: Path) -> None:
    typer.echo(f"Following logs: {file_path}")
    file_handle = None
    position = 0
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            if not file_path.exists():
                if file_handle:
                    file_handle.close()
                    file_handle = None
                    position = 0
                sleep(0.5)
                continue

            if file_handle is None:
                file_handle = open(file_path, encoding="utf-8")
                file_handle.seek(position)

            line = file_handle.readline()
            if line:
                typer.echo(line.rstrip("\n"))
                position = file_handle.tell()
                continue

            if file_path.exists() and file_handle:
                current_size = file_path.stat().st_size
                if current_size < position:
                    file_handle.close()
                    file_handle = None
                    position = 0

            sleep(0.5)
    except KeyboardInterrupt:
        return
    finally:
        if file_handle:
            file_handle.close()


def check_ollama_installed() -> bool:
    result = run_command("which ollama")
    return result.return_code == 0


def ollama_version() -> str:
    result = run_command("ollama --version")
    return result.output_text.split("is")[1].strip()


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


def update_models_parallel(model_names: list[str], jobs: int) -> list[str]:
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {executor.submit(run_command, f"ollama pull {model}"): model for model in model_names}
        for future in as_completed(future_map):
            model = future_map[future]
            result = future.result()
            if result.return_code != 0:
                failures.append(model)
    return failures


def backup_single_model(
    models_path: Path,
    backup_path: Path,
    model: str,
) -> str | None:
    model_name, model_version = model.split(":") if ":" in model else (model, "latest")
    model_schema_path = models_path / f"manifests/registry.ollama.ai/library/{model_name}/{model_version}"
    model_layers = loads(Path(model_schema_path).read_bytes())["layers"]

    digests_path = [models_path / "blobs" / layer["digest"].replace(":", "-") for layer in model_layers]
    digests_path.append(model_schema_path)

    archive_path = backup_path / f"{model_name}-{model_version}.zip"
    create_backup(digests_path, archive_path)
    return None


def backup_models(backup_path: Path = BACKUP_PATH, model: str | None = None) -> None:
    models_path = ollama_models_path()
    backup_path = Path(backup_path)
    backup_path.mkdir(parents=True, exist_ok=True)

    model_list = [model] if model else models()
    for model_name in model_list:
        backup_single_model(models_path, backup_path, model_name)


def backup_models_parallel(
    backup_path: Path,
    model_list: list[str],
    jobs: int,
) -> list[str]:
    models_path = ollama_models_path()
    backup_path = Path(backup_path)
    backup_path.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {
            executor.submit(backup_single_model, models_path, backup_path, model): model for model in model_list
        }
        for future in as_completed(future_map):
            model = future_map[future]
            try:
                future.result()
            except Exception:
                failures.append(model)
    return failures


def restore_models(backup_path: Path) -> None:
    backup_path = Path(backup_path).expanduser()
    models_path = ollama_models_path()

    with ZipFile(backup_path, "r") as zfile:
        zfile.extractall(models_path)


def restore_many(backup_paths: list[Path], jobs: int) -> list[Path]:
    failures: list[Path] = []

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {executor.submit(restore_models, path): path for path in backup_paths}
        for future in as_completed(future_map):
            path = future_map[future]
            try:
                future.result()
            except Exception:
                failures.append(path)
    return failures


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
    jobs: int | None = typer.Option(
        None,
        "--jobs",
        "-j",
        help="Number of parallel jobs",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run command in background",
    ),
) -> None:
    """Update one or all Ollama models."""
    check_installation()

    if background:
        spawn_background()

    jobs = resolve_jobs(jobs)
    all_models = models()
    models_to_update = [model] if model else all_models

    if not models_to_update:
        typer.echo("No models to update.")
        return

    typer.echo(f"Updating {len(models_to_update)} model(s)...\n")
    failures = update_models_parallel(models_to_update, jobs)
    if failures:
        typer.echo("\nUpdate completed with errors.")
        typer.echo(f"Failed: {', '.join(failures)}")
        raise typer.Exit(code=1)
    typer.echo("\nUpdate complete.")


@app.command()
def backup(
    backup_path: Path = typer.Option(
        BACKUP_PATH,
        "--path",
        "-p",
        help="Directory to save backups (default: ~/Downloads/ollama_model_backups)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to backup (backs up all if not provided)",
    ),
    jobs: int | None = typer.Option(
        None,
        "--jobs",
        "-j",
        help="Number of parallel jobs",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run command in background",
    ),
) -> None:
    """Backup Ollama models to a zip file."""
    check_installation()

    if background:
        spawn_background()

    jobs = resolve_jobs(jobs)
    backup_path = Path(backup_path).expanduser()
    typer.echo(f"Backing up models to: {backup_path}")
    model_list = [model] if model else models()
    if not model_list:
        typer.echo("No models to backup.")
        return
    failures = backup_models_parallel(backup_path, model_list, jobs)
    if failures:
        typer.echo("\nBackup completed with errors.")
        typer.echo(f"Failed: {', '.join(failures)}")
        raise typer.Exit(code=1)
    typer.echo("\nBackup complete.")


@app.command()
def restore(
    backup_path: Path = typer.Argument(
        ...,
        help="Path to backup zip file or directory",
    ),
    jobs: int | None = typer.Option(
        None,
        "--jobs",
        "-j",
        help="Number of parallel jobs",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run command in background",
    ),
) -> None:
    """Restore Ollama models from backup."""
    check_installation()

    if background:
        spawn_background()

    backup_path = Path(backup_path).expanduser()
    if not backup_path.exists():
        typer.echo(f"Error: Backup path does not exist: {backup_path}", err=True)
        raise typer.Exit(code=1)

    jobs = resolve_jobs(jobs)

    if backup_path.is_dir():
        backup_files = sorted(backup_path.glob("*.zip"))
        if not backup_files:
            typer.echo(
                f"Error: No backup zip files found in directory: {backup_path}",
                err=True,
            )
            raise typer.Exit(code=1)

        typer.echo(f"Restoring {len(backup_files)} backup(s) from: {backup_path}")
        failures = restore_many(backup_files, jobs)
        if failures:
            typer.echo("\nRestore completed with errors.")
            typer.echo(f"Failed: {', '.join(str(path) for path in failures)}")
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Restoring models from: {backup_path}")
        restore_models(backup_path)
    typer.echo("\nRestore complete.")


@app.command()
def info() -> None:
    """Show Ollama installation information."""
    check_installation()
    typer.echo(f"Ollama Version: {ollama_version()}")
    typer.echo(f"Platform: {platform}")
    typer.echo(f"Installed Models: {len(models())}")
    typer.echo(f"Models Path: {ollama_models_path()}")
    typer.echo(f"Logs: {log_dir()}")


@app.command()
def logs(
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="Follow the log output",
    ),
) -> None:
    """Show log file location or follow logs."""
    log_path = log_dir()
    log_file = log_path / "ollama-tool-cli.log"
    if follow:
        follow_log(log_file)
        return

    typer.echo(f"Log directory: {log_path}")
    typer.echo(f"Log file: {log_file}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
