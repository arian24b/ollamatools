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
import typer.core
from rich import box
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

BANNER = r"""
██████╗ ██╗     ██╗      █████╗ ███╗   ███╗ █████╗
██╔═══██╗██║     ██║     ██╔══██╗████╗ ████║██╔══██╗
██║   ██║██║     ██║     ███████║██╔████╔██║███████║
██║   ██║██║     ██║     ██╔══██║██║╚██╔╝██║██╔══██║
╚██████╔╝███████╗███████╗██║  ██║██║ ╚═╝ ██║██║  ██║
╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝
   ████████╗ ██████╗  ██████╗ ██╗     ███████╗
   ╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔════╝
      ██║   ██║   ██║██║   ██║██║     ███████╗
      ██║   ██║   ██║██║   ██║██║     ╚════██║
      ██║   ╚██████╔╝╚██████╔╝███████╗███████║
      ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚══════╝
"""

VERSION = "1.0.0"


def show_banner() -> None:
    """Display the OllamaTools banner."""
    console.print(BANNER, style="cyan")
    console.print(f"[bold]OllamaTools[/bold] v{VERSION}")
    console.print("[dim]Ollama management CLI[/dim]\n")


class StyledGroup(typer.core.TyperGroup):
    def format_help(self, ctx: typer.Context, formatter: object) -> None:
        show_styled_help(ctx)


