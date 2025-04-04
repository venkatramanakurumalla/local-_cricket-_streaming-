import tkinter as tk
from tkinter import ttk, messagebox
import vlc
import time
import os
import logging
import subprocess
from threading import Thread

class CricketScoreboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Professional Cricket Broadcast Software")
        self.root.geometry("1280x720")
        self.root.configure(bg='#1a1a1a')
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Match state
        self.match = {
            'team1': {"name": "Team A", "runs": 0, "wickets": 0, "overs": 0.0, "extras": {"wides": 0, "noballs": 0, "byes": 0, "legbyes": 0}},
            'team2': {"name": "Team B", "runs": 0, "wickets": 0, "overs": 0.0, "extras": {"wides": 0, "noballs": 0, "byes": 0, "legbyes": 0}},
            'current_batting': 1,
            'max_overs': 20,
            'target': 0,
            'current_ball': 0
        }
        
        self.batsmen = [
            {"name": "Batsman 1", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False, "dismissal": ""},
            {"name": "Batsman 2", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False, "dismissal": ""}
        ]
        self.bowler = {"name": "Bowler 1", "overs": 0.0, "maidens": 0, "runs": 0, "wickets": 0}
        
        # Stream configuration with fallback
        self.streams = {
            "Main Camera": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
            "Fallback": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "End Camera": "rtmp://your.stream2.url/live",
            "Wide Angle": "rtmp://your.stream3.url/live"
        }
        self.stream_var = tk.StringVar(value=list(self.streams.keys())[0])
        self.stream_status_var = tk.StringVar(value="Not Connected")
        
        # Streaming platforms
        self.streaming_platforms = {
            "YouTube": {"rtmp": "", "key": "", "active": False},
            "Facebook": {"rtmp": "", "key": "", "active": False},
            "Twitter": {"rtmp": "", "key": "", "active": False}
        }
        self.ffmpeg_processes = {}
        
        # VLC setup with improved parameters
        try:
            self.vlc_instance = vlc.Instance('--no-xlib', '--network-caching=1000', '--file-caching=1000', '--live-caching=1000')
            self.player = self.vlc_instance.media_player_new()
            self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEncounteredError, self.stream_error_handler)
        except Exception as e:
            self.logger.error(f"VLC initialization failed: {e}")
            messagebox.showerror("Error", "Failed to initialize VLC player")
            return
            
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        self.main_frame = tk.Frame(self.root, bg='#1a1a1a')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.video_frame = tk.Frame(self.main_frame, bg='black')
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        self.video_canvas = tk.Canvas(self.video_frame, bg='black', highlightthickness=0)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.setup_professional_scoreboard()
        self.setup_controls()
        self.setup_streaming_controls()
        
        self.change_stream()

    def setup_professional_scoreboard(self):
        self.score_frame = tk.Frame(self.video_canvas, bg='#333333', bd=2, relief=tk.SUNKEN)
        self.score_window = self.video_canvas.create_window(10, 10, window=self.score_frame, anchor='nw')
        
        top_frame = tk.Frame(self.score_frame, bg='#0066cc')
        top_frame.pack(fill=tk.X, pady=(0, 2))
        
        self.team_var = tk.StringVar()
        tk.Label(top_frame, textvariable=self.team_var, font=('Arial', 14, 'bold'), 
                bg='#0066cc', fg='white').pack(side=tk.LEFT, padx=5)
        
        self.score_var = tk.StringVar()
        tk.Label(top_frame, textvariable=self.score_var, font=('Arial', 16, 'bold'), 
                bg='#0066cc', fg='yellow').pack(side=tk.LEFT, padx=5)
        
        batsmen_frame = tk.Frame(self.score_frame, bg='#333333')
        batsmen_frame.pack(fill=tk.X, padx=5)
        
        self.bat1_name = tk.StringVar()
        self.bat1_stats = tk.StringVar()
        tk.Label(batsmen_frame, textvariable=self.bat1_name, font=('Arial', 12, 'bold'), 
                bg='#333333', fg='white').pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(batsmen_frame, textvariable=self.bat1_stats, font=('Arial', 12), 
                bg='#333333', fg='white').pack(side=tk.LEFT)
        
        self.bat2_name = tk.StringVar()
        self.bat2_stats = tk.StringVar()
        tk.Label(batsmen_frame, textvariable=self.bat2_name, font=('Arial', 12, 'bold'), 
                bg='#333333', fg='white').pack(side=tk.LEFT, padx=(20, 10))
        tk.Label(batsmen_frame, textvariable=self.bat2_stats, font=('Arial', 12), 
                bg='#333333', fg='white').pack(side=tk.LEFT)
        
        bottom_frame = tk.Frame(self.score_frame, bg='#333333')
        bottom_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.bowler_var = tk.StringVar()
        tk.Label(bottom_frame, textvariable=self.bowler_var, font=('Arial', 11), 
                bg='#333333', fg='white').pack(side=tk.LEFT)
        
        self.extras_var = tk.StringVar()
        tk.Label(bottom_frame, textvariable=self.extras_var, font=('Arial', 11), 
                bg='#333333', fg='yellow').pack(side=tk.RIGHT, padx=5)
        
        info_frame = tk.Frame(self.score_frame, bg='#333333')
        info_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.rr_var = tk.StringVar()
        tk.Label(info_frame, textvariable=self.rr_var, font=('Arial', 10), 
                bg='#333333', fg='white').pack(side=tk.LEFT)
        
        self.target_var = tk.StringVar()
        tk.Label(info_frame, textvariable=self.target_var, font=('Arial', 10), 
                bg='#333333', fg='white').pack(side=tk.RIGHT, padx=5)
        
        self.show_score = tk.BooleanVar(value=True)
        tk.Checkbutton(self.score_frame, text="Show", variable=self.show_score, 
                      command=self.toggle_scoreboard, bg='#333333', fg='white',
                      selectcolor='#333333', activebackground='#333333').pack(pady=2)
        
        self.update_scoreboard()

    def setup_controls(self):
        control_frame = tk.Frame(self.main_frame, bg='#2c3e50')
        control_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(control_frame, text="Input:", bg='#2c3e50', fg='white').pack(side=tk.LEFT, padx=5)
        ttk.Combobox(control_frame, textvariable=self.stream_var, 
                    values=list(self.streams.keys()), state="readonly").pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, textvariable=self.stream_status_var, bg='#2c3e50', fg='yellow').pack(side=tk.LEFT, padx=5)
        
        buttons = [
            ("0", lambda: self.add_runs(0)), ("1", lambda: self.add_runs(1)), 
            ("2", lambda: self.add_runs(2)), ("4", lambda: self.add_runs(4)), 
            ("6", lambda: self.add_runs(6)), ("Wicket", self.add_wicket),
            ("Wide", lambda: self.add_extra("wides")), ("NB", lambda: self.add_extra("noballs")),
            ("Bye", lambda: self.add_extra("byes")), ("LB", lambda: self.add_extra("legbyes")),
            ("Over", self.next_over), ("Switch", self.switch_innings)
        ]
        for text, cmd in buttons:
            tk.Button(control_frame, text=text, command=cmd, bg='#3498db', fg='white',
                     font=('Helvetica', 9)).pack(side=tk.LEFT, padx=2)

    def setup_streaming_controls(self):
        stream_frame = tk.LabelFrame(self.main_frame, text="Streaming Control", bg='#2c3e50', fg='white')
        stream_frame.pack(fill=tk.X, pady=5)
        
        for platform in self.streaming_platforms:
            plat_frame = tk.Frame(stream_frame, bg='#2c3e50')
            plat_frame.pack(fill=tk.X, pady=2)
            
            tk.Label(plat_frame, text=f"{platform}:", bg='#2c3e50', fg='white', width=8).pack(side=tk.LEFT)
            
            rtmp_entry = tk.Entry(plat_frame, width=30)
            rtmp_entry.pack(side=tk.LEFT, padx=2)
            rtmp_entry.insert(0, self.streaming_platforms[platform]["rtmp"])
            
            key_entry = tk.Entry(plat_frame, width=20)
            key_entry.pack(side=tk.LEFT, padx=2)
            key_entry.insert(0, self.streaming_platforms[platform]["key"])
            
            tk.Button(plat_frame, text="Start", command=lambda p=platform, r=rtmp_entry, k=key_entry: self.start_streaming(p, r, k),
                     bg='#2ecc71', fg='white').pack(side=tk.LEFT, padx=2)
            tk.Button(plat_frame, text="Stop", command=lambda p=platform: self.stop_streaming(p),
                     bg='#e74c3c', fg='white').pack(side=tk.LEFT, padx=2)

    def start_streaming(self, platform, rtmp_entry, key_entry):
        if self.streaming_platforms[platform]["active"]:
            messagebox.showinfo("Info", f"Already streaming to {platform}!")
            return
            
        rtmp_url = rtmp_entry.get()
        stream_key = key_entry.get()
        
        if not rtmp_url or not stream_key:
            messagebox.showerror("Error", "Please enter RTMP URL and Stream Key")
            return
            
        self.streaming_platforms[platform]["rtmp"] = rtmp_url
        self.streaming_platforms[platform]["key"] = stream_key
        
        input_stream = self.streams[self.stream_var.get()]
        output_url = f"{rtmp_url}/{stream_key}"
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-re', '-i', input_stream,
            '-c:v', 'libx264', '-preset', 'veryfast', '-b:v', '3000k',
            '-c:a', 'aac', '-b:a', '128k',
            '-f', 'flv', output_url
        ]
        
        try:
            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.ffmpeg_processes[platform] = process
            self.streaming_platforms[platform]["active"] = True
            self.logger.info(f"Started streaming to {platform}")
            Thread(target=self.monitor_stream, args=(platform,)).start()
        except Exception as e:
            self.logger.error(f"Streaming to {platform} failed: {e}")
            messagebox.showerror("Error", f"Failed to start streaming to {platform}: {e}")

    def stop_streaming(self, platform):
        if not self.streaming_platforms[platform]["active"] or platform not in self.ffmpeg_processes:
            return
            
        self.ffmpeg_processes[platform].terminate()
        del self.ffmpeg_processes[platform]
        self.streaming_platforms[platform]["active"] = False
        self.logger.info(f"Stopped streaming to {platform}")

    def monitor_stream(self, platform):
        process = self.ffmpeg_processes[platform]
        process.wait()
        if platform in self.ffmpeg_processes:
            del self.ffmpeg_processes[platform]
            self.streaming_platforms[platform]["active"] = False
            self.logger.info(f"Stream to {platform} ended")

    def stream_error_handler(self, event):
        self.stream_status_var.set("Stream Error - Switching to Fallback")
        self.logger.warning("Stream error detected, switching to fallback")
        self.stream_var.set("Fallback")
        self.change_stream()

    def toggle_scoreboard(self):
        self.video_canvas.itemconfigure(self.score_window, state='normal' if self.show_score.get() else 'hidden')

    def update_scoreboard(self):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        overs_str = f"{int(team['overs'])}.{int((team['overs'] % 1) * 6)}"
        
        self.team_var.set(team['name'])
        self.score_var.set(f"{team['runs']}/{team['wickets']} ({overs_str})")
        
        self.bat1_name.set(f"{self.batsmen[0]['name']}{' *' if not self.batsmen[0]['out'] else ''}")
        self.bat1_stats.set(f"{self.batsmen[0]['runs']} ({self.batsmen[0]['balls']}) 4s:{self.batsmen[0]['4s']} 6s:{self.batsmen[0]['6s']}")
        self.bat2_name.set(f"{self.batsmen[1]['name']}{' *' if not self.batsmen[1]['out'] else ''}")
        self.bat2_stats.set(f"{self.batsmen[1]['runs']} ({self.batsmen[1]['balls']}) 4s:{self.batsmen[1]['4s']} 6s:{self.batsmen[1]['6s']}")
        
        overs_str = f"{int(self.bowler['overs'])}.{int((self.bowler['overs'] % 1) * 6)}"
        self.bowler_var.set(f"{self.bowler['name']} {overs_str}-{self.bowler['maidens']}-{self.bowler['runs']}-{self.bowler['wickets']}")
        
        extras = team['extras']
        total_extras = sum(extras.values())
        self.extras_var.set(f"Extras {total_extras} (W:{extras['wides']} NB:{extras['noballs']} B:{extras['byes']} LB:{extras['legbyes']})")
        
        balls = int(team['overs'] * 6 + (team['overs'] % 1) * 10)
        rr = f"{team['runs']/balls*6:.2f}" if balls > 0 else "0.00"
        self.rr_var.set(f"RR: {rr}")
        
        if self.match['current_batting'] == 2 and self.match['target'] > 0:
            remaining = self.match['target'] - team['runs']
            balls_left = int(self.match['max_overs'] * 6 - balls)
            rrr = f"{remaining/balls_left*6:.2f}" if balls_left > 0 else "0.00"
            self.target_var.set(f"Need {remaining} off {balls_left} (RRR: {rrr})")
        else:
            self.target_var.set("")
        
        self.stream_status_var.set("Connected" if self.player.is_playing() else "Disconnected")

    def add_runs(self, runs):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        team['runs'] += runs
        
        striker = next((b for b in self.batsmen if not b['out']), self.batsmen[0])
        striker['runs'] += runs
        if runs > 0:
            striker['balls'] += 1
            if runs == 4: striker['4s'] += 1
            elif runs == 6: striker['6s'] += 1
        
        self.bowler['runs'] += runs
        if runs <= 6:
            self.increment_ball()
        self.update_scoreboard()

    def add_wicket(self):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        team['wickets'] += 1
        
        striker = next((b for b in self.batsmen if not b['out']), self.batsmen[0])
        striker['out'] = True
        striker['balls'] += 1
        striker['dismissal'] = f"b {self.bowler['name']}"
        
        self.bowler['wickets'] += 1
        self.increment_ball()
        self.update_scoreboard()
        
        if team['wickets'] == 10:
            self.switch_innings()

    def add_extra(self, extra_type):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        team['runs'] += 1
        team['extras'][extra_type] += 1
        self.bowler['runs'] += 1
        if extra_type in ["wides", "noballs"]:
            self.match['current_ball'] -= 1
        self.update_scoreboard()

    def increment_ball(self):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        self.match['current_ball'] += 1
        team['overs'] = self.match['current_ball'] / 6
        self.bowler['overs'] = self.match['current_ball'] / 6
        if team['overs'] >= self.match['max_overs']:
            self.switch_innings()

    def next_over(self):
        if self.bowler['runs'] == 0 and self.match['current_ball'] % 6 == 0:
            self.bowler['maidens'] += 1
        self.bowler = {"name": f"Bowler {int(time.time())}", "overs": 0.0, "maidens": 0, "runs": 0, "wickets": 0}
        self.update_scoreboard()

    def switch_innings(self):
        if self.match['current_batting'] == 1:
            self.match['target'] = self.match['team1']['runs'] + 1
            self.match['current_batting'] = 2
        else:
            self.match['current_batting'] = 1
            self.match['target'] = 0
        
        self.batsmen = [
            {"name": f"Batsman {i}", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False, "dismissal": ""}
            for i in range(2)
        ]
        self.bowler = {"name": "Bowler 1", "overs": 0.0, "maidens": 0, "runs": 0, "wickets": 0}
        self.match['current_ball'] = 0
        self.update_scoreboard()

    def change_stream(self, event=None):
        try:
            selected = self.stream_var.get()
            if not selected or selected not in self.streams:
                return
                
            self.player.stop()
            media = self.vlc_instance.media_new(self.streams[selected])
            self.player.set_media(media)
            
            if os.name == 'nt':
                self.player.set_hwnd(self.video_canvas.winfo_id())
            else:
                self.player.set_xwindow(self.video_canvas.winfo_id())
                
            if self.player.play() == -1:
                raise Exception("Failed to play stream")
            else:
                self.stream_status_var.set("Connected")
                
        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            self.stream_status_var.set("Error")
            messagebox.showerror("Stream Error", f"Failed to load stream: {e}")

    def on_closing(self):
        for platform in list(self.ffmpeg_processes.keys()):
            self.stop_streaming(platform)
        self.player.stop()
        self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = CricketScoreboardApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        messagebox.showerror("Error", "Application failed to start")