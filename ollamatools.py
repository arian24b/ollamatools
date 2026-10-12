from dataclasses import dataclass
from json import loads
from os import cpu_count, getenv
from pathlib import Path
from shutil import which
from subprocess import PIPE, Popen
from sys import argv, platform
from time import sleep
from zipfile import ZipFile

from cfui import App, Arg, Fail, run_parallel, ui
from cfui.common import BACKGROUND, JOBS


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

    ui.info(f"Running in background. PID: {process.pid}")
    ui.info("View logs with: ollama-tool-cli logs --follow")
    ui.info(f"Logs: {log_file}")
    raise SystemExit(0)


def follow_log(file_path: Path) -> None:
    ui.info(f"Following logs: {file_path}")
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
                ui.out(line.rstrip("\n"))
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
        raise Fail("Ollama is not installed.", "Install Ollama before using this tool.")


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
    return run_parallel(model_names, lambda m: update_models([m]), jobs)


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
    return run_parallel(model_list, lambda m: backup_single_model(models_path, backup_path, m), jobs)


def restore_model(backup_path: Path) -> None:
    backup_path = Path(backup_path).expanduser()
    models_path = ollama_models_path()

    with ZipFile(backup_path, "r") as zfile:
        zfile.extractall(models_path)


def restore_models(backup_paths: list[Path], jobs: int) -> list[Path]:
    return run_parallel(backup_paths, restore_model, jobs, label=lambda p: p.name)


cli = App(
    "ollama-tool-cli",
    repo="https://github.com/arian24b/ollamatools",
    description="Manage Ollama models: list, update, back up and restore.",
)


@cli.command("list", "List all installed Ollama models")
def list_models(a) -> None:
    check_installation()
    model_list = models()
    if not model_list:
        ui.warning("No models are installed. Use `ollama pull <model>` to install one.")
        return

    raw = run_command(["ollama", "list"]).output_text.strip().split("\n")
    header = raw[0]
    id_start, size_start, modified_start = header.find("ID"), header.find("SIZE"), header.find("MODIFIED")
    rows = [
        (line[:id_start].strip(), line[size_start:modified_start].strip(), line[modified_start:].strip())
        for line in raw[1:]
        if line.strip()
    ]
    ui.table(rows, ["Model", "Size", "Modified"])


@cli.command(
    "update-models",
    "Update one or all Ollama models",
    args=[Arg("model", nargs="?", help="Model name to update (updates all models if not provided)"), JOBS, BACKGROUND],
)
def update_cmd(a) -> None:
    check_installation()
    if a.background:
        spawn_background()

    jobs = resolve_jobs(a.jobs if a.jobs is not None else 1)
    models_to_update = [a.model] if a.model else models()

    if not models_to_update:
        ui.warning("No models to update.")
        return

    ui.info(f"Updating {len(models_to_update)} model(s)")
    failures = update_models_parallel(models_to_update, jobs)
    if failures:
        raise Fail(f"Failed: {', '.join(failures)}")
    ui.success("All models updated successfully.")


@cli.command(
    "backup",
    "Back up Ollama models to zip files",
    args=[
        Arg("-p", "--path", dest="backup_path", default=BACKUP_PATH, help="Directory where backups are saved"),
        Arg("-m", "--model", help="Specific model to back up (backs up all models if not provided)"),
        JOBS,
        BACKGROUND,
    ],
)
def backup(a) -> None:
    check_installation()
    if a.background:
        spawn_background()

    jobs = resolve_jobs(a.jobs)
    backup_path = Path(a.backup_path).expanduser()
    model_list = [a.model] if a.model else models()
    if not model_list:
        ui.warning("No models to back up.")
        return

    ui.info(f"Backing up {len(model_list)} model(s) to: {backup_path}")
    failures = backup_models_parallel(backup_path, model_list, jobs)
    if failures:
        raise Fail(f"Backup completed with errors. Failed: {', '.join(failures)}")
    ui.success("Backup complete.")


@cli.command(
    "restore",
    "Restore Ollama models from backups",
    args=[
        Arg(
            "backup_path",
            required=True,
            prompt="Path to a backup zip file or a directory of backup zip files",
            help="Path to a backup zip file or a directory of backup zip files",
        ),
        JOBS,
        BACKGROUND,
    ],
)
def restore(a) -> None:
    check_installation()
    if a.background:
        spawn_background()

    backup_path = Path(a.backup_path).expanduser()
    if not backup_path.exists():
        raise Fail(f"Backup path does not exist: {backup_path}")

    jobs = resolve_jobs(a.jobs)

    if backup_path.is_dir():
        backup_files = sorted(backup_path.glob("*.zip"))
        if not backup_files:
            raise Fail(f"No backup zip files found in directory: {backup_path}")

        ui.info(f"Restoring {len(backup_files)} backup(s) from: {backup_path}")
        failures = restore_models(backup_files, jobs)
        if failures:
            raise Fail(f"Restore completed with errors. Failed: {', '.join(str(p) for p in failures)}")
    else:
        ui.info(f"Restoring models from: {backup_path}")
        restore_model(backup_path)
    ui.success("Restore complete.")


@cli.command("info", "Show Ollama installation information", banner=True)
def info(a) -> None:
    check_installation()
    ui.table(
        [
            ("Ollama Version", ollama_version()),
            ("Platform", platform),
            ("Installed Models", len(models())),
            ("Models Path", ollama_models_path()),
            ("Logs", log_dir()),
        ]
    )


@cli.command(
    "logs",
    "Show the log file location or follow logs",
    args=[Arg("-f", "--follow", action="store_true", help="Follow the log output")],
)
def logs(a) -> None:
    log_file = log_dir() / "ollama-tool-cli.log"
    if a.follow:
        follow_log(log_file)
        return
    ui.out(f"Log file: {log_file}")


def main() -> None:
    cli.main()


if __name__ == "__main__":
    main()
