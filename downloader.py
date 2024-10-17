import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, StringVar
import yt_dlp
import threading

class YouTubeDownloader:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Video Downloader")
        master.geometry("800x600")
        master.configure(bg="#f0f0f0")

        # Title Label
        self.title_label = tk.Label(master, text="YouTube Video Downloader", font=("Helvetica", 16), bg="#f0f0f0")
        self.title_label.pack(pady=10)

        # URL Input Frame
        self.url_frame = tk.Frame(master, bg="#f0f0f0")
        self.url_frame.pack(pady=10, padx=20, fill="x")

        self.url_label = tk.Label(self.url_frame, text="Enter Video/Playlist URL:", bg="#f0f0f0")
        self.url_label.grid(row=0, column=0, sticky='e')

        self.url_entry = tk.Entry(self.url_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=10)

        # Quality Selection
        self.quality_label = tk.Label(self.url_frame, text="Select Video Quality:", bg="#f0f0f0")
        self.quality_label.grid(row=1, column=0, sticky='e')

        self.quality_var = StringVar(value='best')
        self.quality_dropdown = ttk.Combobox(self.url_frame, textvariable=self.quality_var, width=17)
        self.quality_dropdown['values'] = ('best', '720p', '1080p', '144p', '360p')
        self.quality_dropdown.grid(row=1, column=1, padx=10)

        # Format Selection
        self.format_label = tk.Label(self.url_frame, text="Select Download Format:", bg="#f0f0f0")
        self.format_label.grid(row=2, column=0, sticky='e')

        self.format_var = StringVar(value='mp4')
        self.format_dropdown = ttk.Combobox(self.url_frame, textvariable=self.format_var, width=17)
        self.format_dropdown['values'] = ('mp4', 'mp3', 'mkv', 'webm')
        self.format_dropdown.grid(row=2, column=1, padx=10)

        # Subtitles Option
        self.subtitles_var = tk.BooleanVar()
        self.subtitles_checkbox = tk.Checkbutton(self.url_frame, text="Download Subtitles", variable=self.subtitles_var, bg="#f0f0f0")
        self.subtitles_checkbox.grid(row=3, columnspan=2, pady=5)

        # Button Frame
        self.button_frame = tk.Frame(master, bg="#f0f0f0")
        self.button_frame.pack(pady=10)

        # Download Button
        self.download_button = tk.Button(self.button_frame, text="Download", command=self.start_download_thread, bg="#4CAF50", fg="white", relief="raised", font=("Helvetica", 12))
        self.download_button.pack(side=tk.LEFT, padx=5)

        # Folder Selection Button
        self.folder_button = tk.Button(self.button_frame, text="Select Download Folder", command=self.select_folder, bg="#2196F3", fg="white", relief="raised")
        self.folder_button.pack(side=tk.LEFT, padx=5)

        # Progress Bar
        self.progress_label = tk.Label(master, text="", bg="#f0f0f0")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(master, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Video List Section
        self.video_list_label = tk.Label(master, text="Playlist Videos: 0", bg="#f0f0f0", font=("Helvetica", 14))
        self.video_list_label.pack()

        self.video_list_frame = tk.Frame(master)
        self.video_list_frame.pack(pady=10)

        # Treeview for displaying video details
        self.video_tree = ttk.Treeview(self.video_list_frame, columns=("Title", "Size (MB)", "Status", "Speed"), show="headings")
        self.video_tree.heading("Title", text="Video Title")
        self.video_tree.heading("Size (MB)", text="Size (MB)")
        self.video_tree.heading("Status", text="Status")
        self.video_tree.heading("Speed", text="Speed (MB/s)")
        self.video_tree.pack(side=tk.LEFT, fill=tk.BOTH)

        self.scrollbar = ttk.Scrollbar(self.video_list_frame, orient="vertical", command=self.video_tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.video_tree.configure(yscrollcommand=self.scrollbar.set)

        self.download_folder = ""
        self.video_entries = []

        # Handle window closing
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def select_folder(self):
        self.download_folder = filedialog.askdirectory()
        if self.download_folder:
            self.progress_label.config(text=f"Download folder: {self.download_folder}")

    def start_download_thread(self):
        threading.Thread(target=self.download_video).start()  # Start download in a separate thread

    def download_video(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return

        if not self.download_folder:
            messagebox.showerror("Error", "Please select a download folder.")
            return

        self.progress_label.config(text="Fetching video information...")
        self.video_tree.delete(*self.video_tree.get_children())  # Clear previous video list
        self.video_entries.clear()  # Clear previous entries

        # Fetch video information
        try:
            ydl_opts = {
                'extract_flat': True,  # Extract video information without downloading
                'noplaylist': False,   # Ensure we get all videos in the playlist
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                total_videos = len(info_dict['entries'])
                self.video_list_label.config(text=f"Playlist Videos: {total_videos}")

                # List video titles and set initial status and size
                for entry in info_dict['entries']:
                    title = entry['title']
                    self.video_tree.insert("", "end", values=(title, "Unknown", "Ready", "0.00"))
                    self.video_entries.append({"title": title, "size": "Unknown", "status": "Ready"})

                # Start downloading
                self.start_download(info_dict['entries'])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch playlist: {str(e)}")

    def start_download(self, entries):
        total_size = 0

        for entry in entries:
            video_url = entry['url']
            options = {
                'format': self.format_var.get(),
                'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                'progress_hooks': [self.create_progress_hook(entry)],
                'subtitleslangs': ['en'] if self.subtitles_var.get() else None,
            }

            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    video_info = ydl.extract_info(video_url, download=True)  # Start the download
                    total_bytes = video_info.get('filesize', None) or 0  # Ensure that total_bytes is not None
                    total_size += total_bytes  # Accumulate total size for display

                    # Update the corresponding video status and size in the Treeview
                    for item in self.video_tree.get_children():
                        video_title = self.video_tree.item(item, "values")[0]
                        if video_title == entry['title']:
                            size_mb = (total_bytes / (1024 * 1024)) if total_bytes > 0 else 'Unknown'  # Convert to MB
                            self.video_tree.item(item, values=(video_title, f"{size_mb:.2f}" if isinstance(size_mb, float) else size_mb, "Finished", "0.00"))

            except Exception as e:
                messagebox.showerror("Error", f"Failed to download: {str(e)}")

        # Display total size of all downloaded videos
        total_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
        self.progress_label.config(text=f"All downloads completed! Total size: {total_size_mb:.2f} MB")

    def create_progress_hook(self, entry):
        def progress_hook(d):
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)

                # Convert bytes to MB
                total_size_mb = total_bytes / (1024 * 1024) if total_bytes else "Unknown"
                downloaded_size_mb = downloaded_bytes / (1024 * 1024) if downloaded_bytes else 0
                speed_mb = speed / (1024 * 1024) if speed else 0

                # Update the progress bar
                progress_percent = (downloaded_bytes / total_bytes) * 100 if total_bytes else 0
                self.progress_bar["value"] = progress_percent

                # Update the corresponding video entry in the Treeview
                for item in self.video_tree.get_children():
                    video_title = self.video_tree.item(item, "values")[0]
                    if video_title == entry['title']:
                        self.video_tree.item(item, values=(video_title, f"{total_size_mb:.2f} MB", "Downloading", f"{speed_mb:.2f} MB/s"))

            elif d['status'] == 'finished':
                total_bytes = d.get('total_bytes', 0)
                total_size_mb = total_bytes / (1024 * 1024) if total_bytes else "Unknown"
                
                # Update the video as finished with final size
                for item in self.video_tree.get_children():
                    video_title = self.video_tree.item(item, "values")[0]
                    if video_title == entry['title']:
                        self.video_tree.item(item, values=(video_title, f"{total_size_mb:.2f} MB", "Finished", "0.00 MB/s"))

        return progress_hook


    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
