# ollama-tool-cli

[فارسی](README.fa.md)

List, update, back up and restore your [Ollama](https://ollama.com) models from the command line. Backups are plain zip files you can copy to another machine.

## How it works

The tool shells out to the `ollama` binary for `list` and `pull`. Backups do not use Ollama at all: for each model it reads the manifest under the Ollama models directory (`manifests/registry.ollama.ai/library/<name>/<tag>`), collects the blobs listed in its `layers`, and writes the manifest and blobs into one zip named `<model>-<tag>.zip`. Restore extracts the zip into the models directory. The models directory is fixed per platform: `/usr/share/ollama/.ollama/models` on Linux, `~/.ollama/models` on macOS. Run the tool as a user that can read and write that path.

## Install

Needs Python 3.12 to 3.15 and Ollama on your `PATH`.

```bash
uv tool install ollama-tool-cli      # or: pipx install ollama-tool-cli
ollama-tool-cli --help
```

From a clone: `uv sync && uv run ollama-tool-cli --help`.

## Commands

| Command | What it does |
|---|---|
| `list` | table of installed models with size and modified time |
| `update-models [MODEL] [-j N] [-b]` | pull the newest version of one model, or of all of them |
| `backup [-p DIR] [-m MODEL] [-j N] [-b]` | write each model to a zip (default `~/Downloads/ollama_models_backup`) |
| `restore PATH [-j N] [-b]` | restore from one zip, or from every zip in a directory |
| `info` | Ollama version, platform, number of models, models path, log path |
| `logs [-f]` | print the log file path, or follow it |

`-j/--jobs` sets the number of parallel jobs and `-b/--background` runs the command detached and writes to the log. `restore` asks for the path if you leave it out.

> `update-models` used to be `update`. `update` now updates the tool itself (see below).

## Examples

```bash
ollama-tool-cli list
ollama-tool-cli update-models                    # every model
ollama-tool-cli update-models llama3.2 -j 2
ollama-tool-cli backup --path /mnt/backup --model llama3.2
ollama-tool-cli backup --jobs 4 --background
ollama-tool-cli restore /mnt/backup              # a directory of zips
ollama-tool-cli logs --follow
```

Each model prints one status line when it finishes. The command exits non-zero if any model failed.

If Ollama is not on your `PATH`, every model command stops with `Ollama is not installed.` and exit code 1.

## Background logs

Background commands write to a log file that rotates by size:

- macOS: `~/Library/Logs/ollama-tool-cli/`
- Linux: `${XDG_STATE_HOME:-~/.local/state}/ollama-tool-cli/logs/`
- Windows: `%LOCALAPPDATA%\ollama-tool-cli\Logs\`

## Common commands

Built on [cfuicli](https://github.com/arian24b/cfui), so it looks and behaves like the other tools in this family.

```bash
ollama-tool-cli help [command]     # help; -h works on any command
ollama-tool-cli version            # version and git repository (also: -v)
ollama-tool-cli update [--check]   # update the tool itself; --check only compares versions
ollama-tool-cli -q ...             # quiet: no banner or notes (or OLLAMA_TOOL_CLI_QUIET=1)
```

- A missing required option is asked for when you run the tool in a terminal. In a pipe or in CI it stops with `--flag is required. Pass --flag <value> or run interactively.` (exit code 2).
- Errors appear in a red box on stderr with a non-zero exit code. Ctrl-C exits with 130.
- Color is used only on a terminal. `NO_COLOR=1` turns it off.

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv build
```

Related tools: [LinkCovery](https://github.com/arian24b/linkcovery), [PEM](https://github.com/arian24b/pem), [ThroneTools](https://github.com/arian24b/thronetools).

## License

MIT
