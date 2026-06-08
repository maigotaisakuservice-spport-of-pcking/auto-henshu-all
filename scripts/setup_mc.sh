#!/bin/bash
set -e

# Minecraft 1.12.2 Setup with Forge and Baritone
MC_DIR="minecraft"
mkdir -p $MC_DIR/mods

echo "Installing OpenJDK 8 and dependencies..."
sudo apt-get update
sudo apt-get install -y openjdk-8-jdk xvfb ffmpeg libx11-6 python3-pip curl

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
# Use xvfb-run to ensure headless mode doesn't crash on GUI checks
# Using --downloadMirror to help with library acquisition
xvfb-run java -jar forge-installer.jar --installClient .

# Ensure assets and natives are present (Minecraft 1.12.2 legacy)
mkdir -p assets/indexes versions/1.12.2
curl -Lo versions/1.12.2/1.12.2.jar https://launcher.mojang.com/v1/objects/0f275bc40cc72441d40237976e199b457e6ba39d/client.jar

# Download Baritone (Stable 1.12.2)
echo "Downloading Baritone..."
curl -Lo mods/baritone.jar https://github.com/cabaletta/baritone/releases/download/v1.2.15/baritone-api-forge-1.2.15.jar

# Accept EULA
echo "eula=true" > eula.txt

echo "Setup Complete."
