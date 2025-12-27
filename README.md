# Ollamatools 🦙

A modern CLI tool for managing Ollama models - backup, restore, update, and list your models with ease.

## Installation

### Using pip (recommended)

```bash
pip install ollamatools
```

### Using uv

```bash
uv pip install ollamatools
```

### From source

```bash
git clone https://github.com/arian24b/ollamatool.git
cd ollamatools
pip install .
```

## Requirements

- Python 3.10 or higher
- Ollama installed and running

## Usage

### Basic Commands

```bash
# Show help
ollamatools

# List all installed models
ollamatools list

# Update all models
ollamatools update

# Update a specific model
ollamatools update llama3.2

# Backup all models to default location (~/Downloads/ollama_model_backups)
ollamatools backup

# Backup to custom path
ollamatools backup --path /path/to/backup

# Backup a specific model
ollamatools backup --model llama3.2

# Restore from backup
ollamatools restore /path/to/backup.zip

# Show Ollama version
ollamatools version

# Show installation information
ollamatools info

# Check if Ollama is installed
ollamatools check
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
# Using uv
uv sync

# Using pip
pip install -e ".[dev]"
```

### Build the package

```bash
uv build
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

### ✨ Check out my other project: [Waifu2x-Extension-GUI](https://github.com/AaronFeng753/Waifu2x-Extension-GUI)

#### Photo/Video/GIF enlargement and Video frame interpolation using machine learning

#### Supports AMD / Nvidia / Intel GPU

---

#### ⭐ Make sure you already installed Python on your PC ⭐

# Export one model:

Download [Export_Model.py](https://github.com/AaronFeng753/Ollama-Model-Dumper/blob/main/Export_Model.py)

Edit `BackUp_Folder` and `Ollama_Model_Folder` at the bottom of the file:
```
#****************************************************************
#****************************************************************
#****************************************************************
# Your ollama model folder:
Ollama_Model_Folder = r"D:\llama\.ollama\models"

# Where you want to back up your models:
BackUp_Folder = r"E:\llama_backup"
#****************************************************************
#****************************************************************
#****************************************************************
model_name = input("Enter model name: ")
```

Then start Export_Model.py, enter the model name then click `Enter` key to start export the model.

It will backup gguf and modelfile into a folder:

<p align="left">
<img src="https://github.com/user-attachments/assets/70083bea-575c-4b7f-b4f1-affb950b2286" height="80">
<img src="https://github.com/user-attachments/assets/c317203a-3b87-45c6-8d7d-a2b79bd10625" height="80">
</p>


---

#### ⭐ Make sure you already installed Python on your PC ⭐

# Backup ALL your models:

Download [Backup_ALL_Models.py](https://github.com/AaronFeng753/Ollama-Model-Dumper/blob/main/Backup_ALL_Models.py)

Edit `BackUp_Folder` and `Ollama_Model_Folder` at the bottom of the file:
```
        output_file = f"ModelFile"
        #****************************************************************
        #****************************************************************
        #****************************************************************
        # Your ollama model folder:
        Ollama_Model_Folder = r"D:\llama\.ollama\models"

        # Where you want to back up your models:
        BackUp_Folder = r"E:\llama_backup"
        #****************************************************************
        #****************************************************************
        #****************************************************************
        create_ollama_model_file(model_name, output_file, BackUp_Folder, Ollama_Model_Folder)

def extract_names(data):
```

Then start Backup_ALL_Models.py, it will strating to back up all of your models

It will backup gguf and modelfile into a folder:

<p align="left">
<img src="https://github.com/user-attachments/assets/d2e5835b-bdea-4014-92b5-3c8aaca08aea" height="200">
<img src="https://github.com/user-attachments/assets/c317203a-3b87-45c6-8d7d-a2b79bd10625" height="80">
</p>

To avoid unnecessary copying, by default it will skip the model if it already exists in the backup folder

You can turn off this by delete

```
    if os.path.exists(new_folder_path) and os.path.isdir(new_folder_path):
        print(f"Model: '{model_name}' already exists in the backup folder, so it will be skipped.")
        return
```

At:

```
    new_folder_path = os.path.join(BackUp_Folder, model_name)

    #****************************************************************
    #****************************************************************
    #****************************************************************
    if os.path.exists(new_folder_path) and os.path.isdir(new_folder_path):
        print(f"Model: '{model_name}' already exists in the backup folder, so it will be skipped.")
        return
    #****************************************************************
    #****************************************************************
    #****************************************************************

    if not os.path.exists(new_folder_path):
        os.makedirs(new_folder_path)
        print(f"Created folder: {new_folder_path}")
```

---

#### ⭐ Make sure you already installed Python on your PC ⭐

# Import your backup folder into ollama:

Download [Import_Models.py](https://github.com/AaronFeng753/Ollama-Model-Dumper/blob/main/Import_Models.py)

Edit `scan_folder` at the bottom of the file:
```
#****************************************************************

# Your model backup folder:

scan_folder(r'E:\llama_backup')

#****************************************************************
```

Then start Import_Models.py, it will strating to import all of your model backups into ollama

---

#### ⭐ Make sure you already installed Python on your PC ⭐

# Update your ollama models:

Download: [Update_ALL_Models.py](https://github.com/AaronFeng753/Ollama-Model-Dumper/blob/main/Update_ALL_Models.py)

Then start Update_ALL_Models.py, it will strating to update all of your ollama models using ollama's pull command.

Only the models you downloaded from ollama.com will be updated.

---

### ✨ Check out my other project: [Waifu2x-Extension-GUI](https://github.com/AaronFeng753/Waifu2x-Extension-GUI)

#### Photo/Video/GIF enlargement and Video frame interpolation using machine learning

#### Supports AMD / Nvidia / Intel GPU

![](https://raw.githubusercontent.com/AaronFeng753/AaronFeng753/main/res/ReadMeCover.png)