def show_styled_help(ctx: typer.Context) -> None:
    show_banner()

    group = ctx.parent.command if ctx.parent is not None else ctx.command
    cmd_path = ctx.parent.command_path if ctx.parent is not None else ctx.command_path

    console.print("[bold]Usage:[/bold]")
    console.print(f"  {cmd_path} [OPTIONS] COMMAND [ARGS]...\n")

    commands = group.commands
    if commands:
        console.print("[bold]Commands:[/bold]")
        table = Table(show_header=False, box=box.SIMPLE, padding=0)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description")
        for name, cmd in sorted(commands.items()):
            if cmd.hidden:
                continue
            short_help = cmd.get_short_help_str(limit=60)
            table.add_row(f"  {name}", short_help)
        console.print(table)
        console.print()

    console.print("[bold]Options:[/bold]")
    table = Table(show_header=False, box=box.SIMPLE, padding=0)
    table.add_column("Option", style="cyan", no_wrap=True)
    table.add_column("Description")
    for param in group.params:
        if param.name in ("help", "install_completion", "show_completion"):
            continue
        opts = ", ".join(param.opts)
        help_text = param.help or ""
        table.add_row(f"  {opts}", help_text)
    table.add_row("  -h/--help", "Show this message and exit")
    console.print(table)


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
    process = Popen(  # noqa: S603
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

    with open(log_file, "a", encoding="utf-8") as std_handle:
        if platform.lower() == "win32":
            creationflags = 0x00000008 | 0x00000200
            process = Popen(  # noqa: S603
                command,
                stdout=std_handle,
                stderr=std_handle,
                stdin=PIPE,
                creationflags=creationflags,
                text=True,
            )
        else:
            process = Popen(  # noqa: S603
                command,
                stdout=std_handle,
                stderr=std_handle,
                stdin=PIPE,
                start_new_session=True,
                text=True,
            )

    console.print(f"[dim]Running in background. PID:[/dim] {process.pid}")
    console.print("[dim]View logs with:[/dim] [bold]ollama-tool-cli logs --follow[/bold]")
    console.print(f"[dim]Logs:[/dim] {log_file}")
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


def create_backup(path_to_backup: list[Path], backup_path: Path, base_path: Path) -> None:
    with ZipFile(backup_path, "w") as zfile:
        for file in path_to_backup:
            zfile.write(file, arcname=file.relative_to(base_path))


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
    last_result = CMDOutput(output_text="", error_text="No models to update", return_code=0)
    if not model_names:
        return last_result

    for model_name in model_names:
        last_result = run_command(["ollama", "pull", model_name])

    return last_result


def update_models_parallel(model_names: list[str], jobs: int) -> list[str]:
    failures: list[str] = []

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_ids = {m: progress.add_task(f"  {m}", total=1) for m in model_names}

        with ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {executor.submit(update_models, [m]): m for m in model_names}
            for future in as_completed(futures):
                model_name = futures[future]
                result = future.result()
                if result.return_code == 0:
                    progress.update(task_ids[model_name], description=f"[green]✓ {model_name}", completed=1)
                else:
                    progress.update(
                        task_ids[model_name],
                        description=f"[red]✗ {model_name}",
                        completed=1,
                    )
                    failures.append(model_name)

    return failures


def backup_single_model(models_path: Path, backup_path: Path, model: str) -> None:
    model_full, model_version = model.split(":") if ":" in model else (model, "latest")

    if "/" in model_full:
        *registry_parts, model_short = model_full.split("/")
        registry_path = "/".join(registry_parts)
        manifest_base = models_path / "manifests" / registry_path / model_short
    else:
        model_short = model_full
        manifest_base = models_path / "manifests" / "registry.ollama.ai" / "library" / model_short

    model_schema_path = manifest_base / model_version
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

    archive_name = model_full.replace("/", "-")
    archive_path = backup_path / f"{archive_name}-{model_version}.zip"
    create_backup(digests_path, archive_path, models_path)


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

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_ids = {m: progress.add_task(f"  {m}", total=1) for m in model_list}

        with ThreadPoolExecutor(max_workers=jobs) as executor:
            future_map = {
                executor.submit(backup_single_model, models_path, backup_path, model): model for model in model_list
            }
            for future in as_completed(future_map):
                model = future_map[future]
                try:
                    future.result()
                    progress.update(task_ids[model], description=f"[green]✓ {model}", completed=1)
                except Exception:
                    progress.update(task_ids[model], description=f"[red]✗ {model}", completed=1)
                    failures.append(model)
    return failures


def restore_model(backup_path: Path) -> None:
    backup_path = Path(backup_path).expanduser()
    models_path = ollama_models_path()

    with ZipFile(backup_path, "r") as zfile:
        zfile.extractall(models_path)


def restore_models(backup_paths: list[Path], jobs: int) -> list[Path]:
    failures: list[Path] = []

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_ids = {p.name: progress.add_task(f"  {p.name}", total=1) for p in backup_paths}

        with ThreadPoolExecutor(max_workers=jobs) as executor:
            future_map = {executor.submit(restore_model, path): path for path in backup_paths}
            for future in as_completed(future_map):
                path = future_map[future]
                try:
                    future.result()
                    progress.update(task_ids[path.name], description=f"[green]✓ {path.name}", completed=1)
                except Exception:
                    progress.update(task_ids[path.name], description=f"[red]✗ {path.name}", completed=1)
                    failures.append(path)
    return failures


app = typer.Typer(
    name="ollama-tool-cli",
    cls=StyledGroup,
    context_settings={"help_option_names": ["--help", "-h"]},
)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        show_styled_help(ctx)
        raise typer.Exit()
    if ctx.invoked_subcommand == "info":
        show_banner()
    check_installation()


@app.command(name="list")
def list_models() -> None:
    """List all installed Ollama models."""
    model_list = models()

    if not model_list:
        console.print("[yellow]No models are installed.[/yellow] Use [bold]ollama pull <model>[/bold] to install one.")
        return

    raw = run_command(["ollama", "list"]).output_text.strip().split("\n")

    table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
    table.add_column("Model")
    table.add_column("Size", justify="right")
    table.add_column("Modified")

    header = raw[0]
    id_start = header.find("ID")
    size_start = header.find("SIZE")
    modified_start = header.find("MODIFIED")

    for line in raw[1:]:
        if not line.strip():
            continue
        name = line[:id_start].strip()
        size = line[size_start:modified_start].strip()
        modified = line[modified_start:].strip()
        table.add_row(name, size, modified)

    console.print(f"[bold]Installed {len(model_list)} model(s)[/bold]")
    console.print(table)


@app.command(name="help", hidden=True)
def show_help(ctx: typer.Context) -> None:
    """Show this help message and exit."""
    show_styled_help(ctx)


@app.command()
def update(
    model: str = typer.Argument(
        None,
        help="Model name to update (updates all models if not provided)",
    ),
    jobs: int | None = typer.Option(
        1,
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
        console.print("[yellow]No models to update.[/yellow]")
        return

    console.print(f"Updating {len(models_to_update)} model(s)\n")
    failures = update_models_parallel(models_to_update, jobs)
    if failures:
        console.print(f"\n[red]Failed: {', '.join(failures)}[/red]")
        raise typer.Exit(code=1)
    console.print("\n[green]All models updated successfully.[/green]")


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
    model_list = [model] if model else models()
    if not model_list:
        console.print("[yellow]No models to back up.[/yellow]")
        return

    console.print(f"Backing up [bold]{len(model_list)}[/bold] model(s) to: [dim]{backup_path}[/dim]\n")
    failures = backup_models_parallel(backup_path, model_list, jobs)
    if failures:
        console.print("\n[red]Backup completed with errors.[/red]")
        console.print(f"[red]Failed: {', '.join(failures)}[/red]")
        raise typer.Exit(code=1)
    console.print("\n[green]Backup complete.[/green]")


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
        console.print(f"[red]Error:[/red] Backup path does not exist: {backup_path}")
        raise typer.Exit(code=1)

    jobs = resolve_jobs(jobs)

    if backup_path.is_dir():
        backup_files = sorted(backup_path.glob("*.zip"))
        if not backup_files:
            console.print(f"[red]Error:[/red] No backup zip files found in directory: {backup_path}")
            raise typer.Exit(code=1)

        console.print(f"Restoring [bold]{len(backup_files)}[/bold] backup(s) from: [dim]{backup_path}[/dim]\n")
        failures = restore_models(backup_files, jobs)
        if failures:
            console.print("\n[red]Restore completed with errors.[/red]")
            console.print(f"[red]Failed: {', '.join(str(p) for p in failures)}[/red]")
            raise typer.Exit(code=1)
    else:
        console.print(f"Restoring models from: [dim]{backup_path}[/dim]")
        restore_model(backup_path)
    console.print("\n[green]Restore complete.[/green]")


@app.command()
def info() -> None:
    """Show Ollama installation information."""
    console.print(f"[bold]Ollama Version:[/bold] {ollama_version()}")
    console.print(f"[bold]Platform:[/bold] {platform}")
    console.print(f"[bold]Installed Models:[/bold] {len(models())}")
    console.print(f"[bold]Models Path:[/bold] {ollama_models_path()}")
    console.print(f"[bold]Logs:[/bold] {log_dir()}")


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

    console.print(f"[bold]Log file:[/bold] {log_file}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
