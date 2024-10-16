import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import time
import queue
import yt_dlp
import socket

class Downloader:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Downloader")

        # URL Entry
        self.url_label = tk.Label(master, text="URL")
        self.url_entry = tk.Entry(master, width=50)

        # Download button
        self.download_button = tk.Button(master, text="Download", command=self.start_download_thread)
        self.pause_button = tk.Button(master, text="Pause", command=self.pause_download, state=tk.DISABLED)
        self.resume_button = tk.Button(master, text="Resume", command=self.resume_download, state=tk.DISABLED)

        # Progress bar and download speed label
        self.progress = ttk.Progressbar(master, length=300)
        self.speed_label = tk.Label(master, text="Download speed: 0 MB/sec")

        # Queue list with video names and status
        self.queue_label = tk.Label(master, text="Queue")
        self.queue_frame = tk.Frame(master)
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=("Video", "Status"), show="headings")
        self.queue_tree.heading("Video", text="Video")
        self.queue_tree.heading("Status", text="Status")
        self.queue_tree.column("Video", width=300)
        self.queue_tree.column("Status", width=100)

        # Scrollbar for queue list
        self.scrollbar = ttk.Scrollbar(self.queue_frame, orient='vertical', command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=self.scrollbar.set)

        # Grid layout for better alignment
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=3, sticky="ew")
        self.download_button.grid(row=1, column=1, padx=5, pady=5)
        self.pause_button.grid(row=1, column=2, padx=5, pady=5)
        self.resume_button.grid(row=1, column=3, padx=5, pady=5)
        self.progress.grid(row=2, column=1, padx=5, pady=5, columnspan=3, sticky="ew")
        self.speed_label.grid(row=3, column=1, padx=5, pady=5, columnspan=3, sticky="ew")
        self.queue_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.queue_frame.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.queue_tree.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Column weight configuration for expanding widgets
        master.columnconfigure(1, weight=1)
        master.columnconfigure(2, weight=1)
        master.columnconfigure(3, weight=1)
        master.rowconfigure(5, weight=1)

        # Download management
        self.download_queue = queue.Queue()
        self.current_download = None
        self.start_time = None
        self.last_update_time = None
        self.paused = False
        self.download_active = True

    def start_download_thread(self):
        url = self.url_entry.get()
        self.download_queue.put(url)

        if not self.current_download:
            self.current_download = True
            threading.Thread(target=self.process_queue).start()

    def process_queue(self):
        while not self.download_queue.empty() and self.download_active:
            url = self.download_queue.get()
            self.current_download = url

            save_path = filedialog.askdirectory()
            if not save_path:
                return  # User cancelled

            try:
                if 'playlist' in url:
                    self.handle_playlist(url, save_path)
                else:
                    self.handle_video(url, save_path)
            except Exception as e:
                self.master.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")

            self.current_download = None

    def handle_playlist(self, playlist_url, save_path):
        """Handles downloading a playlist, adding all videos to the queue."""
        with yt_dlp.YoutubeDL() as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            video_urls = [entry['webpage_url'] for entry in playlist_info['entries']]

            # Add each video to the queue tree
            for i, video_url in enumerate(video_urls):
                video_title = playlist_info['entries'][i]['title']
                self.queue_tree.insert('', 'end', values=(video_title, "Queued"))
                self.download_queue.put(video_url)

    def handle_video(self, video_url, save_path):
        """Handles downloading a single video."""
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{save_path}/%(title)s.%(ext)s',
            'progress_hooks': [self.progress_function],
            'noprogress': False
        }

        video_title = self.queue_tree.item(self.queue_tree.get_children()[0])['values'][0]
        self.update_status(video_title, "Downloading")
        self.start_time = time.time()

        retry = True
        while retry:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                retry = False  # Download succeeded, exit loop
            except Exception as e:
                if self.is_connection_error(e):
                    self.update_status(video_title, "Retrying...")
                    time.sleep(5)  # Wait for 5 seconds before retrying
                else:
                    raise e

        self.update_status(video_title, "Downloaded")

    def update_status(self, video_title, status):
        """Update the status of a video in the queue tree."""
        for row in self.queue_tree.get_children():
            if self.queue_tree.item(row)['values'][0] == video_title:
                self.queue_tree.item(row, values=(video_title, status))
                break

    def progress_function(self, d):
        """Progress hook to update the progress bar and download speed."""
        if d['status'] == 'downloading':
            total_size = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            bytes_downloaded = d.get('downloaded_bytes', 0)

            # Avoid division by zero
            if total_size:
                percentage = (bytes_downloaded / total_size) * 100
            else:
                percentage = 0

            # Schedule UI update in the main thread
            self.master.after(0, self.update_progress, percentage)

            elapsed_time = time.time() - self.start_time
            download_speed_MBps = d.get('speed', 0) / (1024 * 1024) if d.get('speed') else 0
            # Schedule speed update in the main thread
            self.master.after(0, self.update_speed, download_speed_MBps)

    def update_progress(self, percentage):
        """Update the progress bar in the GUI."""
        self.progress['value'] = percentage

    def update_speed(self, download_speed_MBps):
        """Update the speed label in the GUI."""
        self.speed_label['text'] = f"Download speed: {download_speed_MBps:.2f} MB/sec"

    def pause_download(self):
        """Pause the current download."""
        self.download_active = False
        self.paused = True
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)

    def resume_download(self):
        """Resume the paused download."""
        self.download_active = True
        self.paused = False
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        threading.Thread(target=self.process_queue).start()

    def is_connection_error(self, exception):
        """Check if the given exception is due to a connection error."""
        return isinstance(exception, (socket.error, yt_dlp.utils.DownloadError)) or "Temporary failure" in str(exception)

root = tk.Tk()
my_gui = Downloader(root)
root.mainloop()
