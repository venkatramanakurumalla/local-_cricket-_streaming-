import os
import tkinter as tk
from tkinter import ttk, messagebox
import vlc
import time
from PIL import Image, ImageDraw, ImageFont, ImageTk
import cv2
import numpy as np
import threading

class CricketBroadcastSoftware:
    def __init__(self, root):
        self.root = root
        self.root.title("Cricket Broadcast Software")
        self.root.geometry("1200x800")

        # Match variables
        self.team1 = {"name": "INDIA", "runs": 0, "wickets": 0, "overs": 0.0, "extras": 0}
        self.team2 = {"name": "AUSTRALIA", "runs": 0, "wickets": 0, "overs": 0.0, "extras": 0}
        self.current_batting = 1
        self.batsmen = [
            {"name": "Rohit Sharma", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False},
            {"name": "Virat Kohli", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False}
        ]
        self.bowler = {"name": "Mitchell Starc", "overs": 0, "maidens": 0, "runs": 0, "wickets": 0}

        # RTMP Sources
        self.rtmp_sources = {
            "Main Camera": "rtmp://server/main_cam",
            "End Camera": "rtmp://server/end_cam",
            "Field Camera": "rtmp://server/field_cam"
        }
        self.current_stream = None
        self.streaming = False

        # VLC Setup
        self.vlc_instance = vlc.Instance(["--no-xlib", "--quiet"])
        self.player = self.vlc_instance.media_player_new()
        self.overlay_image = None

        # GUI Setup
        self.create_widgets()

    def create_widgets(self):
        # Main Panels
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Panel - Video Player
        video_frame = tk.LabelFrame(main_frame, text="Live Feed", padx=10, pady=10)
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.video_canvas = tk.Canvas(video_frame, bg="black")
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        # RTMP Source Selection
        source_frame = tk.Frame(video_frame)
        source_frame.pack(fill=tk.X, pady=5)

        tk.Label(source_frame, text="Select Camera:").pack(side=tk.LEFT)
        self.source_var = tk.StringVar()
        self.source_dropdown = ttk.Combobox(
            source_frame, 
            textvariable=self.source_var,
            values=list(self.rtmp_sources.keys())
        )
        self.source_dropdown.pack(side=tk.LEFT, padx=5)
        self.source_dropdown.bind("<<ComboboxSelected>>", self.change_stream)

        # Right Panel - Scoreboard Controls
        control_frame = tk.LabelFrame(main_frame, text="Scoreboard Controls", padx=10, pady=10)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Scoreboard Display
        self.score_label = tk.Label(control_frame, text="INDIA: 0/0 (0.0 ov)", font=("Arial", 14, "bold"))
        self.score_label.pack(pady=10)

        # Batting Controls
        tk.Button(control_frame, text="+1 Run", command=lambda: self.add_runs(1)).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="+4 Runs", command=lambda: self.add_runs(4)).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="+6 Runs", command=lambda: self.add_runs(6)).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="Wicket", command=self.add_wicket).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="Wide/No Ball", command=self.add_extra).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="Next Over", command=self.next_over).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="Switch Innings", command=self.switch_innings).pack(fill=tk.X, pady=2)

        # Streaming Controls
        stream_frame = tk.LabelFrame(control_frame, text="Broadcast Controls", padx=10, pady=10)
        stream_frame.pack(fill=tk.X, pady=10)

        tk.Label(stream_frame, text="YouTube/RTMP URL:").pack()
        self.stream_url = tk.Entry(stream_frame)
        self.stream_url.pack(fill=tk.X, pady=2)
        self.stream_url.insert(0, "rtmp://a.rtmp.youtube.com/live2/YOUR_KEY")

        tk.Button(stream_frame, text="Start Broadcast", command=self.start_broadcast).pack(fill=tk.X, pady=2)
        tk.Button(stream_frame, text="Stop Broadcast", command=self.stop_broadcast).pack(fill=tk.X, pady=2)

        # Initialize first stream
        if self.rtmp_sources:
            self.source_var.set(list(self.rtmp_sources.keys())[0])
            self.change_stream()

    def change_stream(self, event=None):
        """Switch between RTMP sources"""
        source_name = self.source_var.get()
        if source_name in self.rtmp_sources:
            self.current_stream = self.rtmp_sources[source_name]
            media = self.vlc_instance.media_new(self.current_stream)
            self.player.set_media(media)
            
            if os.name == 'nt':  # Windows
                self.player.set_hwnd(self.video_canvas.winfo_id())
            else:  # Linux/Mac
                self.player.set_xwindow(self.video_canvas.winfo_id())
                
            self.player.play()

    def update_scoreboard(self):
        """Update the scoreboard display"""
        team = self.team1 if self.current_batting == 1 else self.team2
        score_text = f"{team['name']}: {team['runs']}/{team['wickets']} ({team['overs']} ov)"
        self.score_label.config(text=score_text)

        # Generate overlay image (for broadcasting)
        self.generate_overlay()

    def generate_overlay(self):
        """Create a transparent scoreboard overlay"""
        width, height = 400, 100
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = ImageFont.truetype("arial.ttf", 20)

        team = self.team1 if self.current_batting == 1 else self.team2
        score_text = f"{team['name']} {team['runs']}/{team['wickets']} ({team['overs']} ov)"
        draw.text((10, 10), score_text, font=font, fill=(255, 255, 255, 255))

        # Convert to OpenCV format (for streaming)
        self.overlay_image = cv2.cvtColor(np.array(overlay), cv2.COLOR_RGBA2BGRA)

    def start_broadcast(self):
        """Start streaming with overlay"""
        if not self.current_stream:
            messagebox.showerror("Error", "No RTMP source selected!")
            return

        rtmp_url = self.stream_url.get()
        if not rtmp_url.startswith("rtmp://"):
            messagebox.showerror("Error", "Invalid RTMP URL!")
            return

        # Start streaming thread
        self.streaming = True
        threading.Thread(target=self.stream_with_overlay, args=(rtmp_url,)).start()

    def stream_with_overlay(self, rtmp_url):
        """Broadcast with scoreboard overlay"""
        stream_options = f":sout=#transcode{{vcodec=h264,vb=2500}}:duplicate{{dst=rtp{{dst={rtmp_url}}}}}"
        media = self.vlc_instance.media_new(self.current_stream, stream_options)
        self.player.set_media(media)
        self.player.play()

        while self.streaming:
            self.generate_overlay()
            time.sleep(1)

    def stop_broadcast(self):
        """Stop streaming"""
        self.streaming = False
        self.player.stop()

    # Scoreboard Functions
    def add_runs(self, runs):
        team = self.team1 if self.current_batting == 1 else self.team2
        team['runs'] += runs
        self.batsmen[0]['runs'] += runs
        self.batsmen[0]['balls'] += 1
        if runs == 4:
            self.batsmen[0]['4s'] += 1
        elif runs == 6:
            self.batsmen[0]['6s'] += 1
        self.bowler['runs'] += runs
        self.update_scoreboard()

    def add_wicket(self):
        team = self.team1 if self.current_batting == 1 else self.team2
        team['wickets'] += 1
        self.bowler['wickets'] += 1
        self.batsmen[0]['out'] = True
        self.update_scoreboard()

    def next_over(self):
        team = self.team1 if self.current_batting == 1 else self.team2
        team['overs'] += 1
        if self.bowler['runs'] == 0:
            self.bowler['maidens'] += 1
        self.update_scoreboard()

    def switch_innings(self):
        self.current_batting = 2 if self.current_batting == 1 else 1
        self.update_scoreboard()

    def add_extra(self):
        team = self.team1 if self.current_batting == 1 else self.team2
        team['runs'] += 1
        team['extras'] += 1
        self.bowler['runs'] += 1
        self.update_scoreboard()

if __name__ == "__main__":
    root = tk.Tk()
    app = CricketBroadcastSoftware(root)
    root.mainloop()