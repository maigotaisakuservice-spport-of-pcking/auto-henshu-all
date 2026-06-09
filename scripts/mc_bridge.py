import subprocess
import time
import os
import signal

class MinecraftBridge:
    def __init__(self, mc_path="minecraft", display=":99", resolution="1280x720"):
        self.mc_path = mc_path
        self.display = display
        self.resolution = resolution
        self.mc_process = None
        self.record_process = None

    def start_display(self):
        print(f"Starting Xvfb on {self.display}...")
        subprocess.Popen(["Xvfb", self.display, "-screen", "0", f"{self.resolution}x24"])
        os.environ["DISPLAY"] = self.display

    def start_recording(self, output_file):
        print(f"Starting ffmpeg recording to {output_file}...")
        # Capture the Xvfb display
        cmd = [
            "ffmpeg", "-f", "x11grab", "-video_size", self.resolution,
            "-i", self.display, "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", output_file, "-y"
        ]
        self.record_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def get_classpath(self):
        """Constructs a comprehensive classpath by scanning the libraries and versions directories."""
        cp_parts = []

        # 1. Find the Forge Universal/Client jar in the root
        forge_jars = [f for f in os.listdir(self.mc_path) if f.startswith("forge-") and f.endswith(".jar")]
        for jar in forge_jars:
            cp_parts.append(jar)

        # 2. Recursively add all jars in the 'libraries' folder
        lib_dir = os.path.join(self.mc_path, "libraries")
        if os.path.exists(lib_dir):
            for root, _, files in os.walk(lib_dir):
                for file in files:
                    if file.endswith(".jar"):
                        # Use relative path from mc_path
                        rel_path = os.path.relpath(os.path.join(root, file), self.mc_path)
                        cp_parts.append(rel_path)

        # 3. Add the vanilla 1.12.2 jar
        vanilla = "versions/1.12.2/1.12.2.jar"
        if os.path.exists(os.path.join(self.mc_path, vanilla)):
            cp_parts.append(vanilla)

        return ":".join(cp_parts)

    def start_minecraft(self):
        print("Starting Minecraft Forge 1.12.2...")
        classpath = self.get_classpath()

        if "launchwrapper" not in classpath:
            print("WARNING: launchwrapper not found in classpath. Forge installation might be incomplete.")

        cmd = [
            "java", "-Xmx2G",
            "-Djava.library.path=versions/1.12.2/1.12.2-natives",
            "-cp", classpath,
            "net.minecraft.launchwrapper.Launch",
            "--gameDir", ".",
            "--version", "1.12.2",
            "--assetsDir", "assets",
            "--assetIndex", "1.12",
            "--userProperties", "{}",
            "--accessToken", "0",
            "--username", "AI_Player",
            "--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker"
        ]

        print(f"Running Minecraft with classpath of {len(classpath.split(':'))} jars.")
        # Log the command for debugging (be careful with tokens, but here tokens are mock)
        self.mc_process = subprocess.Popen(cmd, cwd=self.mc_path)

    def send_baritone_command(self, command):
        print(f"Executing Baritone command: {command}")
        # Command is sent by writing to the 'chat' via a local mod or stdin bridge.
        # We use a helper file that a custom mod on the Minecraft side would read.
        with open(os.path.join(self.mc_path, "baritone_cmd.txt"), "w") as f:
            f.write(command)

    def stop_all(self):
        if self.record_process:
            self.record_process.send_signal(signal.SIGINT)
            self.record_process.wait()
            print("Recording stopped.")
        if self.mc_process:
            self.mc_process.terminate()
            print("Minecraft stopped.")

if __name__ == "__main__":
    bridge = MinecraftBridge()
    bridge.start_display()
    bridge.start_recording("test_capture.mp4")
    bridge.start_minecraft()
    time.sleep(10)
    bridge.stop_all()
