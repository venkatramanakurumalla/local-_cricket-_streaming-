import tkinter as tk
from tkinter import ttk, messagebox
import vlc
import time
import os
import logging

class CricketScoreboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Local Cricket Software")
        self.root.geometry("1280x720")
        self.root.configure(bg='#2c3e50')
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Match state
        self.match = {
            'team1': {"name": "Team A", "runs": 0, "wickets": 0, "overs": 0.0, "extras": {"wides": 0, "noballs": 0}},
            'team2': {"name": "Team B", "runs": 0, "wickets": 0, "overs": 0.0, "extras": {"wides": 0, "noballs": 0}},
            'current_batting': 1,
            'max_overs': 20
        }
        
        self.batsmen = [
            {"name": "Batsman 1", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False},
            {"name": "Batsman 2", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False}
        ]
        self.bowler = {"name": "Bowler 1", "overs": 0.0, "maidens": 0, "runs": 0, "wickets": 0}
        
        # Stream configuration
        self.streams = {
            "Main Camera": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
            "End Camera": "rtmp://your.stream2.url/live",
            "Wide Angle": "rtmp://your.stream3.url/live"
        }
        self.stream_var = tk.StringVar(value=list(self.streams.keys())[0])  # Moved here
        
        # VLC setup
        try:
            self.vlc_instance = vlc.Instance('--no-xlib')
            self.player = self.vlc_instance.media_player_new()
        except Exception as e:
            self.logger.error(f"VLC initialization failed: {e}")
            messagebox.showerror("Error", "Failed to initialize VLC player")
            return
            
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        self.main_frame = tk.Frame(self.root, bg='#2c3e50')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Video frame
        self.video_frame = tk.Frame(self.main_frame, bg='black')
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Video canvas
        self.video_canvas = tk.Canvas(self.video_frame, bg='black', highlightthickness=0)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Scoreboard overlay
        self.setup_scoreboard_overlay()
        
        # Control panel
        self.setup_controls()
        
        # Initialize stream
        self.change_stream()

    def setup_scoreboard_overlay(self):
        self.score_frame = tk.Frame(self.video_canvas, bg='black', bd=2, relief=tk.RAISED)
        self.score_window = self.video_canvas.create_window(10, 10, window=self.score_frame, anchor='nw')
        
        # Team score
        self.score_var = tk.StringVar()
        tk.Label(self.score_frame, textvariable=self.score_var, font=('Helvetica', 16, 'bold'), 
                bg='black', fg='white').pack(pady=2, padx=5)
        
        # Batsmen
        self.bat1_var = tk.StringVar()
        self.bat2_var = tk.StringVar()
        tk.Label(self.score_frame, textvariable=self.bat1_var, font=('Helvetica', 12), 
                bg='black', fg='white').pack(pady=1, padx=5, anchor='w')
        tk.Label(self.score_frame, textvariable=self.bat2_var, font=('Helvetica', 12), 
                bg='black', fg='white').pack(pady=1, padx=5, anchor='w')
        
        # Bowler
        self.bowler_var = tk.StringVar()
        tk.Label(self.score_frame, textvariable=self.bowler_var, font=('Helvetica', 12), 
                bg='black', fg='white').pack(pady=1, padx=5, anchor='w')
        
        # Extras
        self.extras_var = tk.StringVar()
        tk.Label(self.score_frame, textvariable=self.extras_var, font=('Helvetica', 10), 
                bg='black', fg='yellow').pack(pady=1, padx=5)
        
        # Toggle button
        self.show_score = tk.BooleanVar(value=True)
        tk.Checkbutton(self.score_frame, text="Show", variable=self.show_score, 
                      command=self.toggle_scoreboard, bg='black', fg='white',
                      selectcolor='black', activebackground='black').pack(pady=2)
        
        self.update_scoreboard()

    def setup_controls(self):
        control_frame = tk.Frame(self.main_frame, bg='#34495e')
        control_frame.pack(fill=tk.X, pady=5)
        
        # Stream selection
        tk.Label(control_frame, text="Stream:", bg='#34495e', fg='white').pack(side=tk.LEFT, padx=5)
        stream_dropdown = ttk.Combobox(control_frame, textvariable=self.stream_var, 
                                     values=list(self.streams.keys()), state="readonly")
        stream_dropdown.pack(side=tk.LEFT, padx=5)
        stream_dropdown.bind("<<ComboboxSelected>>", self.change_stream)
        
        # Control buttons
        buttons = [
            ("1", lambda: self.add_runs(1)), ("4", lambda: self.add_runs(4)), 
            ("6", lambda: self.add_runs(6)), ("Wicket", self.add_wicket),
            ("Wide", lambda: self.add_extra("wides")), ("NB", lambda: self.add_extra("noballs")),
            ("Over", self.next_over), ("Switch", self.switch_innings)
        ]
        for text, cmd in buttons:
            tk.Button(control_frame, text=text, command=cmd, bg='#3498db', fg='white',
                     font=('Helvetica', 9)).pack(side=tk.LEFT, padx=2)

    def toggle_scoreboard(self):
        if self.show_score.get():
            self.video_canvas.itemconfigure(self.score_window, state='normal')
        else:
            self.video_canvas.itemconfigure(self.score_window, state='hidden')

    def update_scoreboard(self):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        overs_str = f"{int(team['overs'])}.{int((team['overs'] % 1) * 6)}"
        self.score_var.set(f"{team['name']} {team['runs']}/{team['wickets']} ({overs_str}/{self.match['max_overs']})")
        
        self.bat1_var.set(f"{self.batsmen[0]['name']}{' *' if not self.batsmen[0]['out'] else ''}: "
                         f"{self.batsmen[0]['runs']} ({self.batsmen[0]['balls']})")
        self.bat2_var.set(f"{self.batsmen[1]['name']}{' *' if not self.batsmen[1]['out'] else ''}: "
                         f"{self.batsmen[1]['runs']} ({self.batsmen[1]['balls']})")
        
        overs_str = f"{int(self.bowler['overs'])}.{int((self.bowler['overs'] % 1) * 6)}"
        self.bowler_var.set(f"{self.bowler['name']}: {overs_str} - {self.bowler['maidens']} - "
                          f"{self.bowler['runs']} - {self.bowler['wickets']}")
        
        extras = team['extras']
        self.extras_var.set(f"Extras: {extras['wides'] + extras['noballs']} "
                          f"(W:{extras['wides']} NB:{extras['noballs']})")

    def add_runs(self, runs):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        team['runs'] += runs
        
        striker = next((b for b in self.batsmen if not b['out']), self.batsmen[0])
        striker['runs'] += runs
        striker['balls'] += 1
        if runs == 4: striker['4s'] += 1
        elif runs == 6: striker['6s'] += 1
        
        self.bowler['runs'] += runs
        self.increment_ball()
        self.update_scoreboard()

    def add_wicket(self):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        team['wickets'] += 1
        
        striker = next((b for b in self.batsmen if not b['out']), self.batsmen[0])
        striker['out'] = True
        striker['balls'] += 1
        
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
        self.update_scoreboard()

    def increment_ball(self):
        team = self.match['team1'] if self.match['current_batting'] == 1 else self.match['team2']
        team['overs'] += 0.1
        self.bowler['overs'] += 0.1
        if team['overs'] >= self.match['max_overs']:
            self.switch_innings()

    def next_over(self):
        if self.bowler['runs'] == 0:
            self.bowler['maidens'] += 1
        self.bowler = {"name": f"Bowler {int(time.time())}", "overs": 0.0, "maidens": 0, "runs": 0, "wickets": 0}
        self.update_scoreboard()

    def switch_innings(self):
        self.match['current_batting'] = 2 if self.match['current_batting'] == 1 else 1
        self.batsmen = [
            {"name": f"Batsman {i}", "runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False}
            for i in range(2)
        ]
        self.bowler = {"name": "Bowler 1", "overs": 0.0, "maidens": 0, "runs": 0, "wickets": 0}
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
                
        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            messagebox.showerror("Stream Error", f"Failed to load stream: {e}")

    def on_closing(self):
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