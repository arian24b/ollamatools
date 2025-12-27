# Ollama Tool CLI 🦙

A modern CLI tool for managing Ollama models - backup, restore, update, and list your models with ease.

## Installation

### Using pip (recommended)

```bash
pip install ollama-tool-cli
```

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

# Backup all models to default location (~/Downloads/ollama_model_backups)
ollama-tool-cli backup

# Backup to custom path
ollama-tool-cli backup --path /path/to/backup

# Backup a specific model
ollama-tool-cli backup --model llama3.2

# Restore from backup
ollama-tool-cli restore /path/to/backup.zip

# Show Ollama version
ollama-tool-cli version

# Show installation information
ollama-tool-cli info

# Check if Ollama is installed
ollama-tool-cli check
```

### Command Details

#### `list`
Display all installed Ollama models with their versions.

#### `update [model]`
Update one or all Ollama models. If no model name is provided, updates all models.

#### `backup [--path PATH] [--model MODEL]`
Backup Ollama models to zip files. By default backs up all models to `~/Downloads/ollama_model_backups`.

- `--path, -p`: Custom backup directory path
- `--model, -m`: Backup only a specific model

#### `restore <path>`
Restore Ollama models from a backup zip file or directory.

#### `version`
Display the installed Ollama version.

#### `info`
Show detailed Ollama installation information including version, models path, platform, and number of installed models.

#### `check`
Verify that Ollama is installed and accessible.

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

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
