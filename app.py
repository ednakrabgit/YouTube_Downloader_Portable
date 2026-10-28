import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp

def get_ffmpeg_path():
    """ค้นหาไฟล์ ffmpeg.exe จากตำแหน่งต่างๆ"""
    # 1. เช็คใน PyInstaller bundle
    if getattr(sys, 'frozen', False):
        bundle_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        bundled = os.path.join(bundle_path, "ffmpeg.exe")
        if os.path.exists(bundled):
            return bundled
        exe_dir = os.path.dirname(sys.executable)
        bundled_next = os.path.join(exe_dir, "ffmpeg.exe")
        if os.path.exists(bundled_next):
            return bundled_next

    # 2. เช็คในโฟลเดอร์ปัจจุบันของโค้ด
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(current_dir, "ffmpeg.exe")
    if os.path.exists(local):
        return local

    # 3. เช็คใน working directory
    cwd_local = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.exists(cwd_local):
        return cwd_local

    # 4. เช็คจาก imageio_ffmpeg ถ้ามี
    try:
        import imageio_ffmpeg
        img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if img_ffmpeg and os.path.exists(img_ffmpeg):
            return img_ffmpeg
    except Exception:
        pass

    # 5. Fallback เป็นคำสั่งใน PATH
    return "ffmpeg"


