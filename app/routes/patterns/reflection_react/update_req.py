import subprocess
import re


def get_installed_version(package_name):
    """Get the latest installed version of the package."""
    result = subprocess.run(['pip', 'show', package_name], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split()[1]
    return None


def upgrade_packages(requirements_file):
    with open(requirements_file, 'r') as file:
        lines = file.readlines()

    updated_lines = []

    for line in lines:
        # Extract package name and current version (handles == and ~= cases)
        match = re.match(r'([a-zA-Z0-9\-_]+)(==|~=)([0-9.]+)', line)
        if match:
            package_name = match.group(1)
            print(f"Upgrading {package_name}...")
            # Upgrade the package to the latest version
            subprocess.run(['pip', 'install', '--upgrade', package_name])

            # Get the latest installed version
            new_version = get_installed_version(package_name)
            if new_version:
                # Replace the version in the line
                updated_lines.append(f"{package_name}=={new_version}\n")
            else:
                updated_lines.append(line)
        else:
            # Handle lines that don't match the version pattern (e.g., comments)
            updated_lines.append(line)

    # Write the updated requirements to the file
    with open(requirements_file, 'w') as file:
        file.writelines(updated_lines)

    print("All packages have been upgraded and requirements.txt has been updated.")


if __name__ == "__main__":
    upgrade_packages('requirements.txt')
