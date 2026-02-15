# Ollama Tool CLI 🦙

A modern CLI tool for managing Ollama models—back up, restore, update, and list your models with ease.

## Installation

### Using uv

```bash
uv add ollama-tool-cli
```

### From source

```bash
git clone https://github.com/arian24b/ollamatools.git
cd ollamatools
uv sync
```

## Requirements

- Python 3.10 or higher
- Ollama installed and running

## Usage

### Basic Commands

```bash
# Show help
ollama-tool-cli

# List all installed models
ollama-tool-cli list

# Update all models
ollama-tool-cli update

# Update a specific model
ollama-tool-cli update llama3.2

# Backup all models to default location (~/Downloads/ollama_models_backup)
ollama-tool-cli backup

# Backup to custom path
ollama-tool-cli backup --path /path/to/backup

# Backup a specific model
ollama-tool-cli backup --model llama3.2

# Backup with parallel jobs
ollama-tool-cli backup --jobs 4

# Run backup in background
ollama-tool-cli backup --background

# Restore from backup
ollama-tool-cli restore /path/to/backup.zip

# Restore all backups in a directory
ollama-tool-cli restore /path/to/backup_dir

# Show installation information and version
ollama-tool-cli info

# Show log paths
ollama-tool-cli logs

# Follow logs
ollama-tool-cli logs --follow
```

### Command Details

#### `list`
Display all installed Ollama models with their versions.

#### `update [model]`
Update one model or all models. If no model name is provided, all installed models are updated.

- `--jobs, -j`: Number of parallel jobs
- `--background, -b`: Run command in background

#### `backup [--path PATH] [--model MODEL]`
Back up Ollama models to zip files. By default, all models are backed up to `~/Downloads/ollama_models_backup`.

- `--path, -p`: Custom backup directory path
- `--model, -m`: Backup only a specific model
- `--jobs, -j`: Number of parallel jobs
- `--background, -b`: Run command in background

#### `restore <path>`
Restore Ollama models from a backup zip file or from a directory containing backup zip files.

- `--jobs, -j`: Number of parallel jobs
- `--background, -b`: Run command in background

#### `info`
Show detailed installation information, including the Ollama version, models path, platform, and number of installed models.

#### `logs`
Show log file locations or follow logs.

- `--follow, -f`: Follow the log output

## Background logs

Background commands write to an OS-specific log directory with size-based rotation:

- macOS: `~/Library/Logs/ollama-tool-cli/`
- Linux: `${XDG_STATE_HOME:-~/.local/state}/ollama-tool-cli/logs/`
- Windows: `%LOCALAPPDATA%\ollama-tool-cli\Logs\`

## Development

### Setup development environment

```bash
uv sync
```

### Build the package

```bash
uv build
```

## License

MIT License — see the LICENSE file for details.

## Contributing

Contributions are welcome! Feel free to submit a pull request.
