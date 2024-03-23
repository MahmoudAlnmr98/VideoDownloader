import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pytube import YouTube, Playlist, exceptions
import threading
import time
import queue

class AutoScrollbar(ttk.Scrollbar):
    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        ttk.Scrollbar.set(self, low, high)

class Downloader:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Downloader")

        self.url_label = tk.Label(master, text="URL")
        self.url_entry = tk.Entry(master)
        self.download_button = tk.Button(master, text="Download", command=self.start_download_thread)
        self.progress = ttk.Progressbar(master, length=200)
        self.queue_label = tk.Label(master, text="Queue")
        self.queue_frame = tk.Frame(master)
        self.queue_listbox = tk.Listbox(self.queue_frame)
        self.scrollbar = AutoScrollbar(self.queue_frame, orient='vertical', command=self.queue_listbox.yview)
        self.queue_listbox.configure(yscrollcommand=self.scrollbar.set)
        self.speed_label = tk.Label(master, text="Download speed: 0 MB/sec")

        self.url_label.pack()
        self.url_entry.pack()
        self.download_button.pack()
        self.progress.pack()
        self.queue_label.pack()
        self.queue_frame.pack(fill='both', expand=True)
        self.queue_listbox.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        self.speed_label.pack()

        self.download_queue = queue.Queue()
        self.current_download = None
        self.start_time = None
        self.last_update_time = None
        self.last_bytes_downloaded = 0

    def start_download_thread(self):
        url = self.url_entry.get()
        self.download_queue.put(url)

        if not self.current_download:
            threading.Thread(target=self.download).start()

    def progress_function(self, stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining

        percentage = (bytes_downloaded / total_size) * 100
        self.progress['value'] = percentage
        self.master.update_idletasks()

        if self.last_update_time is not None:
            elapsed_time = time.time() - self.last_update_time
            download_speed = (bytes_downloaded - self.last_bytes_downloaded) / elapsed_time
            download_speed_MBps = download_speed / (1024 * 1024)  # convert to MB/sec
            self.speed_label['text'] = f"Download speed: {download_speed_MBps:.2f} MB/sec"

        self.last_update_time = time.time()
        self.last_bytes_downloaded = bytes_downloaded

    def download(self):
        while not self.download_queue.empty():
            url = self.download_queue.get()
            self.current_download = url

            try:
                save_path = filedialog.askdirectory()
                if 'playlist' in url:
                    playlist = Playlist(url)
                    for video_url in playlist.video_urls:
                        youtube = YouTube(video_url, on_progress_callback=self.progress_function)
                        video = youtube.streams.get_highest_resolution()
                        self.queue_listbox.insert(tk.END, f"{youtube.title} - queued")
                        self.start_time = time.time()
                        video.download(save_path)
                        self.queue_listbox.delete(0)
                        self.queue_listbox.insert(tk.END, f"{youtube.title} - downloaded")
                else:
                    youtube = YouTube(url, on_progress_callback=self.progress_function)
                    video = youtube.streams.get_highest_resolution()
                    self.start_time = time.time()
                    video.download(save_path)
                    self.queue_listbox.delete(0)
                    self.queue_listbox.insert(tk.END, f"{youtube.title} - downloaded")
            except exceptions.PytubeError as e:
                messagebox.showerror("Error", f"An error occurred while downloading {url}: {str(e)}")

            self.current_download = None

root = tk.Tk()
my_gui = Downloader(root)
root.mainloop()