class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader Portable (MP4 / MP3)")
        self.geometry("740x680")
        self.minsize(620, 520)

        # ตั้งค่าไอคอนและธีมพื้นฐาน
        self._setup_style()

        # ตัวแปรสถานะ
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_dir_var = tk.StringVar(value=default_dir)
        self.format_var = tk.StringVar(value="mp4")  # mp4, mp3, both
        self.quality_var = tk.StringVar(value="best") # best, 1080, 720
        self.is_downloading = False

        self._create_widgets()

    def _setup_style(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista")
        except Exception:
            pass

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill="both", expand=True)

        # --- 1. ส่วนเลือกโฟลเดอร์ปลายทาง ---
        dir_frame = ttk.LabelFrame(main_frame, text=" 📂 โฟลเดอร์ปลายทาง (Save Location) ", padding=8)
        dir_frame.pack(fill="x", pady=(0, 8))

        dir_entry = ttk.Entry(dir_frame, textvariable=self.save_dir_var, font=("Segoe UI", 9))
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        browse_btn = ttk.Button(dir_frame, text="📁 เลือกโฟลเดอร์...", command=self._browse_dir)
        browse_btn.pack(side="left", padx=2)

        open_btn = ttk.Button(dir_frame, text="🔍 เปิดโฟลเดอร์", command=self._open_dir)
        open_btn.pack(side="left", padx=2)

        # --- 2. ส่วนเลือกฟอร์แมตและคุณภาพ ---
        opt_frame = ttk.LabelFrame(main_frame, text=" ⚙️ รูปแบบไฟล์และคุณภาพ (Format & Quality) ", padding=8)
        opt_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(opt_frame, text="ฟอร์แมต:").pack(side="left", padx=(5, 10))
        ttk.Radiobutton(opt_frame, text="🎬 MP4 (วิดีโอ)", value="mp4", variable=self.format_var).pack(side="left", padx=8)
        ttk.Radiobutton(opt_frame, text="🎵 MP3 (เสียง)", value="mp3", variable=self.format_var).pack(side="left", padx=8)
        ttk.Radiobutton(opt_frame, text="📦 ทั้ง 2 แบบ (MP4 + MP3)", value="both", variable=self.format_var).pack(side="left", padx=8)

        # --- 3. กล่องกรอกลิงก์ ---
        link_frame = ttk.LabelFrame(main_frame, text=" 🔗 ลิงก์ YouTube (วางได้หลายลิงก์ บรรทัดละ 1 ลิงก์ หรือลิงก์ Playlist) ", padding=8)
        link_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.links_text = tk.Text(link_frame, height=7, wrap="none", font=("Consolas", 10), undo=True)
        self.links_text.pack(side="left", fill="both", expand=True)

        link_scroll = ttk.Scrollbar(link_frame, orient="vertical", command=self.links_text.yview)
        link_scroll.pack(side="right", fill="y")
        self.links_text.config(yscrollcommand=link_scroll.set)

        # --- 4. สถานะและ Progress Bar ---
        prog_frame = ttk.Frame(main_frame)
        prog_frame.pack(fill="x", pady=(0, 8))

        self.status_label = ttk.Label(prog_frame, text="พร้อมทำงาน", font=("Segoe UI", 9, "bold"), foreground="#0066cc")
        self.status_label.pack(anchor="w", pady=(0, 2))

        self.prog_bar = ttk.Progressbar(prog_frame, mode="determinate")
        self.prog_bar.pack(fill="x")

        # --- 5. กล่อง Log รายงานผล ---
        log_frame = ttk.LabelFrame(main_frame, text=" 📋 บันทึกการดาวน์โหลด (Logs) ", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.log_text = tk.Text(log_frame, height=7, state="disabled", bg="#1e1e1e", fg="#e0e0e0", font=("Consolas", 9), insertbackground="white")
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scroll.set)

        # --- 6. ปุ่มคำสั่งหลักด้านล่าง ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")

        self.start_btn = ttk.Button(btn_frame, text="🚀 เริ่มดาวน์โหลดทั้งหมด (Start Download)", command=self._start_download)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.clear_btn = ttk.Button(btn_frame, text="🧹 ล้างรายการ", command=self._clear_links)
        self.clear_btn.pack(side="left", padx=5)

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if chosen:
            self.save_dir_var.set(chosen)

    def _open_dir(self):
        target = self.save_dir_var.get()
        if os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                messagebox.showerror("ผิดพลาด", f"ไม่สามารถเปิดโฟลเดอร์ได้: {e}")
        else:
            messagebox.showwarning("แจ้งเตือน", "โฟลเดอร์นี้ยังไม่มีอยู่จริง")

    def _clear_links(self):
        if not self.is_downloading:
            self.links_text.delete("1.0", tk.END)

    def _log(self, text):
        def _update():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.after(0, _update)

    def _set_status(self, text, color="#0066cc"):
        def _update():
            self.status_label.config(text=text, foreground=color)
        self.after(0, _update)

    def _set_progress(self, val):
        def _update():
            self.prog_bar["value"] = val
        self.after(0, _update)

    def _start_download(self):
        if self.is_downloading:
            return

        raw_links = self.links_text.get("1.0", tk.END).strip().splitlines()
        links = [l.strip() for l in raw_links if l.strip() and not l.strip().startswith("#")]

        if not links:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกลิงก์ YouTube อย่างน้อย 1 ลิงก์")
            return

        save_dir = self.save_dir_var.get().strip()
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("เกิดข้อผิดพลาด", f"ไม่สามารถสร้างโฟลเดอร์ปลายทางได้: {e}")
                return

        self.is_downloading = True
        self.start_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self._set_progress(0)

        threading.Thread(target=self._download_worker, args=(links, save_dir, self.format_var.get()), daemon=True).start()

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            if total > 0:
                percent = (downloaded / total) * 100
                self._set_progress(percent)
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                self._set_status(f"กำลังดาวน์โหลด: {percent:.1f}% | ความเร็ว: {speed} | เหลืออีก: {eta}")

    def _download_worker(self, links, save_dir, fmt_choice):
        ffmpeg_bin = get_ffmpeg_path()
        ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.isabs(ffmpeg_bin) else None

        total_links = len(links)
        success_count = 0
        error_count = 0

        self._log(f"==================================================")
        self._log(f"🚀 เริ่มต้นการดาวน์โหลดทั้งหมด {total_links} รายการ")
        self._log(f"📂 โฟลเดอร์ปลายทาง: {save_dir}")
        self._log(f"⚙️ ฟอร์แมตที่เลือก: {fmt_choice.upper()}")
        if ffmpeg_bin:
            self._log(f"🔧 เครื่องมือ FFmpeg: {ffmpeg_bin}")
        self._log(f"==================================================")

        for idx, url in enumerate(links, 1):
            self._set_status(f"รายการที่ {idx}/{total_links}: กำลังดึงข้อมูลและดาวน์โหลด...")
            self._set_progress(0)
            self._log(f"\n[{idx}/{total_links}] URL: {url}")

            # กำหนด Options ของ yt-dlp
            out_tmpl = os.path.join(save_dir, '%(title)s.%(ext)s')

            # โหมด 1: MP4 อย่างเดียว
            if fmt_choice == "mp4":
                ydl_opts = {
                    'outtmpl': out_tmpl,
                    'progress_hooks': [self._progress_hook],
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                    'quiet': True,
                    'no_warnings': True,
                }
                if ffmpeg_dir:
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    self._log(f"  ✅ ดาวน์โหลด MP4 สำเร็จ")
                    success_count += 1
                except Exception as e:
                    self._log(f"  ❌ ล้มเหลว: {e}")
                    error_count += 1

            # โหมด 2: MP3 อย่างเดียว
            elif fmt_choice == "mp3":
                ydl_opts = {
                    'outtmpl': out_tmpl,
                    'progress_hooks': [self._progress_hook],
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True,
                    'no_warnings': True,
                }
                if ffmpeg_dir:
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    self._log(f"  ✅ ดาวน์โหลดและแปลง MP3 สำเร็จ")
                    success_count += 1
                except Exception as e:
                    self._log(f"  ❌ ล้มเหลว: {e}")
                    error_count += 1

            # โหมด 3: ทั้ง 2 แบบ (MP4 + MP3)
            elif fmt_choice == "both":
                downloaded_file = None
                def finished_hook(d):
                    nonlocal downloaded_file
                    if d['status'] == 'finished':
                        downloaded_file = d.get('filename')

                # ดาวน์โหลด MP4 ก่อน
                ydl_opts_mp4 = {
                    'outtmpl': out_tmpl,
                    'progress_hooks': [self._progress_hook, finished_hook],
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                    'quiet': True,
                    'no_warnings': True,
                }
                if ffmpeg_dir:
                    ydl_opts_mp4['ffmpeg_location'] = ffmpeg_dir

                mp4_ok = False
                try:
                    with yt_dlp.YoutubeDL(ydl_opts_mp4) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if not downloaded_file and info:
                            downloaded_file = ydl.prepare_filename(info)
                            base, _ = os.path.splitext(downloaded_file)
                            downloaded_file = base + ".mp4"

                    self._log(f"  ✅ 1/2 ดาวน์โหลด MP4 สำเร็จ")
                    mp4_ok = True
                except Exception as e:
                    self._log(f"  ❌ MP4 ล้มเหลว: {e}")

                # แตกไฟล์ MP3 ต่อทันที (ถ้ามี ffmpeg จะแปลงจาก MP4 ตรงๆ ไม่ต้องโหลดซ้ำ)
                mp3_ok = False
                if mp4_ok and downloaded_file and os.path.exists(downloaded_file) and ffmpeg_bin:
                    base_name, _ = os.path.splitext(downloaded_file)
                    mp3_path = base_name + ".mp3"
                    self._set_status(f"รายการที่ {idx}/{total_links}: กำลังแปลง MP3 จาก MP4...")
                    self._log(f"  ⚡ แปลงเป็น MP3 โดยตรงจาก MP4...")
                    try:
                        cmd = [ffmpeg_bin, "-y", "-i", downloaded_file, "-vn", "-c:a", "libmp3lame", "-q:a", "2", mp3_path]
                        startupinfo = None
                        if sys.platform == "win32":
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        subprocess.run(cmd, startupinfo=startupinfo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        self._log(f"  ✅ 2/2 แปลง MP3 สำเร็จ")
                        mp3_ok = True
                    except Exception as e:
                        self._log(f"  ⚠️ แปลง MP3 ตรงขัดข้อง กำลังดาวน์โหลดแยก: {e}")

                # Fallback ถ้าแปลงตรงไม่ผ่าน ให้ yt-dlp ดาวน์โหลด MP3 แยก
                if not mp3_ok:
                    ydl_opts_mp3 = {
                        'outtmpl': out_tmpl,
                        'progress_hooks': [self._progress_hook],
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'quiet': True,
                        'no_warnings': True,
                    }
                    if ffmpeg_dir:
                        ydl_opts_mp3['ffmpeg_location'] = ffmpeg_dir
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts_mp3) as ydl:
                            ydl.download([url])
                        self._log(f"  ✅ 2/2 ดาวน์โหลด MP3 สำเร็จ")
                        mp3_ok = True
                    except Exception as e:
                        self._log(f"  ❌ MP3 ล้มเหลว: {e}")

                if mp4_ok or mp3_ok:
                    success_count += 1
                else:
                    error_count += 1

        self._set_progress(100)
        self._set_status(f"เสร็จสิ้น! สำเร็จ: {success_count}, ล้มเหลว: {error_count}", color="#008800" if error_count == 0 else "#cc6600")

        self._log(f"\n==================================================")
        self._log(f"🎉 สรุปผลการดาวน์โหลด:")
        self._log(f"  - สำเร็จ: {success_count} รายการ")
        self._log(f"  - ล้มเหลว: {error_count} รายการ")
        self._log(f"  - โฟลเดอร์: {save_dir}")
        self._log(f"==================================================")

        def _finish_ui():
            self.is_downloading = False
            self.start_btn.config(state="normal")
            self.clear_btn.config(state="normal")
            messagebox.showinfo("เสร็จสิ้น", f"ดาวน์โหลดเสร็จสมบูรณ์!\n\nสำเร็จ: {success_count} รายการ\nล้มเหลว: {error_count} รายการ\n\nบันทึกไว้ที่: {save_dir}")

        self.after(0, _finish_ui)


if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()

