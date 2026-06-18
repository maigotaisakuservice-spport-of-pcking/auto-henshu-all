#!/bin/bash
set -e

# Minecraft 1.12.2 Setup with Forge and Baritone (CI Optimized)
MC_DIR="minecraft"
MC_VERSION="1.12.2"
FORGE_VERSION="14.23.5.2859"

echo "Setting up Minecraft $MC_VERSION with Forge $FORGE_VERSION..."

# 1. Prepare Directory
rm -rf $MC_DIR
mkdir -p $MC_DIR/mods

# 2. Install Dependencies
sudo apt-get update
sudo apt-get install -y xvfb ffmpeg libx11-6 python3-pip curl xdotool

# 3. Pre-place Vanilla Server JAR (Crucial for checksum match)
# Forge installer looks for this exact name to avoid binary discrepancy errors
echo "Downloading vanilla server JAR..."
curl -Lo "$MC_DIR/minecraft_server.$MC_VERSION.jar" "https://piston-data.mojang.com/v1/objects/886945bfb2b978778c3a0288fd7fab09d315b25f/server.jar"

# 4. Download Forge Installer
echo "Downloading Forge installer..."
curl -Lo "$MC_DIR/forge-installer.jar" "https://maven.minecraftforge.net/net/minecraftforge/forge/$MC_VERSION-$FORGE_VERSION/forge-$MC_VERSION-$FORGE_VERSION-installer.jar"

# 5. Run Forge Installer (Headless Server Mode)
echo "Installing Forge Server..."
cd $MC_DIR
java -jar forge-installer.jar --installServer .

# 6. Cleanup Installer
rm forge-installer.jar

# 7. Download Baritone (Stable 1.12.2)
echo "Downloading Baritone..."
curl -Lo mods/baritone.jar https://github.com/cabaletta/baritone/releases/download/v1.2.15/baritone-api-forge-1.2.15.jar

# 8. Accept EULA
echo "eula=true" > eula.txt

# 9. Create dummy launcher profiles for client-side detection if needed
echo '{"profiles": {}}' > launcher_profiles.json

echo "Setup Complete. Vanilla JAR and Forge Universal JAR are now synchronized."
