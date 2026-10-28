import os
import sys
import time
import datetime
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp

def get_ffmpeg_path():
    """ค้นหาไฟล์ ffmpeg.exe จากตำแหน่งต่างๆ"""
    if getattr(sys, 'frozen', False):
        bundle_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        bundled = os.path.join(bundle_path, "ffmpeg.exe")
        if os.path.exists(bundled):
            return bundled
        exe_dir = os.path.dirname(sys.executable)
        bundled_next = os.path.join(exe_dir, "ffmpeg.exe")
        if os.path.exists(bundled_next):
            return bundled_next

    current_dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(current_dir, "ffmpeg.exe")
    if os.path.exists(local):
        return local

    cwd_local = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.exists(cwd_local):
        return cwd_local

    try:
        import imageio_ffmpeg
        img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if img_ffmpeg and os.path.exists(img_ffmpeg):
            return img_ffmpeg
    except Exception:
        pass

    return "ffmpeg"


class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader Portable (MP4 / MP3)")
        self.geometry("780x750")
        self.minsize(680, 580)

        self._setup_style()

        # ตัวแปรสถานะ
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_dir_var = tk.StringVar(value=default_dir)
        self.format_var = tk.StringVar(value="mp4")      # mp4, mp3, both
        self.ipad_compat_var = tk.BooleanVar(value=True) # โหมด iPad mini 1 / อุปกรณ์รุ่นเก่า
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

        dir_input_frame = ttk.Frame(dir_frame)
        dir_input_frame.pack(fill="x")

        dir_entry = ttk.Entry(dir_input_frame, textvariable=self.save_dir_var, font=("Segoe UI", 9))
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        browse_btn = ttk.Button(dir_input_frame, text="📁 เลือกโฟลเดอร์...", command=self._browse_dir)
        browse_btn.pack(side="left", padx=2)

        open_btn = ttk.Button(dir_input_frame, text="🔍 เปิดโฟลเดอร์", command=self._open_dir)
        open_btn.pack(side="left", padx=2)

        ttk.Label(
            dir_frame,
            text="* สร้างโฟลเดอร์ย่อย 'mp3' สำหรับไฟล์เสียง และ 'mp4' สำหรับไฟล์วิดีโอ ให้อัตโนมัติ",
            font=("Segoe UI", 8),
            foreground="#555555"
        ).pack(anchor="w", pady=(3, 0))

        # --- 2. ส่วนเลือกฟอร์แมตและความเข้ากันได้ ---
        opt_frame = ttk.LabelFrame(main_frame, text=" ⚙️ รูปแบบไฟล์และความเข้ากันได้ (Format & Compatibility) ", padding=8)
        opt_frame.pack(fill="x", pady=(0, 8))

        row1 = ttk.Frame(opt_frame)
        row1.pack(fill="x", pady=(0, 4))
        ttk.Label(row1, text="ฟอร์แมต:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(5, 10))
        ttk.Radiobutton(row1, text="🎬 MP4 (วิดีโอ)", value="mp4", variable=self.format_var).pack(side="left", padx=8)
        ttk.Radiobutton(row1, text="🎵 MP3 (เสียง)", value="mp3", variable=self.format_var).pack(side="left", padx=8)
        ttk.Radiobutton(row1, text="📦 ทั้ง 2 แบบ (MP4 + MP3)", value="both", variable=self.format_var).pack(side="left", padx=8)

        row2 = ttk.Frame(opt_frame)
        row2.pack(fill="x", pady=(4, 0))
        ipad_chk = ttk.Checkbutton(
            row2, 
            text="🍏 โหมดรองรับ iPad mini 1 / อุปกรณ์รุ่นเก่า (บังคับ H.264 / 30fps / yuv420p เล่นได้ 100%)", 
            variable=self.ipad_compat_var
        )
        ipad_chk.pack(side="left", padx=(5, 10))

        # --- 3. กล่องกรอกลิงก์ ---
        link_frame = ttk.LabelFrame(main_frame, text=" 🔗 ลิงก์ YouTube (วางได้หลายลิงก์ บรรทัดละ 1 ลิงก์ หรือลิงก์ Playlist) ", padding=8)
        link_frame.pack(fill="both", expand=True, pady=(0, 8))

        text_container = ttk.Frame(link_frame)
        text_container.pack(fill="both", expand=True)

        self.links_text = tk.Text(text_container, height=7, wrap="none", font=("Consolas", 10), undo=True)
        self.links_text.pack(side="left", fill="both", expand=True)

        link_scroll = ttk.Scrollbar(text_container, orient="vertical", command=self.links_text.yview)
        link_scroll.pack(side="right", fill="y")
        self.links_text.config(yscrollcommand=link_scroll.set)

        self.count_label = ttk.Label(link_frame, text="🎵 ตรวจพบ: 0 เพลง / รายการ (วางลิงก์ได้หลายบรรทัด หรือลิงก์ Playlist)", font=("Segoe UI", 9, "bold"), foreground="#666666")
        self.count_label.pack(anchor="w", pady=(4, 0))

        self.links_text.bind("<KeyRelease>", self._update_link_count)
        self.links_text.bind("<<Paste>>", lambda e: self.after(50, self._update_link_count))
        self.links_text.bind("<FocusOut>", self._update_link_count)

        # --- 4. สถานะและ Progress Bar ---
        prog_frame = ttk.LabelFrame(main_frame, text=" 📊 สถานะและความคืบหน้า (Progress) ", padding=8)
        prog_frame.pack(fill="x", pady=(0, 8))

        self.status_label = ttk.Label(prog_frame, text="พร้อมทำงาน", font=("Segoe UI", 9, "bold"), foreground="#0066cc")
        self.status_label.pack(anchor="w", pady=(0, 2))

        self.prog_bar = ttk.Progressbar(prog_frame, mode="determinate")
        self.prog_bar.pack(fill="x", pady=(2, 4))

        self.eta_label = ttk.Label(prog_frame, text="⏳ รอเริ่มต้นดาวน์โหลด (วางลิงก์แล้วกดเริ่มดาวน์โหลด)", font=("Segoe UI", 8), foreground="#555555")
        self.eta_label.pack(anchor="w")

        # --- 5. กล่อง Log รายงานผล ---
        log_frame = ttk.LabelFrame(main_frame, text=" 📋 บันทึกการทำงาน (Logs) ", padding=8)
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

        self.convert_btn = ttk.Button(btn_frame, text="🍏 ซ่อมไฟล์ MP4 เดิมให้เล่นบน iPad ได้", command=self._convert_existing_for_ipad)
        self.convert_btn.pack(side="left", padx=5)

        self.clear_btn = ttk.Button(btn_frame, text="🧹 ล้างรายการ", command=self._clear_links)
        self.clear_btn.pack(side="left", padx=5)

        self._update_link_count()

    def _ensure_subfolders(self, base_dir):
        """สร้างโฟลเดอร์ย่อย mp3 และ mp4 อัตโนมัติ"""
        mp3_dir = os.path.join(base_dir, "mp3")
        mp4_dir = os.path.join(base_dir, "mp4")
        try:
            os.makedirs(mp3_dir, exist_ok=True)
            os.makedirs(mp4_dir, exist_ok=True)
        except Exception as e:
            self._log(f"⚠️ ไม่สามารถสร้างโฟลเดอร์ย่อย mp3/mp4: {e}")
        return mp3_dir, mp4_dir

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if chosen:
            self.save_dir_var.set(chosen)
            mp3_dir, mp4_dir = self._ensure_subfolders(chosen)
            self._log(f"📁 เลือกโฟลเดอร์ปลายทาง: {chosen}")
            self._log(f"  ├─ 🎵 โฟลเดอร์ MP3: {mp3_dir}")
            self._log(f"  └─ 🎬 โฟลเดอร์ MP4: {mp4_dir}")

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
            self._update_link_count()

    def _update_link_count(self, event=None):
        try:
            raw_links = self.links_text.get("1.0", tk.END).strip().splitlines()
            valid_links = [l.strip() for l in raw_links if l.strip() and not l.strip().startswith("#")]
            count = len(valid_links)
            if count == 0:
                self.count_label.config(text="🎵 ตรวจพบ: 0 เพลง / รายการ (วางลิงก์ได้หลายบรรทัด หรือลิงก์ Playlist)", foreground="#666666")
            else:
                self.count_label.config(text=f"🎵 ตรวจพบทั้งหมด: {count} เพลง / รายการ พร้อมดาวน์โหลด", foreground="#0066cc")
        except Exception:
            pass

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

    def _set_eta(self, text):
        def _update():
            self.eta_label.config(text=text)
        self.after(0, _update)

    def _set_progress(self, val):
        def _update():
            self.prog_bar["value"] = val
        self.after(0, _update)

    def _calc_time_estimates(self, cur_num, total_num, percent, song_eta_sec):
        """คำนวณเวลาที่เหลือโดยประมาณ และเวลาที่คาดว่าจะเสร็จสิ้น"""
        now = datetime.datetime.now()
        start_t = getattr(self, 'download_start_time', None)
        if not start_t:
            return "กำลังคำนวณ...", "กำลังคำนวณ..."

        elapsed = time.time() - start_t
        p = max(0.0, min(100.0, percent)) / 100.0

        completed_units = (cur_num - 1) + p
        remaining_units = max(0.0, total_num - completed_units)

        total_eta = None
        if total_num <= 1:
            if song_eta_sec is not None and song_eta_sec >= 0:
                total_eta = song_eta_sec
            elif completed_units > 0.05 and elapsed > 2.0:
                rate = completed_units / elapsed
                total_eta = remaining_units / rate
        else:
            if completed_units > 0.1 and elapsed > 2.0:
                rate = completed_units / elapsed
                total_eta = remaining_units / rate
            elif song_eta_sec is not None and song_eta_sec >= 0:
                total_eta = song_eta_sec + ((total_num - cur_num) * max(20, song_eta_sec))

        if total_eta is not None and total_eta >= 0:
            total_sec = int(total_eta)
            if total_sec < 60:
                rem_str = f"{total_sec} วินาที"
            else:
                mins, secs = divmod(total_sec, 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    rem_str = f"{hours} ชม. {mins} นาที"
                elif secs > 0:
                    rem_str = f"{mins} นาที {secs} วินาที"
                else:
                    rem_str = f"{mins} นาที"

            finish_time = now + datetime.timedelta(seconds=total_sec)
            finish_str = finish_time.strftime("%H:%M:%S น.")
            return rem_str, finish_str

        return "กำลังคำนวณ...", "กำลังคำนวณ..."

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

        self._ensure_subfolders(save_dir)

        self.is_downloading = True
        self.start_btn.config(state="disabled")
        self.convert_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self._set_progress(0)
        self._set_status(f"🚀 เตรียมการดาวน์โหลดทั้งหมด {len(links)} เพลง / รายการ...")
        self._set_eta("⏳ กำลังเริ่มกระบวนการ...")

        threading.Thread(
            target=self._download_worker, 
            args=(links, save_dir, self.format_var.get(), self.ipad_compat_var.get()), 
            daemon=True
        ).start()

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            self._set_progress(percent)
            speed = d.get('_speed_str', 'N/A')
            song_eta_sec = d.get('eta')

            pl_count = d.get('playlist_count')
            pl_idx = d.get('playlist_index')
            if pl_count and pl_count > 1:
                cur_num = pl_idx or self.current_idx
                tot_num = pl_count
            else:
                cur_num = self.current_idx
                tot_num = getattr(self, 'total_songs', 1)

            rem_str, finish_str = self._calc_time_estimates(cur_num, tot_num, percent, song_eta_sec)
            self._set_status(f"🎵 กำลังดาวน์โหลดเพลงที่ {cur_num}/{tot_num} ({percent:.1f}%)")
            self._set_eta(f"⚡ ความเร็ว: {speed}  |  ⏳ เหลืออีกประมาณ: {rem_str}  |  🏁 คาดว่าจะเสร็จ: {finish_str}")

    def _post_process_for_ipad(self, filepath, ffmpeg_bin):
        """แปลงไฟล์ให้รองรับ iPad mini 1 (Apple A5: H.264 High 4.1 / yuv420p / <=30fps / AAC / FastStart)"""
        if not os.path.exists(filepath):
            return filepath

        base, ext = os.path.splitext(filepath)
        temp_out = base + "_ipad_temp.mp4"
        cmd = [
            ffmpeg_bin, "-y", "-i", filepath,
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-vf", "scale='min(1920,iw)':-2",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-movflags", "+faststart",
            temp_out
        ]

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self._set_status("กำลังแปลงไฟล์ให้รองรับ iPad mini 1 (H.264 / 30fps)...")
            self._log(f"  ⚡ แปลงเป็น H.264 High 4.1 (yuv420p, 30fps, FastStart) สำหรับ iPad...")
            res = subprocess.run(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(temp_out) and os.path.getsize(temp_out) > 0:
                os.replace(temp_out, filepath)
                self._log(f"  ✅ ปรับแต่งไฟล์ให้เล่นบน iPad mini 1 ได้ 100% เรียบร้อย")
                return filepath
            else:
                self._log(f"  ⚠️ แปลงสำหรับ iPad ไม่สำเร็จ (ใช้ไฟล์เดิม): {res.stderr.decode('utf-8', errors='ignore')[:150]}")
        except Exception as e:
            self._log(f"  ⚠️ ข้อผิดพลาดขณะแปลงไฟล์สำหรับ iPad: {e}")
        finally:
            if os.path.exists(temp_out):
                try:
                    os.remove(temp_out)
                except Exception:
                    pass
        return filepath

    def _friendly_error(self, err_obj):
        err = str(err_obj)
        if "The playlist does not exist" in err:
            return "Playlist นี้ไม่มีอยู่จริงใน YouTube (The playlist does not exist) — กรุณาตรวจสอบว่าคัดลอกลิงก์มาครบถ้วนหรือไม่ หรือ Playlist ถูกลบ/ตั้งเป็นส่วนตัว"
        if "Private video" in err or "Private playlist" in err:
            return "วิดีโอหรือ Playlist นี้ถูกตั้งเป็นส่วนตัว (Private) ไม่สามารถเข้าถึงได้"
        if "Video unavailable" in err:
            return "วิดีโอนี้ไม่สามารถใช้งานได้ (Video unavailable)"
        if "Sign in to confirm your age" in err:
            return "วิดีโอนี้จำกัดอายุ (Age-restricted) จำเป็นต้องเข้าสู่ระบบ"
        if "Incomplete YouTube ID" in err:
            return "รหัสลิงก์ YouTube ไม่ครบถ้วน กรุณาตรวจสอบลิงก์"
        if "ERROR:" in err:
            err = err.split("ERROR:", 1)[1].strip()
        return err[:250]

    def _download_worker(self, links, save_dir, fmt_choice, ipad_mode):
        self.download_start_time = time.time()
        start_clock = datetime.datetime.now().strftime("%H:%M:%S น.")

        ffmpeg_bin = get_ffmpeg_path()
        ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.isabs(ffmpeg_bin) else None
        mp3_dir, mp4_dir = self._ensure_subfolders(save_dir)

        self._set_status("🔍 กำลังตรวจสอบลิงก์และดึงรายการเพลง / Playlist...")
        self._set_eta("⏳ กำลังเชื่อมต่อ YouTube เพื่อตรวจสอบรายการ...")
        self._log("==================================================")
        self._log(f"🔍 เริ่มการตรวจสอบลิงก์ ({len(links)} ลิงก์ที่กรอก)")
        self._log(f"⏰ เวลาเริ่มต้น: {start_clock}")
        self._log(f"📂 โฟลเดอร์ปลายทางหลัก: {save_dir}")
        self._log(f"  ├─ 🎵 โฟลเดอร์ MP3: {mp3_dir}")
        self._log(f"  └─ 🎬 โฟลเดอร์ MP4: {mp4_dir}")
        self._log(f"⚙️ ฟอร์แมตที่เลือก: {fmt_choice.upper()}")
        self._log(f"🍏 โหมด iPad mini 1: {'เปิดใช้งาน (H.264 / 30fps)' if ipad_mode else 'ปิด'}")
        if ffmpeg_bin:
            self._log(f"🔧 เครื่องมือ FFmpeg: {ffmpeg_bin}")
        self._log("==================================================")

        resolved_items = []
        failed_items = []

        ydl_opts_scan = {
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts_scan) as ydl_scan:
            for raw_u in links:
                try:
                    self._set_status(f"🔍 กำลังตรวจสอบ: {raw_u[:60]}...")
                    info = ydl_scan.extract_info(raw_u, download=False)
                    if not info:
                        failed_items.append((raw_u, "ไม่พบข้อมูลจากลิงก์นี้"))
                        self._log(f"  ❌ ไม่พบข้อมูล: {raw_u}")
                        continue

                    if info.get('_type') == 'playlist' or 'entries' in info:
                        pl_title = info.get('title', 'YouTube Playlist')
                        raw_entries = [e for e in info.get('entries', []) if e]
                        if not raw_entries:
                            failed_items.append((raw_u, "Playlist ว่างเปล่าหรือไม่มีวิดีโอที่เล่นได้"))
                            self._log(f"  ⚠️ Playlist ว่างเปล่า: {raw_u}")
                            continue

                        self._log(f"  📂 ตรวจพบ Playlist: '{pl_title}' (รวม {len(raw_entries)} เพลง)")
                        for e in raw_entries:
                            vid_url = e.get('url') or e.get('webpage_url')
                            if vid_url and not vid_url.startswith('http'):
                                vid_url = f"https://www.youtube.com/watch?v={vid_url}"
                            vid_id = e.get('id', '')
                            final_url = vid_url or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else '')
                            if final_url:
                                resolved_items.append({'url': final_url, 'title': e.get('title', 'Unknown')})
                    else:
                        vid_title = info.get('title', 'Unknown')
                        vid_url = info.get('webpage_url') or raw_u
                        resolved_items.append({'url': vid_url, 'title': vid_title})
                        self._log(f"  🎬 ตรวจพบวิดีโอ: {vid_title}")
                except Exception as e:
                    friendly_msg = self._friendly_error(e)
                    failed_items.append((raw_u, friendly_msg))
                    self._log(f"  ❌ ข้อผิดพลาดในการตรวจสอบลิงก์: {raw_u}")
                    self._log(f"     -> สาเหตุ: {friendly_msg}")

        # หากไม่มีเพลงที่พร้อมดาวน์โหลดเลยแม้แต่เพลงเดียว
        if not resolved_items:
            self._set_progress(0)
            self._set_status("❌ ดาวน์โหลดล้มเหลว: ไม่พบรายการที่ดาวน์โหลดได้", color="#cc0000")
            self._set_eta("⚠️ กรุณาตรวจสอบลิงก์ YouTube ที่กรอกใหม่อีกครั้ง")

            err_summary = "\n".join([f"• ลิงก์: {u}\n  สาเหตุ: {err}" for u, err in failed_items])
            self._log("\n==================================================")
            self._log("❌ การดาวน์โหลดล้มเหลวทั้งหมด ไม่สามารถดำเนินการต่อได้:")
            self._log(err_summary)
            self._log("==================================================")

            def _fail_ui():
                self.is_downloading = False
                self.start_btn.config(state="normal")
                self.convert_btn.config(state="normal")
                self.clear_btn.config(state="normal")
                messagebox.showerror(
                    "ดาวน์โหลดไม่สำเร็จ",
                    f"ไม่สามารถดาวน์โหลดได้เนื่องจากพบข้อผิดพลาด:\n\n"
                    f"{err_summary}\n\n"
                    f"💡 คำแนะนำ:\n"
                    f"- ตรวจสอบว่าคัดลอกลิงก์มาถูกต้องครบถ้วนหรือไม่ (เช่น รหัส Playlist ขาดหาย)\n"
                    f"- ตรวจสอบว่าวิดีโอหรือ Playlist ไม่ได้ถูกตั้งเป็น ส่วนตัว (Private) หรือถูกลบไปแล้ว"
                )

            self.after(0, _fail_ui)
            return

        total_songs = len(resolved_items)
        self.total_songs = total_songs
        self.current_idx = 1
        success_count = 0
        error_count = len(failed_items)
        failed_downloads = list(failed_items)

        self._log(f"\n🚀 เริ่มดาวน์โหลดเนื้อหาจริงทั้งหมด {total_songs} เพลง...")
        self._set_status(f"🎵 เตรียมดาวน์โหลดทั้งหมด {total_songs} เพลง...")

        for idx, item in enumerate(resolved_items, 1):
            url = item['url']
            title = item.get('title', 'Unknown')
            self.current_idx = idx

            self._set_status(f"🎵 เพลงที่ {idx}/{total_songs}: {title[:40]}...")
            self._set_progress(0)
            self._set_eta(f"⏳ เพลงที่ {idx} จาก {total_songs} เพลง: กำลังดาวน์โหลด...")
            self._log(f"\n[{idx}/{total_songs}] กำลังดาวน์โหลด: {title}\n    URL: {url}")

            out_tmpl_mp4 = os.path.join(mp4_dir, '%(title)s.%(ext)s')
            out_tmpl_mp3 = os.path.join(mp3_dir, '%(title)s.%(ext)s')
            downloaded_mp4_path = None

            def finished_hook(d):
                nonlocal downloaded_mp4_path
                if d['status'] == 'finished':
                    downloaded_mp4_path = d.get('filename')

            # โหมด 1: MP4
            if fmt_choice == "mp4":
                if ipad_mode:
                    v_format = 'bestvideo[vcodec^=avc1][height<=1080][fps<=30]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
                else:
                    v_format = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best'

                ydl_opts = {
                    'outtmpl': out_tmpl_mp4,
                    'progress_hooks': [self._progress_hook, finished_hook],
                    'format': v_format,
                    'merge_output_format': 'mp4',
                    'quiet': True,
                    'no_warnings': True,
                }
                if ffmpeg_dir:
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info:
                            expected_path = ydl.prepare_filename(info)
                            base, _ = os.path.splitext(expected_path)
                            final_mp4 = base + ".mp4"
                            if os.path.exists(final_mp4):
                                downloaded_mp4_path = final_mp4
                            elif downloaded_mp4_path and os.path.exists(downloaded_mp4_path):
                                pass
                            elif os.path.exists(expected_path):
                                downloaded_mp4_path = expected_path

                    self._log(f"  ✅ ดาวน์โหลด MP4 สำเร็จ (บันทึกใน mp4/)")

                    if ipad_mode and downloaded_mp4_path and os.path.exists(downloaded_mp4_path):
                        self._set_status(f"🍏 เพลงที่ {idx}/{total_songs}: กำลังปรับแต่งวิดีโอสำหรับ iPad mini 1...")
                        self._set_eta(f"⚡ กำลังเข้ารหัส H.264 High 4.1 / FastStart เพื่อให้เล่นได้ 100%...")
                        self._post_process_for_ipad(downloaded_mp4_path, ffmpeg_bin)

                    success_count += 1
                except Exception as e:
                    friendly_err = self._friendly_error(e)
                    self._log(f"  ❌ ล้มเหลว: {friendly_err}")
                    failed_downloads.append((title or url, friendly_err))
                    error_count += 1

            # โหมด 2: MP3 อย่างเดียว
            elif fmt_choice == "mp3":
                ydl_opts = {
                    'outtmpl': out_tmpl_mp3,
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
                    self._log(f"  ✅ ดาวน์โหลดและแปลง MP3 สำเร็จ (บันทึกใน mp3/)")
                    success_count += 1
                except Exception as e:
                    friendly_err = self._friendly_error(e)
                    self._log(f"  ❌ ล้มเหลว: {friendly_err}")
                    failed_downloads.append((title or url, friendly_err))
                    error_count += 1

            # โหมด 3: ทั้ง 2 แบบ (MP4 + MP3)
            elif fmt_choice == "both":
                if ipad_mode:
                    v_format = 'bestvideo[vcodec^=avc1][height<=1080][fps<=30]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
                else:
                    v_format = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best'

                ydl_opts_mp4 = {
                    'outtmpl': out_tmpl_mp4,
                    'progress_hooks': [self._progress_hook, finished_hook],
                    'format': v_format,
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
                        if info:
                            expected_path = ydl.prepare_filename(info)
                            base, _ = os.path.splitext(expected_path)
                            final_mp4 = base + ".mp4"
                            if os.path.exists(final_mp4):
                                downloaded_mp4_path = final_mp4
                            elif downloaded_mp4_path and os.path.exists(downloaded_mp4_path):
                                pass
                            elif os.path.exists(expected_path):
                                downloaded_mp4_path = expected_path

                    self._log(f"  ✅ 1/2 ดาวน์โหลด MP4 สำเร็จ (บันทึกใน mp4/)")
                    if ipad_mode and downloaded_mp4_path and os.path.exists(downloaded_mp4_path):
                        self._set_status(f"🍏 เพลงที่ {idx}/{total_songs}: กำลังปรับแต่งวิดีโอสำหรับ iPad mini 1...")
                        self._set_eta(f"⚡ กำลังเข้ารหัส H.264 High 4.1 / FastStart เพื่อให้เล่นได้ 100%...")
                        self._post_process_for_ipad(downloaded_mp4_path, ffmpeg_bin)

                    mp4_ok = True
                except Exception as e:
                    friendly_err = self._friendly_error(e)
                    self._log(f"  ❌ MP4 ล้มเหลว: {friendly_err}")

                # แตกไฟล์ MP3 ต่อทันที โดยนำไปวางไว้ในโฟลเดอร์ mp3
                mp3_ok = False
                if mp4_ok and downloaded_mp4_path and os.path.exists(downloaded_mp4_path) and ffmpeg_bin:
                    file_stem = os.path.splitext(os.path.basename(downloaded_mp4_path))[0]
                    mp3_path = os.path.join(mp3_dir, f"{file_stem}.mp3")
                    self._set_status(f"🎵 เพลงที่ {idx}/{total_songs}: กำลังสร้างไฟล์ MP3...")
                    self._set_eta(f"⚡ กำลังแปลงไฟล์เสียง MP3 (192 kbps) จาก MP4 โดยตรง...")
                    self._log(f"  ⚡ แปลงเป็น MP3 จาก MP4 โดยตรง...")
                    try:
                        cmd = [ffmpeg_bin, "-y", "-i", downloaded_mp4_path, "-vn", "-c:a", "libmp3lame", "-q:a", "2", mp3_path]
                        startupinfo = None
                        if sys.platform == "win32":
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        subprocess.run(cmd, startupinfo=startupinfo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        self._log(f"  ✅ 2/2 แปลง MP3 สำเร็จ (บันทึกใน mp3/)")
                        mp3_ok = True
                    except Exception as e:
                        self._log(f"  ⚠️ แปลง MP3 ตรงขัดข้อง: {e}")

                if not mp3_ok:
                    ydl_opts_mp3 = {
                        'outtmpl': out_tmpl_mp3,
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
                        self._log(f"  ✅ 2/2 ดาวน์โหลด MP3 สำเร็จ (บันทึกใน mp3/)")
                        mp3_ok = True
                    except Exception as e:
                        friendly_err = self._friendly_error(e)
                        self._log(f"  ❌ MP3 ล้มเหลว: {friendly_err}")

                if mp4_ok or mp3_ok:
                    success_count += 1
                else:
                    error_count += 1
                    failed_downloads.append((title or url, "ล้มเหลวทั้ง MP4 และ MP3"))

        total_elapsed = time.time() - self.download_start_time
        mins, secs = divmod(int(total_elapsed), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            elapsed_str = f"{hours} ชม. {mins} นาที {secs} วินาที"
        elif mins > 0:
            elapsed_str = f"{mins} นาที {secs} วินาที"
        else:
            elapsed_str = f"{secs} วินาที"

        finish_clock = datetime.datetime.now().strftime("%H:%M:%S น.")

        self._set_progress(100)
        if error_count == 0:
            status_txt = f"🎉 เสร็จสิ้นสมบูรณ์ทั้งหมด {total_songs} เพลง!"
            status_color = "#008800"
        elif success_count > 0:
            status_txt = f"⚠️ เสร็จสิ้นบางส่วน: สำเร็จ {success_count} เพลง, ล้มเหลว {error_count} เพลง"
            status_color = "#cc6600"
        else:
            status_txt = f"❌ ดาวน์โหลดล้มเหลวทั้งหมด ({error_count} เพลง)"
            status_color = "#cc0000"

        self._set_status(status_txt, color=status_color)
        self._set_eta(f"⏱️ เวลาที่ใช้ทั้งหมด: {elapsed_str}  |  🏁 เสร็จสมบูรณ์เมื่อเวลา: {finish_clock}")

        self._log(f"\n==================================================")
        self._log(f"📊 สรุปผลการดาวน์โหลด:")
        self._log(f"  - จำนวนเพลงทั้งหมด: {total_songs} เพลง")
        self._log(f"  - สำเร็จ: {success_count} รายการ")
        self._log(f"  - ล้มเหลว: {error_count} รายการ")
        self._log(f"  - เวลาที่ใช้ทั้งหมด: {elapsed_str}")
        self._log(f"  - เสร็จสิ้นเมื่อเวลา: {finish_clock}")
        if failed_downloads:
            self._log(f"\n❌ รายการที่ไม่สำเร็จ:")
            for item_name, err in failed_downloads:
                self._log(f"  • {item_name}:\n    -> {err}")
        self._log(f"  - โฟลเดอร์หลัก: {save_dir}")
        self._log(f"    • MP3: {mp3_dir}")
        self._log(f"    • MP4: {mp4_dir}")
        self._log(f"==================================================")

        def _finish_ui():
            self.is_downloading = False
            self.start_btn.config(state="normal")
            self.convert_btn.config(state="normal")
            self.clear_btn.config(state="normal")

            if error_count == 0:
                messagebox.showinfo(
                    "เสร็จสิ้น",
                    f"ดาวน์โหลดเสร็จสมบูรณ์!\n\n"
                    f"🎵 จำนวนทั้งหมด: {total_songs} เพลง\n"
                    f"✅ สำเร็จ: {success_count} รายการ\n"
                    f"⏱️ เวลาที่ใช้ทั้งหมด: {elapsed_str}\n"
                    f"🏁 เสร็จสิ้นเวลา: {finish_clock}\n\n"
                    f"บันทึกไฟล์แยกประเภทไว้ที่:\n"
                    f"🎵 MP3: {mp3_dir}\n"
                    f"🎬 MP4: {mp4_dir}"
                )
            elif success_count > 0:
                err_preview = "\n".join([f"• {name}:\n  {err}" for name, err in failed_downloads[:4]])
                if len(failed_downloads) > 4:
                    err_preview += f"\n... และอีก {len(failed_downloads) - 4} รายการ (ตรวจสอบได้ใน Logs)"
                messagebox.showwarning(
                    "เสร็จสิ้นบางส่วน",
                    f"ดาวน์โหลดเสร็จสิ้นบางส่วน!\n\n"
                    f"✅ สำเร็จ: {success_count} รายการ\n"
                    f"❌ ล้มเหลว: {error_count} รายการ\n"
                    f"⏱️ เวลาที่ใช้: {elapsed_str}\n\n"
                    f"รายการที่มีปัญหา:\n{err_preview}\n\n"
                    f"บันทึกไฟล์สำเร็จไว้ที่: {save_dir}"
                )
            else:
                err_preview = "\n".join([f"• {name}:\n  {err}" for name, err in failed_downloads[:4]])
                messagebox.showerror(
                    "ดาวน์โหลดไม่สำเร็จ",
                    f"ไม่สามารถดาวน์โหลดได้ (ล้มเหลว {error_count} รายการ)\n\n"
                    f"สาเหตุที่ล้มเหลว:\n{err_preview}\n\n"
                    f"คำแนะนำ: กรุณาตรวจสอบลิงก์ YouTube ที่กรอกใหม่อีกครั้ง"
                )

        self.after(0, _finish_ui)

    def _convert_existing_for_ipad(self):
        """แปลงไฟล์ MP4 ที่ดาวน์โหลดมาแล้ว ให้สามารถเล่นภาพบน iPad mini 1 ได้ 100%"""
        if self.is_downloading:
            return

        files = filedialog.askopenfilenames(
            title="เลือกไฟล์ MP4 ที่ต้องการแปลงให้เล่นบน iPad ได้",
            filetypes=[("Video Files", "*.mp4;*.mkv;*.webm;*.avi;*.mov"), ("All Files", "*.*")]
        )
        if not files:
            return

        self.is_downloading = True
        self.start_btn.config(state="disabled")
        self.convert_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self._set_progress(0)

        def _worker():
            ffmpeg_bin = get_ffmpeg_path()
            total = len(files)
            success = 0
            start_t = time.time()
            self._log(f"\n==================================================")
            self._log(f"🍏 เริ่มการแปลงไฟล์เดิมให้เล่นบน iPad mini 1 ({total} ไฟล์)")
            self._log(f"⏰ เวลาเริ่มต้น: {datetime.datetime.now().strftime('%H:%M:%S น.')}")
            self._log(f"==================================================")

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            for idx, f in enumerate(files, 1):
                base, _ = os.path.splitext(f)
                out_path = f"{base}_ipad.mp4"

                elapsed = time.time() - start_t
                if idx > 1 and elapsed > 1.0:
                    avg_time = elapsed / (idx - 1)
                    rem_sec = int(avg_time * (total - idx + 1))
                    mins, secs = divmod(rem_sec, 60)
                    rem_str = f"{mins} นาที {secs} วินาที" if mins > 0 else f"{secs} วินาที"
                    finish_str = (datetime.datetime.now() + datetime.timedelta(seconds=rem_sec)).strftime("%H:%M:%S น.")
                    eta_text = f"⏳ เหลืออีกประมาณ: {rem_str}  |  🏁 คาดว่าจะเสร็จ: {finish_str}"
                else:
                    eta_text = "⏳ กำลังประมวลผลไฟล์..."

                self._set_status(f"🍏 กำลังแปลงไฟล์ที่ {idx}/{total}: {os.path.basename(f)}")
                self._set_eta(eta_text)
                self._log(f"[{idx}/{total}] แปลง: {os.path.basename(f)}")

                cmd = [
                    ffmpeg_bin, "-y", "-i", f,
                    "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
                    "-pix_fmt", "yuv420p", "-r", "30",
                    "-vf", "scale='min(1920,iw)':-2",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                    "-movflags", "+faststart",
                    out_path
                ]

                try:
                    res = subprocess.run(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res.returncode == 0 and os.path.exists(out_path):
                        self._log(f"  ✅ สำเร็จ -> {os.path.basename(out_path)}")
                        success += 1
                    else:
                        self._log(f"  ❌ แปลงไม่สำเร็จ: {res.stderr.decode('utf-8', errors='ignore')[:150]}")
                except Exception as e:
                    self._log(f"  ❌ เกิดข้อผิดพลาด: {e}")

                self._set_progress((idx / total) * 100)

            total_elapsed = time.time() - start_t
            mins, secs = divmod(int(total_elapsed), 60)
            elapsed_str = f"{mins} นาที {secs} วินาที" if mins > 0 else f"{secs} วินาที"
            finish_clock = datetime.datetime.now().strftime("%H:%M:%S น.")

            self._set_status(f"🎉 แปลงเสร็จสิ้นทั้งหมด {total} ไฟล์! (สำเร็จ {success}/{total})", color="#008800")
            self._set_eta(f"⏱️ เวลาที่ใช้ทั้งหมด: {elapsed_str}  |  🏁 เสร็จสมบูรณ์เมื่อเวลา: {finish_clock}")
            self._log(f"==================================================")
            self._log(f"🎉 แปลงไฟล์ทั้งหมดเสร็จสมบูรณ์!")
            self._log(f"  - จำนวนทั้งหมด: {total} ไฟล์ (สำเร็จ {success} ไฟล์)")
            self._log(f"  - เวลาที่ใช้ทั้งหมด: {elapsed_str}")
            self._log(f"  - เสร็จสิ้นเมื่อเวลา: {finish_clock}")
            self._log(f"==================================================")

            def _done():
                self.is_downloading = False
                self.start_btn.config(state="normal")
                self.convert_btn.config(state="normal")
                self.clear_btn.config(state="normal")
                messagebox.showinfo("เสร็จสิ้น", f"แปลงไฟล์สำหรับ iPad เสร็จเรียบร้อย!\n\nสำเร็จ {success} จาก {total} ไฟล์\nไฟล์ที่ได้จะมีชื่อลงท้ายด้วย _ipad.mp4\nเวลาที่ใช้: {elapsed_str}")

            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
