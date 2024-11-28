#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Treat unset variables as an error and exit immediately.
set -u

# Pipe failures should be detected when piping commands.
set -o pipefail

# Check if pip3 is available.
if ! command -v pip3 &> /dev/null; then
  echo "Error: pip3 is not installed or not in the PATH."
  exit 1
fi

# Install or upgrade the langgraph-cli package.
echo "Installing or upgrading langgraph-cli..."
pip3 install -U "langgraph-cli[inmem]"

# Check if langgraph command is available.
if ! command -v langgraph &> /dev/null; then
  echo "Error: langgraph is not installed or not in the PATH."
  exit 1
fi

# Validate the configuration file exists.
CONFIG_FILE="./langgraph.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Error: Configuration file $CONFIG_FILE not found."
  exit 1
fi

# Run the langgraph dev command.
echo "Running langgraph with the specified configuration..."
langgraph dev --config "$CONFIG_FILE"
