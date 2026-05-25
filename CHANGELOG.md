# CHANGELOG

<!-- version list -->

## v1.3.1 (2026-05-25)

### Bug Fixes

- Suppress subprocess linting warnings
  ([`d864f1d`](https://github.com/arian24b/ollamatools/commit/d864f1d21fd4f401275f2bca6faa6b7841d64fd7))

- Use full package name for semantic-release in CI
  ([`ef78dac`](https://github.com/arian24b/ollamatools/commit/ef78dac0c5854e0a24030bcd34ef85896d6067f5))

- Use uvx for ruff and semantic-release in CI workflows
  ([`efb3c52`](https://github.com/arian24b/ollamatools/commit/efb3c5203778615e04d66f043e448f486613db9c))

### Chores

- Update dependencies
  ([`13bff24`](https://github.com/arian24b/ollamatools/commit/13bff240e952f90251f312f17a01c1222fefac0d))

### Refactoring

- Improve CLI user experience with rich formatting
  ([`5ada69e`](https://github.com/arian24b/ollamatools/commit/5ada69e6d5b43386a24f54f6a12da46ee2f76708))


## v1.3.0 (2026-02-17)

### Bug Fixes

- Correct backup path in README and code to use consistent naming
  ([`5e379de`](https://github.com/arian24b/ollamatools/commit/5e379de0ceb8fc1e2f9a4b960bd9a8ee2b4c8eaf))

- Handle empty model names in update_models function
  ([`ff13440`](https://github.com/arian24b/ollamatools/commit/ff13440a91c9dd4ce722b4eb19f519d9e41572aa))

- Improve language consistency and clarity in README
  ([`1fa741b`](https://github.com/arian24b/ollamatools/commit/1fa741b92d53f3956740f4e49f4175e03895c23d))

- Update actions/checkout to version 6 in release workflow
  ([`1a4d4c8`](https://github.com/arian24b/ollamatools/commit/1a4d4c80deb74e6d8d9a798f70a60dc89265b698))

- Update classifier
  ([`d3b83bb`](https://github.com/arian24b/ollamatools/commit/d3b83bbd68528e6e4125c0fde90e38c162efdd48))

- Update create_backup function to include base_path for correct file archiving
  ([`282e90f`](https://github.com/arian24b/ollamatools/commit/282e90f6907b1bd1049d06f701432d60525f1381))

### Chores

- Remove Python version file
  ([`9f1ad53`](https://github.com/arian24b/ollamatools/commit/9f1ad534c3c88b8dbe3c856a3d8185c942e9d8cf))

- Reorder dependencies and update script entry point in pyproject.toml
  ([`dfd1309`](https://github.com/arian24b/ollamatools/commit/dfd1309258b6acbab0fa0eb76d50d96cff8812d8))

- Update typer dependency version and adjust project metadata
  ([`fa9d304`](https://github.com/arian24b/ollamatools/commit/fa9d304a8d98c5080154f40cadb6f6716533449c))

### Features

- Add dependabot configuration for GitHub Actions and UV package updates
  ([`5ade13d`](https://github.com/arian24b/ollamatools/commit/5ade13d253a2a567a95c646fc5eb77fdd4a28290))

### Refactoring

- Streamline command execution and improve backup functionality
  ([`901a6fb`](https://github.com/arian24b/ollamatools/commit/901a6fb85e832f2b0286459edbfd82468f8ee2d7))


## v1.2.0 (2026-02-11)

### Features

- Add parallel jobs, background jobs, restore from dir, remove check and version command.
  ([`795181a`](https://github.com/arian24b/ollamatools/commit/795181ab13c1c62b4e62e6d3e63019b9ce3a4fca))


## v1.1.2 (2026-02-11)

### Bug Fixes

- Simplify imports and improve code readability
  ([`075b94d`](https://github.com/arian24b/ollamatools/commit/075b94db3c710b4480f149d3ac91c1376f210e0c))


## v1.1.1 (2025-12-27)

### Bug Fixes

- Update Git configuration to use GitHub actor and modify URLs in pyproject.toml
  ([`ebc97c2`](https://github.com/arian24b/ollamatools/commit/ebc97c2d46ad90ea1e5f2eec3da25682a60d25f6))


## v1.1.0 (2025-12-27)

### Bug Fixes

- Change build command to uv build for semantic-release compatibility
  ([`0ec8798`](https://github.com/arian24b/ollamatools/commit/0ec87980bd70119ec2a775d9427f15fc4a19832f))

### Chores

- Update version to 1.0.1 and modify build settings
  ([`e55f3ff`](https://github.com/arian24b/ollamatools/commit/e55f3ffdd2303d8b8c55b6086b1e78fb380e9964))

### Features

- Rename package to ollama-tool-cli and CLI command to ollama-tool-cli
  ([`aa2843f`](https://github.com/arian24b/ollamatools/commit/aa2843fd341753263cd5600051b3108d00dceed7))


## v1.0.0 (2025-12-27)

- Initial Release
