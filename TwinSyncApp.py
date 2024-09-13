#v1.3
#now the volume function finally works
#improved gui and threading
#the new standard version



import tkinter as tk
from tkinter import ttk, filedialog
import pyaudio
import wave
import threading
import queue
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from comtypes import CoInitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import os

CoInitialize()

class TwinsyncUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Twinsync Media Player")
        self.master.geometry("600x400")
        self.master.resizable(False, False)
        self.master.configure(bg="#121212")

        self.volume_control = self.initialize_volume_control()  # Initialize volume_control

        self.create_widgets()

        self.is_playing = False
        self.paused = False
        self.file_info_label = tk.Label(self.master, text="", font=("Helvetica", 10), fg="white", bg="#121212")
        self.file_info_label.pack(pady=10)

        self.stream1 = None
        self.stream2 = None

        self.queue = queue.Queue()

    def initialize_volume_control(self):
        devices = AudioUtilities.GetSpeakers()
        return cast(devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume))

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')

        header_label = tk.Label(self.master, text="Twinsync Media Player", font=("Helvetica", 20, "bold"), fg="white", bg="#121212")
        header_label.pack(pady=10)

        file_frame = tk.Frame(self.master, bg="#121212")
        file_frame.pack(pady=20)

        self.entry = ttk.Entry(file_frame, width=40, font=("Helvetica", 12), style="TEntry")
        self.entry.grid(row=0, column=0, padx=10)

        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file, style="Accent.TButton")
        browse_button.grid(row=0, column=1, padx=10)

        controls_frame = tk.Frame(self.master, bg="#121212")
        controls_frame.pack(pady=20)

        play_button = ttk.Button(controls_frame, text="Play", command=self.toggle_playback, style="Accent.TButton")
        play_button.grid(row=0, column=0, padx=10)

        stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop_playback, style="Accent.TButton")
        stop_button.grid(row=0, column=1, padx=10)

        pause_resume_frame = tk.Frame(controls_frame, bg="#121212")
        pause_resume_frame.grid(row=0, column=2, padx=10)

        pause_button = ttk.Button(pause_resume_frame, text="Pause", command=self.pause_playback, style="Accent.TButton")
        pause_button.grid(row=0, column=0)

        resume_button = ttk.Button(pause_resume_frame, text="Resume", command=self.resume_playback, style="Accent.TButton")
        resume_button.grid(row=0, column=1)

        volume_label = tk.Label(self.master, text="Volume:", font=("Helvetica", 12), fg="white", bg="#121212")
        volume_label.pack(pady=10)

        self.volume_scale = ttk.Scale(self.master, from_=0, to=100, orient="horizontal", command=self.set_volume, style="TScale")
        self.volume_scale.set(int(self.volume_control.GetMasterVolumeLevelScalar() * 100))  # Set initial volume
        self.volume_scale.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=500, mode="determinate", style="TProgressbar")
        self.progress_bar.pack(pady=10)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if file_path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, file_path)
            self.update_file_info(file_path)

    def toggle_playback(self):
        if self.is_playing:
            if self.paused:
                self.resume_playback()
            else:
                self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        path = self.entry.get()
        try:
            self.validate_path(path)

            playback_thread = threading.Thread(target=self.play_audio, args=(path,))
            playback_thread.start()

        except FileNotFoundError:
            self.handle_error("File not found.")
        except ValueError:
            self.handle_error("Not a WAV file.")
        except Exception as e:
            self.handle_error(f"An error occurred: {str(e)}")

    def stop_playback(self):
        self.is_playing = False
        self.paused = False

    def pause_playback(self):
        self.paused = True

    def resume_playback(self):
        self.paused = False

    def validate_path(self, path):
        if not path.endswith(".wav"):
            raise ValueError("Not a WAV file.")
        if not os.path.isfile(path):
            raise FileNotFoundError("File not found.")

    def play_audio(self, path):
        try:
            self.is_playing = True
            self.paused = False
            with wave.open(path, "rb") as wav_file:
                format = pyaudio.get_format_from_width(wav_file.getsampwidth())
                channels = wav_file.getnchannels()
                rate = wav_file.getframerate()

                p = pyaudio.PyAudio()
                output_devices = [i for i in range(p.get_device_count()) if p.get_device_info_by_index(i)['maxOutputChannels'] > 0]

                if len(output_devices) < 2:
                    raise ValueError("Not enough output devices detected.")

                self.stream1 = p.open(format=format, channels=channels, rate=rate, output=True, output_device_index=output_devices[0])
                self.stream2 = p.open(format=format, channels=channels, rate=rate, output=True, output_device_index=output_devices[1])

                chunk_size = 1024
                data = wav_file.readframes(chunk_size)
                total_frames = wav_file.getnframes()

                while data and self.is_playing:
                    if not self.paused:
                        self.stream1.write(data)
                        self.stream2.write(data)

                        # Update progress bar
                        current_frame = wav_file.tell()
                        progress = (current_frame / total_frames) * 100
                        self.progress_bar["value"] = progress

                        data = wav_file.readframes(chunk_size)

                self.stream1.stop_stream()
                self.stream1.close()
                self.stream2.stop_stream()
                self.stream2.close()
                p.terminate()

        except Exception as e:
            self.handle_error(f"An error occurred during playback: {str(e)}")

        finally:
            self.is_playing = False
            # Reset progress bar after playback
            self.progress_bar["value"] = 0

    def set_volume(self, value):
        # Set the system volume when the scale is adjusted
        volume_level = float(value) / 100.0
        self.volume_control.SetMasterVolumeLevelScalar(volume_level, None)

    def handle_error(self, message):
        self.queue.put(lambda: self.file_info_label.config(text=f"Error: {message}", fg="#FF5252", bg="#121212"))
        self.master.after(0, self.process_queue)

    def update_file_info(self, file_path):
        try:
            with wave.open(file_path, "rb") as wav_file:
                duration = wav_file.getnframes() / float(wav_file.getframerate())
                minutes, seconds = divmod(duration, 60)
                info_text = f"Duration: {int(minutes)}:{int(seconds):02d} minutes, Sample Rate: {wav_file.getframerate()} Hz, Channels: {wav_file.getnchannels()}"
                self.queue.put(lambda: self.file_info_label.config(text=info_text, fg="#69F0AE", bg="#121212"))
                self.master.after(0, self.process_queue)

        except Exception as e:
            self.queue.put(lambda: self.file_info_label.config(text=f"Error getting file info: {str(e)}", fg="#FF5252", bg="#121212"))
            self.master.after(0, self.process_queue)

    def process_queue(self):
        while not self.queue.empty():
            self.queue.get()()

        self.master.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = TwinsyncUI(root)
    root.mainloop()
