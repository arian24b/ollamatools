from dataclasses import dataclass
from json import loads
from pathlib import Path
from subprocess import PIPE, Popen
from sys import platform
from zipfile import ZipFile


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
        print(f"Updating model: {model_name}")
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


def main() -> None:
    if not check_ollama_installed():
        print("Ollama is not installed. Please install Ollama to proceed.")
        return
    print(f"Ollama Version: {ollama_version()}")
    print(f"Models Path: {ollama_models_path()}")
    print(models())
    # update_models(models())
    backup_models()


if __name__ == "__main__":
    main()
