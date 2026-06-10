#!/bin/bash
set -e

# Minecraft 1.12.2 Setup with Forge and Baritone
MC_DIR="minecraft"
# rm -rf $MC_DIR # Don't always delete, might want to cache?
# But CI is clean anyway. Let's keep it for safety.
mkdir -p $MC_DIR/mods
mkdir -p $MC_DIR/versions/1.12.2

echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y xvfb ffmpeg libx11-6 python3-pip curl xdotool

# Create dummy launcher profiles
echo '{"profiles": {}}' > $MC_DIR/launcher_profiles.json

# Download Forge Installer
FORGE_VERSION="14.23.5.2859"
URL="https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-$FORGE_VERSION/forge-1.12.2-$FORGE_VERSION-installer.jar"

if [ ! -f "$MC_DIR/forge-installer.jar" ]; then
    echo "Downloading Forge installer..."
    curl -Lo "$MC_DIR/forge-installer.jar" "$URL"
fi

# Headless Install
cd $MC_DIR

# Function to run command with retries
run_with_retry() {
    local max_attempts=3
    local timeout=5
    local attempt=1
    local exitCode=0

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt of $max_attempts: $@"
        set +e
        "$@"
        exitCode=$?
        set -e

        if [ $exitCode -eq 0 ]; then
            return 0
        fi

        echo "Command failed with exit code $exitCode. Retrying in $timeout seconds..."
        sleep $timeout
        attempt=$((attempt + 1))
        timeout=$((timeout * 2))
    done

    echo "Command failed after $max_attempts attempts."
    return $exitCode
}

# Install Server (most reliable for libraries)
echo "Installing Forge Server..."
run_with_retry java -jar forge-installer.jar --installServer .

# Install Client (for assets/client libs)
echo "Installing Forge Client..."
run_with_retry xvfb-run java -Duser.home=. -jar forge-installer.jar --installClient . || echo "Client install warning, continuing..."

# Download Baritone (Stable 1.12.2)
if [ ! -f "mods/baritone.jar" ]; then
    echo "Downloading Baritone..."
    curl -Lo mods/baritone.jar https://github.com/cabaletta/baritone/releases/download/v1.2.15/baritone-api-forge-1.2.15.jar
fi

# Accept EULA
echo "eula=true" > eula.txt

echo "Setup Complete."
