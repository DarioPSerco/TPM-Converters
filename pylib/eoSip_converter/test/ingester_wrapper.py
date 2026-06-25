import shutil
import os
import subprocess
import sys
from pathlib import Path


def backup_filename(config_file: Path) -> Path:
    return config_file.parent / (config_file.name + ".bak")


def modify_config(config_file: Path):
    # Make a backup of the original config
    shutil.copy(config_file, backup_filename(config_file))

    # Modify the config file here
    with open(config_file, "r") as file:
        config = file.readlines()

    # Example modification: change a specific line
    with open(config_file, "w") as file:
        for line in config:
            if "parameter_to_change" in line:
                file.write("parameter_to_change = new_value\n")
            else:
                file.write(line)


def restore_config(config_file: Path):
    # Restore the original config file
    shutil.copy(backup_filename(config_file), config_file)
    os.remove(backup_filename(config_file))


def run_script() -> int:
    # Run the main script with arguments
    result = subprocess.run(
        ["python", "path/to/your_script.py", "-c", config_file],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    print(result.stderr)
    return result.returncode


if __name__ == "__main__":
    import json
    from argparse import ArgumentParser
    from pathlib import Path

    with open(Path(__file__).parent / "ingester_wrapper_config.json", 'rt') as f:
        files = json.load(f)

    parser = ArgumentParser()

    parser.add_argument(
        'mission',
        type=str,
        choices=list(files.keys()),
        help='Choose a mission from: {}.'.format(', '.join(files.keys()))
    )

    parser.add_argument(
        "-d",
        dest="data_dir",
        help="Path to the input data directory",
    )

    parser.add_argument(
        "-c",
        dest="config",
        help="Path to the config file",
    )
    args = parser.parse_args()
    config_file = args.config

    # Modify the config file
    try:
        modify_config()
        exit_code = run_script()
    finally:
        restore_config()
        sys.exit(exit_code)
