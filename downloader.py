import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import time
import queue
import yt_dlp

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

        # Queue list with video names, size, and status
        self.queue_label = tk.Label(master, text="Queue")
        self.queue_frame = tk.Frame(master)
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=("Video", "Size", "Status"), show="headings")
        self.queue_tree.heading("Video", text="Video")
        self.queue_tree.heading("Size", text="Size")
        self.queue_tree.heading("Status", text="Status")
        self.queue_tree.column("Video", width=300)
        self.queue_tree.column("Size", width=100)
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
        self.current_download_thread = None
        self.start_time = None
        self.paused = False
        self.current_video_title = None  # Track the currently downloading video
        self.save_paths = {}  # Store the path for saving videos by playlist URL

    def start_download_thread(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return

        # Check if it's a playlist or a single video
        if 'playlist' in url:
            self.handle_playlist(url)
        else:
            self.queue_video(url)

        if not self.current_download_thread or not self.current_download_thread.is_alive():
            self.current_download_thread = threading.Thread(target=self.process_queue)
            self.current_download_thread.start()

    def handle_playlist(self, playlist_url):
        """Handles downloading a playlist, adding all videos to the queue."""
        # Prompt for save directory only once per playlist
        if playlist_url not in self.save_paths:
            save_path = filedialog.askdirectory()
            if not save_path:  # User cancelled
                return
            self.save_paths[playlist_url] = save_path  # Store the save path for this playlist

        # Fetch the playlist videos
        with yt_dlp.YoutubeDL() as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            video_urls = [entry['webpage_url'] for entry in playlist_info['entries']]
            
            # Add each video to the queue tree
            for video_url in video_urls:
                self.queue_video(video_url)

    def queue_video(self, video_url):
        """Queues a video for downloading and adds it to the tree view."""
        video_title = self.get_video_title(video_url)
        self.queue_tree.insert('', 'end', values=(video_title, "Pending", "Queued"))
        self.download_queue.put(video_url)  # Queue the video for downloading

    def get_video_title(self, video_url):
        """Fetch the video title."""
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('title', 'Unknown Title')

    def process_queue(self):
        while not self.download_queue.empty():
            if self.paused:
                time.sleep(1)
                continue

            video_url = self.download_queue.get()
            self.handle_video(video_url)

    def handle_video(self, video_url):
        """Handles downloading a single video."""
        playlist_url = self.find_playlist_url(video_url)
        save_path = self.save_paths[playlist_url] if playlist_url else '.'  # Default to current directory

        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{save_path}/%(title)s.%(ext)s',
            'progress_hooks': [self.progress_function],
            'noprogress': False
        }

        # Store the current video title
        self.current_video_title = self.get_video_title(video_url)
        self.update_status(self.current_video_title, "Downloading")  # Set status to downloading
        self.start_time = time.time()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                video_size = info_dict.get('filesize', None)
                if video_size is None:  # If filesize is not available, get the size of the downloaded file
                    video_file_path = ydl.prepare_filename(info_dict)
                    video_size = os.path.getsize(video_file_path)

                video_size_MB = video_size / (1024 * 1024) if video_size is not None else 'Unknown'
                self.update_video_size(self.current_video_title, video_size_MB)
                self.update_status(self.current_video_title, "Downloaded")  # Update to "Downloaded"
        except Exception as e:
            self.update_status(self.current_video_title, "Failed")  # Update to "Failed" on error
            print(f"Error downloading {self.current_video_title}: {e}")

    def find_playlist_url(self, video_url):
        """Find the playlist URL for a given video URL."""
        for playlist_url in self.save_paths:
            if playlist_url in video_url:
                return playlist_url
        return None
    
    def update_video_size(self, video_title, size):
        """Update the size of a video in the queue tree."""
        for row in self.queue_tree.get_children():
            if self.queue_tree.item(row)['values'][0] == video_title:
                # Update the size with MB formatting
                self.queue_tree.item(row, values=(video_title, f"{size:.2f} MB" if isinstance(size, float) else size))  
                break

    def update_status(self, video_title, status):
        """Update the status of a video in the queue tree."""
        for row in self.queue_tree.get_children():
            if self.queue_tree.item(row)['values'][0] == video_title:
                current_size = self.queue_tree.item(row)['values'][1]
                self.queue_tree.item(row, values=(video_title, current_size, status))
                break

    def progress_function(self, d):
        """Progress hook to update the progress bar and download speed."""
        if d['status'] == 'downloading':
            total_size = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            bytes_downloaded = d.get('downloaded_bytes', 0)

            # Calculate percentage
            percentage = (bytes_downloaded / total_size) * 100 if total_size else 0

            # Update size during the download
            if total_size > 0:
                self.update_video_size(self.current_video_title, total_size / (1024 * 1024))

            # Update progress bar
            self.master.after(0, self.update_progress, percentage)

            # Update download speed
            download_speed_MBps = d.get('speed', 0) / (1024 * 1024) if d.get('speed') else 0
            self.master.after(0, self.update_speed, download_speed_MBps)

            # Update the status less frequently to avoid flickering
            if int(percentage) % 10 == 0:  # Update status every 10%
                self.master.after(0, self.update_status, self.current_video_title, "Downloading")

    def update_progress(self, percentage):
        self.progress['value'] = percentage

    def update_speed(self, speed):
        self.speed_label['text'] = f"Download speed: {speed:.2f} MB/sec"

    def pause_download(self):
        self.paused = True
        self.pause_button['state'] = tk.DISABLED
        self.resume_button['state'] = tk.NORMAL

    def resume_download(self):
        self.paused = False
        self.pause_button['state'] = tk.NORMAL
        self.resume_button['state'] = tk.DISABLED

if __name__ == "__main__":
    root = tk.Tk()
    app = Downloader(root)
    root.mainloop()

