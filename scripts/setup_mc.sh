#!/bin/bash
set -e

# Minecraft 1.12.2 Setup with Forge and Baritone
MC_DIR="minecraft"
mkdir -p $MC_DIR/mods

echo "Installing OpenJDK 8 and dependencies..."
sudo apt-get update
sudo apt-get install -y openjdk-8-jre-headless xvfb ffmpeg libx11-6 python3-pip

# Download Forge Installer
FORGE_VERSION="14.23.5.2859"
URL="https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-$FORGE_VERSION/forge-1.12.2-$FORGE_VERSION-installer.jar"

if [ ! -f "$MC_DIR/forge-installer.jar" ]; then
    curl -Lo "$MC_DIR/forge-installer.jar" "$URL"
fi

# Headless Install
cd $MC_DIR
java -jar forge-installer.jar --installClient . > /dev/null

# Download Baritone (Stable 1.12.2)
curl -Lo mods/baritone.jar https://github.com/cabaletta/baritone/releases/download/v1.2.15/baritone-api-forge-1.2.15.jar

# Accept EULA
echo "eula=true" > eula.txt

echo "Setup Complete. Run via 'java -jar forge-1.12.2-$FORGE_VERSION.jar'"
