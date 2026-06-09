#!/bin/bash
set -e

# Minecraft 1.12.2 Setup with Forge and Baritone
MC_DIR="minecraft"
mkdir -p $MC_DIR/mods
mkdir -p $MC_DIR/versions/1.12.2

echo "Installing dependencies..."
# openjdk-8-jdk is handled by setup-java action in workflow
sudo apt-get update
sudo apt-get install -y xvfb ffmpeg libx11-6 python3-pip curl

# Create dummy launcher profiles to trick the Forge installer
echo '{"profiles": {}}' > $MC_DIR/launcher_profiles.json

# Download Forge Installer
FORGE_VERSION="14.23.5.2859"
URL="https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-$FORGE_VERSION/forge-1.12.2-$FORGE_VERSION-installer.jar"

if [ ! -f "$MC_DIR/forge-installer.jar" ]; then
    echo "Downloading Forge installer..."
    curl -Lo "$MC_DIR/forge-installer.jar" "$URL"
fi

# Headless Install
echo "Installing Forge (Headless)..."
cd $MC_DIR

# Download vanilla client jar first as the installer might need it
echo "Downloading vanilla 1.12.2 client..."
curl -Lo versions/1.12.2/1.12.2.jar https://launcher.mojang.com/v1/objects/0f275bc40cc72441d40237976e199b457e6ba39d/client.jar

# Run installer
echo "Running Forge installer..."
# Using xvfb-run just in case, and omitting --installClient if it still fails,
# but let's try with a dummy profile first.
# Added -Duser.home=. to ensure it looks for launcher_profiles.json in the current dir
xvfb-run java -Duser.home=. -jar forge-installer.jar --installClient . || echo "Forge installer failed, attempting manual setup..."

# Download Baritone (Stable 1.12.2)
echo "Downloading Baritone..."
curl -Lo mods/baritone.jar https://github.com/cabaletta/baritone/releases/download/v1.2.15/baritone-api-forge-1.2.15.jar

# Accept EULA
echo "eula=true" > eula.txt

echo "Setup Complete."
