import importlib.metadata
import re
import requests


def get_installed_version(package_name):
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def get_latest_version_from_pypi(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            latest_version = data['info']['version']
            return latest_version
        else:
            return None
    except Exception:
        return None


def parse_requirement_line(line):
    pattern = r'^([^=\[\]]+)(\[[^\]]+\])?\s*(==|~=|>=|<=|!=|<|>)?\s*(.+)?$'
    match = re.match(pattern, line.strip())
    if match:
        package_name = match.group(1)
        extras = match.group(2)  # e.g., [standard]
        operator = match.group(3)  # e.g., '==', '>=', etc.
        version = match.group(4)  # version string
        return package_name.strip(), extras, operator, version
    else:
        return None, None, None, None


def update_requirements_file(requirements_file):
    updated_lines = []

    with open(requirements_file, "r") as file:
        for line in file:
            package_line = line.rstrip('\n')

            # Ignore comments or empty lines
            if not package_line.strip() or package_line.strip().startswith("#"):
                updated_lines.append(package_line)
                continue

            package_name, extras, operator, version = parse_requirement_line(package_line)

            if package_name is None:
                # Line could not be parsed, keep as is
                updated_lines.append(package_line)
                continue

            # Remove extras from package name for version lookup
            package_name_no_extras = package_name

            installed_version = get_installed_version(package_name_no_extras)

            if installed_version:
                operator = '=='
                version = installed_version
            else:
                if operator is None:
                    # No version specified and package not installed
                    latest_version = get_latest_version_from_pypi(package_name_no_extras)
                    if latest_version:
                        operator = '=='
                        version = latest_version
                    else:
                        # Could not get version, keep the line as is
                        updated_lines.append(package_line)
                        continue
                else:
                    # Package not installed, operator is specified
                    # Keep original line
                    updated_lines.append(package_line)
                    continue

            # Reconstruct the requirement line
            updated_line = package_name
            if extras:
                updated_line += extras
            if operator and version:
                updated_line += f"{operator}{version}"
            updated_lines.append(updated_line)

    # Write the updated content back to requirements.txt
    with open(requirements_file, "w") as file:
        file.write("\n".join(updated_lines) + "\n")


if __name__ == "__main__":
    requirements_file = "requirements.txt"
    update_requirements_file(requirements_file)
