from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from json import loads
from os import cpu_count, getenv
from pathlib import Path
from shutil import which
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
BACKUP_PATH = Path("~/Downloads/ollama_models_backup").expanduser()
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024
LOG_FILE_BACKUPS = 3


def run_command(command: list[str]) -> CMDOutput:
    process = Popen(
        command,
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


def resolve_jobs(value: int | None) -> int:
    jobs = min(4, cpu_count() or 1) if value is None else value
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
    return Path("./ollama-tool-cli").expanduser()


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
            text=True,
        )
    else:
        process = Popen(
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=PIPE,
            start_new_session=True,
            text=True,
        )

    typer.echo(f"Running in background. PID: {process.pid}")
    typer.echo("View logs with: ollama-tool-cli logs --follow")
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
    return which("ollama") is not None


def ollama_version() -> str:
    result = run_command(["ollama", "--version"])
    output = result.output_text.strip()
    if not output:
        return "unknown"
    if " is " in output:
        return output.split(" is ", 1)[1].strip()
    return output


def check_installation() -> None:
    if not check_ollama_installed():
        typer.echo(
            "Error: Ollama is not installed. Please install Ollama before using this tool.",
            err=True,
        )
        raise typer.Exit(code=1)


def create_backup(path_to_backup: list[Path], backup_path: Path) -> None:
    with ZipFile(backup_path, "w") as zfile:
        for file in path_to_backup:
            zfile.write(file, arcname=file.relative_to(file.anchor))


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
    result = run_command(["ollama", "list"]).output_text.strip().split("\n")
    return [line.split()[0] for line in result[1:]]


def update_models(model_names: list[str]) -> CMDOutput:
    for model_name in model_names:
        typer.echo(f"Updating model: {model_name}")
        res = run_command(["ollama", "pull", model_name])
    return res


def update_models_parallel(model_names: list[str], jobs: int) -> list[str]:
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {executor.submit(update_models, [model]): model for model in model_names}
        for future in as_completed(future_map):
            model = future_map[future]
            result = future.result()
            if result.return_code != 0:
                failures.append(model)
    return failures


def backup_single_model(models_path: Path, backup_path: Path, model: str) -> None:
    model_name, model_version = model.split(":") if ":" in model else (model, "latest")
    model_schema_path = models_path / f"manifests/registry.ollama.ai/library/{model_name}/{model_version}"
    if not model_schema_path.exists():
        msg = f"Model manifest not found for: {model}"
        raise FileNotFoundError(msg)
    model_layers = loads(Path(model_schema_path).read_bytes())["layers"]

    digests_path = [models_path / "blobs" / layer["digest"].replace(":", "-") for layer in model_layers]
    digests_path.append(model_schema_path)

    missing_files = [path for path in digests_path if not path.exists()]
    if missing_files:
        msg = f"Missing model blob(s) for {model}: {', '.join(str(path) for path in missing_files)}"
        raise FileNotFoundError(msg)

    archive_path = backup_path / f"{model_name}-{model_version}.zip"
    create_backup(digests_path, archive_path)


def backup_models(backup_path: Path = BACKUP_PATH, model: str | None = None) -> None:
    models_path = ollama_models_path()
    backup_path = Path(backup_path)
    backup_path.mkdir(parents=True, exist_ok=True)

    model_list = [model] if model else models()
    for model_name in model_list:
        backup_single_model(models_path, backup_path, model_name)


def backup_models_parallel(backup_path: Path, model_list: list[str], jobs: int) -> list[str]:
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


app = typer.Typer(
    name="ollama-tool-cli",
    no_args_is_help=True,
)


@app.command()
def list() -> None:
    """List all installed Ollama models."""
    model_list = models()

    if not model_list:
        typer.echo("No models are installed. Use `ollama pull <model>` to install one.")
        return

    typer.echo(f"\nInstalled {len(model_list)} model(s):")
    typer.echo("-" * 40)
    for model in model_list:
        typer.echo(f"  • {model}")
    typer.echo("-" * 40)


@app.command()
def update(
    model: str = typer.Argument(
        None,
        help="Model name to update (updates all models if not provided)",
    ),
    jobs: int | None = typer.Option(
        None,
        "--jobs",
        "-j",
        help="Number of parallel jobs",
    ),
    *,
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run the command in the background",
    ),
) -> None:
    """Update one or all Ollama models."""
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
        help="Directory where backups are saved (default: ~/Downloads/ollama_models_backup)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to back up (backs up all models if not provided)",
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
        help="Run the command in the background",
    ),
) -> None:
    """Back up Ollama models to zip files."""
    if background:
        spawn_background()

    jobs = resolve_jobs(jobs)
    backup_path = Path(backup_path).expanduser()
    typer.echo(f"Backing up models to: {backup_path}")
    model_list = [model] if model else models()
    if not model_list:
        typer.echo("No models to back up.")
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
        help="Path to a backup zip file or a directory of backup zip files",
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
        help="Run the command in the background",
    ),
) -> None:
    """Restore Ollama models from backups."""
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
    """Show the log file location or follow logs."""
    log_path = log_dir()
    log_file = log_path / "ollama-tool-cli.log"
    if follow:
        follow_log(log_file)
        return

    typer.echo(f"Log directory: {log_path}")
    typer.echo(f"Log file: {log_file}")


def main() -> None:
    check_installation()
    app()


def run() -> None:
    main()


if __name__ == "__main__":
    main()
