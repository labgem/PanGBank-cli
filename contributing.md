# Contributing

Thank you for your interest in contributing to PanGBank-cli! This is an open-source project, and we welcome everyone to get involved.

## Help or Reporting a Bug

If you have a question or found a bug? Please open an issue.

Before you do, check the [Issues](https://github.com/labgem/PanGBank-cli/issues) page to see if it's already been reported.

If you don’t see it there, create a new [issue](https://github.com/labgem/PanGBank-cli/issues). We appreciate your input!


## Adding a new feature to PanGBank-cli

### Starting with an issue

If you have ideas for new features or improvements, initiate a discussion in an issue. This allows us to evaluate and discuss your suggestions together.

For minor changes like fixing typos or making small edits, create a new Pull Request (PR) directly with your proposed changes.

### Setting Up the Development Environment

1. **Fork and Clone the Repository:**
   - Fork the repository to your GitHub account.
   - Clone your forked repository to your local machine.

2. **Get an Environment:**
   Create an environment with all PanGBank-cli prerequisites installed by following the installation instructions.


3. **Branch from 'dev':**
   Start your changes from the `dev` branch, where updates for the upcoming release are integrated.
   ```bash
   git checkout dev
   ```

4. **Install in Editable Mode:**
   To enable code editing and testing of new functionality, you can install PanGBank-cli in editable mode:
   ```bash
   pip install -e .[dev]
   ```
   - The `[dev]` part installs additional packages required for development. While not mandatory, it is recommended for an optimal development environment. Refer to the `pyproject.toml` file for details on the additional dependencies that will be installed.

   Installing in editable mode allows you to modify the codebase and experiment with new features directly.

5. **Install the pre-commit hooks:**
   Linting, formatting and type checking run as [pre-commit](https://pre-commit.com) hooks. We use [prek](https://github.com/j178/prek), a faster drop-in replacement (`pre-commit` itself works too). Both are configured in `.pre-commit-config.yaml`:
   - [Ruff](https://docs.astral.sh/ruff/) lints and formats the code (it replaces Black and flake8).
   - [Pyright](https://github.com/microsoft/pyright) type checks it in **strict** mode, so every function needs argument and return type annotations.

   ```bash
   prek install            # run the hooks automatically on every `git commit`
   prek run --all-files    # run them by hand on the whole repository
   ```

   The pyright hook uses the active Python environment, so activate the one where you ran `pip install -e .[dev]` before committing. The same hooks run in CI on every push and pull request.

**Tips**: VS Code's Pylance reads the `[tool.pyright]` section of `pyproject.toml`, so it shows the same type errors as the hook. Install the Ruff extension and set it as the Python formatter to match `ruff format`.


### Making Your Changes

Maintain consistency in code formatting. When adding new code, closely follow the existing structure. Functions should include descriptive docstrings explaining their purpose and detailing the parameters. Every function must annotate its arguments and return type (enforced by Ruff and Pyright).

### Update Documentation

If your changes alter the tool's behavior, update the documentation to reflect them. Provide clear descriptions and, if necessary, examples of commands and their respective outputs.


### Tests

#### Continuous Integration (CI) Workflow

We've configured a CI workflow in the Actions tab, executing PanGBank-cli on a small dataset and testing its results. If you've introduced a new feature, consider updating the CI YAML file to test it and ensure seamless integration.

#### Unit Tests

It is recommended to add unit test to any additions to the code. The test suite is located in the 'tests' directory at the root of the project.

### Creating a Pull Request 🚀

Once you've made your changes:

1. **Create a Pull Request:** Submit a pull request from your forked repository to the 'dev' branch on GitHub.

2. **Describe Your Changes:** Clearly describe the modifications you've made and link any associated issue(s) in the PR description.

3. **Collaborative Review:** We will review your changes, offer feedback, and engage in discussions until we collectively agree on the implementation.
