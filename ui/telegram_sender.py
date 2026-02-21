# --- START OF FILE ui/telegram_sender.py ---
import os
import json
import time
import asyncio
import re
import requests
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QComboBox, 
                             QGroupBox, QTextEdit, QProgressBar, QMessageBox,
                             QRadioButton, QButtonGroup, QScrollArea, QSpinBox, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.config import ConfigManager
from ui.common import tr

# Try importing Telethon
try:
    from telethon import TelegramClient
    from telethon.tl.types import InputMediaPoll, Poll, PollAnswer, TextWithEntities
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False


class TelegramWorker(QThread):
    log_signal = pyqtSignal(str, str) 
    progress_signal = pyqtSignal(int, int) 
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    stopped_at_signal = pyqtSignal(int)

    def __init__(self, bank_path, config_data, mode="bot", start_idx=1, title_msg=None):
        super().__init__()
        self.bank_path = bank_path
        self.cfg = config_data
        self.mode = mode
        self.start_idx = start_idx
        self.title_msg = title_msg
        self.is_running = True
        self.option_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']

    def stop(self):
        self.is_running = False

    def get_media_files(self, folder, idx):
        found = []
        exts = ['.jpg', '.png', '.gif']
        img_dir = os.path.join(folder, "images")
        if not os.path.exists(img_dir): return []
        
        # Base image
        for ext in exts:
            p = os.path.join(img_dir, f"{idx}{ext}")
            if os.path.exists(p): 
                found.append(p)
                break
        
        # Sequence images
        for i in range(1, 11):
            f_found = False
            for ext in exts:
                p = os.path.join(img_dir, f"{idx}_{i}{ext}")
                if os.path.exists(p):
                    found.append(p)
                    f_found = True
                    break
            if not f_found: pass 
            
        return sorted(found)

    def get_note_media_file(self, folder, idx):
        exts = ['.jpg', '.png', '.gif']
        img_dir = os.path.join(folder, "images")
        if not os.path.exists(img_dir): return None
        for ext in exts:
            p = os.path.join(img_dir, f"{idx}_note{ext}")
            if os.path.exists(p):
                return p
        return None

    def escape_markdown(self, text):
        if not isinstance(text, str): return str(text)
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\1', text)

    def run(self):
        try:
            with open(os.path.join(self.bank_path, "bank.json"), 'r', encoding='utf-8') as f:
                quizzes = json.load(f)
        except Exception as e:
            self.error_signal.emit(str(e))
            return

        total = len(quizzes)
        
        if self.mode == "bot":
            self.run_bot_mode(quizzes, total)
        else:
            if TELETHON_AVAILABLE:
                asyncio.run(self.run_user_mode(quizzes, total))
            else:
                self.error_signal.emit("Telethon not installed.")

    def run_bot_mode(self, quizzes, total):
        token = self.cfg.get("bot_token")
        chat_id = self.cfg.get("chat_id")
        base_url = f"https://api.telegram.org/bot{token}"
        
        # Send optional title message
        if self.title_msg and self.start_idx == 1:
            try:
                r = requests.post(f"{base_url}/sendMessage", data={"chat_id": chat_id, "text": self.title_msg}, timeout=30)
                r.raise_for_status()
                self.log_signal.emit("Title message sent.", "#66bb6a")
            except Exception as e:
                self.log_signal.emit(f"Error sending title: {e}", "#ff9800")
        
        for i in range(self.start_idx - 1, total):
            idx = i + 1
            if not self.is_running: 
                self.stopped_at_signal.emit(idx)
                break
                
            quiz = quizzes[i]
            
            # Check for totally empty question and completely ignore it
            q_text = re.sub(r'^[\d\s\-.)]+', '', quiz.get("question", "")).strip()
            if not quiz.get("options") and not quiz.get("explanation") and not q_text:
                self.log_signal.emit(f"Skipping empty text question #{idx}...", "#888")
                continue

            self.progress_signal.emit(idx, total)
            self.log_signal.emit(tr("tg_processing").format(idx), "#4da3ff") 

            media_files = self.get_media_files(self.bank_path, idx)
            
            success = False
            retries = 0
            
            while retries < 5 and self.is_running:
                try:
                    last_msg_id = None
                    # 1. Send Media
                    if media_files:
                        if len(media_files) == 1:
                            fpath = media_files[0]
                            is_gif = fpath.endswith(".gif")
                            method = "sendAnimation" if is_gif else "sendPhoto"
                            with open(fpath, 'rb') as f:
                                files = {'animation' if is_gif else 'photo': f}
                                data = {'chat_id': chat_id, 'caption': f"Question #{idx}"}
                                r = requests.post(f"{base_url}/{method}", data=data, files=files, timeout=30)
                                r.raise_for_status()
                                last_msg_id = r.json().get('result', {}).get('message_id')
                        else:
                            files_dict = {}
                            media_arr = []
                            file_handles = []
                            for j, p in enumerate(media_files):
                                fh = open(p, 'rb')
                                file_handles.append(fh)
                                key = f"media{j}"
                                files_dict[key] = fh
                                media_arr.append({
                                    "type": "photo", 
                                    "media": f"attach://{key}",
                                    "caption": f"Question #{idx}" if j==0 else ""
                                })
                            
                            r = requests.post(f"{base_url}/sendMediaGroup", 
                                              data={'chat_id': chat_id, 'media': json.dumps(media_arr)}, 
                                              files=files_dict, timeout=60)
                            for fh in file_handles: fh.close()
                            r.raise_for_status()
                            last_msg_id = r.json().get('result', [])[-1].get('message_id')

                    # 2. Send Poll
                    options = quiz.get("options", [])
                    if len(options) < 2:
                        options = ["A", "B", "C", "D", "E"][:max(2, len(quiz.get("correct_options", [0])) + 1)]
                        if len(options) < 2: options = ["A", "B"]
                        
                    correct_opts = quiz.get("correct_options", [])
                    if not correct_opts: correct_opts = [0]
                    
                    expl = quiz.get("explanation", "").strip()
                    is_quiz = len(correct_opts) == 1
                    
                    poll_data = {
                        "chat_id": chat_id,
                        "question": quiz.get("question", "?") or "?",
                        "options": json.dumps(options),
                        "is_anonymous": True,
                        "type": "quiz" if is_quiz else "regular",
                        "allows_multiple_answers": not is_quiz
                    }
                    if is_quiz:
                        poll_data["correct_option_id"] = correct_opts[0]
                        if expl:
                            poll_data["explanation"] = self.escape_markdown(expl)
                            poll_data["explanation_parse_mode"] = "MarkdownV2"
                    
                    if last_msg_id: poll_data["reply_to_message_id"] = last_msg_id

                    r = requests.post(f"{base_url}/sendPoll", data=poll_data, timeout=30)
                    r.raise_for_status()
                    poll_msg_id = r.json().get('result', {}).get('message_id')
                    self.log_signal.emit("Poll sent.", "#66bb6a") 
                    
                    # 3. Spoiler and Notes Image
                    note_media = self.get_note_media_file(self.bank_path, idx)
                    if (not is_quiz) or (is_quiz and expl) or note_media:
                        correct_syms = [self.option_letters[k] for k in correct_opts if 0 <= k < 10]
                        txt = f"✅ الجواب: {', '.join(correct_syms)}"
                        if expl: txt += f"\n💡 {expl}"
                        spoiler = f"||{self.escape_markdown(txt)}||"
                        
                        if note_media:
                            with open(note_media, 'rb') as f:
                                r2 = requests.post(f"{base_url}/sendPhoto", data={
                                    "chat_id": chat_id, "caption": spoiler, 
                                    "parse_mode": "MarkdownV2", "reply_to_message_id": poll_msg_id,
                                    "has_spoiler": True
                                }, files={'photo': f}, timeout=30)
                                r2.raise_for_status()
                        else:
                            r2 = requests.post(f"{base_url}/sendMessage", data={
                                "chat_id": chat_id, "text": spoiler, 
                                "parse_mode": "MarkdownV2", "reply_to_message_id": poll_msg_id
                            }, timeout=30)
                            r2.raise_for_status()
                    
                    success = True
                    break
                except Exception as e:
                    retries += 1
                    self.log_signal.emit(f"Error on Q#{idx} (Retry {retries}/5): {e}", "#ff9800")
                    for _ in range(20):
                        if not self.is_running: break
                        time.sleep(0.1)
            
            if not self.is_running:
                if not success:
                    self.stopped_at_signal.emit(idx)
                else:
                    self.stopped_at_signal.emit(idx + 1)
                break

            if not success:
                self.error_signal.emit(f"Failed to send Q#{idx} after 5 retries. Stopped.")
                self.stopped_at_signal.emit(idx)
                self.is_running = False
                return
            
            for _ in range(30):
                if not self.is_running: break
                time.sleep(0.1)

        if self.is_running:
            self.finished_signal.emit()


    async def run_user_mode(self, quizzes, total):
        api_id = self.cfg.get("api_id")
        api_hash = self.cfg.get("api_hash")
        chat_id = self.cfg.get("chat_id")
        
        try:
            real_chat_id = int(chat_id)
        except:
            real_chat_id = chat_id

        client = TelegramClient('bb_qbox_session', api_id, api_hash)
        await client.start()
        
        if self.title_msg and self.start_idx == 1:
            try:
                await client.send_message(real_chat_id, self.title_msg)
                self.log_signal.emit("Title message sent.", "#66bb6a")
            except Exception as e:
                self.log_signal.emit(f"Error sending title: {e}", "#ff9800")
        
        for i in range(self.start_idx - 1, total):
            idx = i + 1
            if not self.is_running: 
                self.stopped_at_signal.emit(idx)
                break
                
            quiz = quizzes[i]
            
            q_text = re.sub(r'^[\d\s\-.)]+', '', quiz.get("question", "")).strip()
            if not quiz.get("options") and not quiz.get("explanation") and not q_text:
                self.log_signal.emit(f"Skipping empty text question #{idx}...", "#888")
                continue
                
            self.progress_signal.emit(idx, total)
            self.log_signal.emit(tr("tg_processing").format(idx), "#4da3ff")

            media_files = self.get_media_files(self.bank_path, idx)
            
            success = False
            retries = 0
            while retries < 5 and self.is_running:
                try:
                    reply_to = None

                    # 1. Media
                    if media_files:
                        msg = await client.send_file(real_chat_id, media_files, caption=f"Question #{idx}")
                        reply_to = msg[-1].id if isinstance(msg, list) else msg.id

                    # 2. Poll
                    options = quiz.get("options", [])
                    if len(options) < 2:
                        options = ["A", "B", "C", "D", "E"][:max(2, len(quiz.get("correct_options", [0])) + 1)]
                        if len(options) < 2: options = ["A", "B"]

                    correct_opts = quiz.get("correct_options", [])
                    if not correct_opts: correct_opts = [0]

                    answers = [PollAnswer(TextWithEntities(str(o), []), bytes([k])) for k, o in enumerate(options)]
                    correct = [bytes([k]) for k in correct_opts]
                    is_quiz = len(correct) == 1
                    
                    expl = quiz.get("explanation", "").strip()
                    
                    poll = Poll(
                        id=0,
                        question=TextWithEntities(quiz.get("question", "?") or "?", []),
                        answers=answers,
                        closed=False,
                        public_voters=False,
                        multiple_choice=not is_quiz,
                        quiz=is_quiz,
                        close_period=None, close_date=None
                    )
                    
                    sol = expl if (is_quiz and expl) else None
                    sol_ent = [] if sol else None

                    poll_msg = await client.send_message(
                        real_chat_id,
                        file=InputMediaPoll(poll=poll, correct_answers=correct if is_quiz else None, 
                                            solution=sol, solution_entities=sol_ent),
                        reply_to=reply_to
                    )
                    self.log_signal.emit("Poll sent.", "#66bb6a")

                    # 3. Spoiler
                    note_media = self.get_note_media_file(self.bank_path, idx)
                    if (not is_quiz) or (is_quiz and sol) or note_media:
                        correct_syms = [self.option_letters[k] for k in correct_opts if 0 <= k < 10]
                        txt = f"✅ Answer: {', '.join(correct_syms)}"
                        if sol: txt += f"\n💡 Note: {sol}"
                        
                        if note_media:
                            await client.send_file(real_chat_id, note_media, caption=f"||{txt}||", parse_mode='md', reply_to=poll_msg.id)
                        else:
                            await client.send_message(real_chat_id, f"||{txt}||", parse_mode='md', reply_to=poll_msg.id)
                        
                    success = True
                    break
                except Exception as e:
                    retries += 1
                    self.log_signal.emit(f"Error on Q#{idx} (Retry {retries}/5): {e}", "#ff9800")
                    for _ in range(20):
                        if not self.is_running: break
                        await asyncio.sleep(0.1)
            
            if not self.is_running:
                if not success:
                    self.stopped_at_signal.emit(idx)
                else:
                    self.stopped_at_signal.emit(idx + 1)
                break

            if not success:
                self.error_signal.emit(f"Failed to send Q#{idx} after 5 retries. Stopped.")
                self.stopped_at_signal.emit(idx)
                self.is_running = False
                break
                
            for _ in range(30):
                if not self.is_running: break
                await asyncio.sleep(0.1)
        
        await client.disconnect()

        if self.is_running:
            self.finished_signal.emit()


class TelegramWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("tg_title"))
        self.resize(700, 750)
        
        if ConfigManager.get_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        ConfigManager.load_window_state("telegram", self)
        self.worker = None
        self.init_ui()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        ConfigManager.save_window_state("telegram", self)
        super().closeEvent(event)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #2b2b2b; color: white; font-family: 'Segoe UI'; font-size: 14px; }
            QGroupBox { border: 1px solid #555; border-radius: 6px; margin-top: 10px; font-weight: bold; color: #4da3ff; padding: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit, QComboBox, QSpinBox { background-color: #333; border: 1px solid #555; padding: 6px; border-radius: 4px; color: #fff; }
            QPushButton { background-color: #444; border: 1px solid #666; padding: 8px; border-radius: 4px; color: white; }
            QPushButton:hover { background-color: #505050; border-color: #4da3ff; }
            QTextEdit { background-color: #1e1e1e; border: 1px solid #444; font-family: Consolas, monospace; }
            QProgressBar { border: 1px solid #444; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background-color: #1565C0; }
        """)

        # 1. Bank Selection
        gb_bank = QGroupBox(tr("tg_select_bank"))
        gb_bank_l = QVBoxLayout(gb_bank)
        
        h_bank = QHBoxLayout()
        self.combo_banks = QComboBox()
        self.load_banks()
        self.combo_banks.currentIndexChanged.connect(self.on_bank_selected)
        h_bank.addWidget(self.combo_banks)
        
        lbl_start = QLabel("Start from Q:" if ConfigManager.get_language() == "en" else "البدء من سؤال:")
        h_bank.addWidget(lbl_start)
        
        self.spin_start = QSpinBox()
        self.spin_start.setMinimum(1)
        self.spin_start.setMaximum(999999)
        self.spin_start.setValue(1)
        self.spin_start.setMinimumWidth(80)
        h_bank.addWidget(self.spin_start)
        h_bank.setStretch(0, 1) 
        gb_bank_l.addLayout(h_bank)
        
        h_title = QHBoxLayout()
        self.chk_title = QCheckBox(tr("tg_send_title"))
        self.txt_title = QLineEdit()
        self.txt_title.setText(ConfigManager.get_config_value("tg_title_msg", "#المحاضرة_"))
        self.txt_title.setEnabled(False)
        self.chk_title.toggled.connect(self.txt_title.setEnabled)
        h_title.addWidget(self.chk_title)
        h_title.addWidget(self.txt_title)
        gb_bank_l.addLayout(h_title)
        
        layout.addWidget(gb_bank)

        # 2. Settings
        gb_sets = QGroupBox(tr("tg_settings"))
        sets_l = QVBoxLayout(gb_sets)
        
        # Mode
        h_mode = QHBoxLayout()
        h_mode.addWidget(QLabel(tr("tg_mode")))
        self.radio_bot = QRadioButton(tr("tg_mode_bot"))
        self.radio_user = QRadioButton(tr("tg_mode_user"))
        self.radio_bot.setChecked(True)
        if not TELETHON_AVAILABLE:
            self.radio_user.setEnabled(False)
            self.radio_user.setText(tr("tg_mode_user") + " (Missing Lib)")
        
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_bot)
        self.mode_group.addButton(self.radio_user)
        h_mode.addWidget(self.radio_bot)
        h_mode.addWidget(self.radio_user)
        h_mode.addStretch()
        sets_l.addLayout(h_mode)
        
        # Inputs
        self.stack_bot = QWidget()
        l_bot = QVBoxLayout(self.stack_bot)
        l_bot.setContentsMargins(0,0,0,0)
        self.txt_token = QLineEdit()
        self.txt_token.setPlaceholderText("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        l_bot.addWidget(QLabel(tr("tg_bot_token")))
        l_bot.addWidget(self.txt_token)

        self.stack_user = QWidget()
        l_usr = QVBoxLayout(self.stack_user)
        l_usr.setContentsMargins(0,0,0,0)
        self.txt_api_id = QLineEdit()
        self.txt_api_hash = QLineEdit()
        self.txt_api_hash.setEchoMode(QLineEdit.EchoMode.Password)
        l_usr.addWidget(QLabel(tr("tg_api_id")))
        l_usr.addWidget(self.txt_api_id)
        l_usr.addWidget(QLabel(tr("tg_api_hash")))
        l_usr.addWidget(self.txt_api_hash)
        self.stack_user.hide()

        sets_l.addWidget(self.stack_bot)
        sets_l.addWidget(self.stack_user)
        
        # Chat ID
        self.txt_chat = QLineEdit()
        self.txt_chat.setPlaceholderText("@channel or -100xxxxxxxx")
        sets_l.addWidget(QLabel(tr("tg_chat_id")))
        sets_l.addWidget(self.txt_chat)
        
        btn_save = QPushButton(tr("tg_save_creds"))
        btn_save.clicked.connect(self.save_creds)
        sets_l.addWidget(btn_save)
        
        layout.addWidget(gb_sets)

        # 3. Log & Progress
        layout.addWidget(QLabel(tr("tg_log")))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        
        self.prog_bar = QProgressBar()
        layout.addWidget(self.prog_bar)

        # 4. Actions
        h_act = QHBoxLayout()
        self.btn_start = QPushButton(tr("tg_start"))
        self.btn_start.setMinimumHeight(50)
        self.btn_start.setStyleSheet("background-color: #2e7d32; font-weight: bold; font-size: 16px;")
        self.btn_start.clicked.connect(self.start_process)
        
        self.btn_stop = QPushButton(tr("tg_stop"))
        self.btn_stop.setMinimumHeight(50)
        self.btn_stop.setStyleSheet("background-color: #c62828; font-weight: bold;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_process)
        
        btn_home = QPushButton(tr("back_menu"))
        btn_home.setFlat(True)
        btn_home.clicked.connect(self.go_home)

        h_act.addWidget(self.btn_start)
        h_act.addWidget(self.btn_stop)
        layout.addLayout(h_act)
        layout.addWidget(btn_home)

        # Logic
        self.radio_bot.toggled.connect(self.switch_mode)
        self.load_creds()

    def load_banks(self):
        self.combo_banks.clear()
        if os.path.exists("banks"):
            dirs = sorted([d for d in os.listdir("banks") if os.path.isdir(os.path.join("banks", d))])
            self.combo_banks.addItems(dirs)

    def on_bank_selected(self):
        self.spin_start.setValue(1)
        self.btn_start.setText(tr("tg_start"))

    def switch_mode(self):
        if self.radio_bot.isChecked():
            self.stack_bot.show()
            self.stack_user.hide()
        else:
            self.stack_bot.hide()
            self.stack_user.show()

    def load_creds(self):
        creds = ConfigManager.get_secret("telegram", {})
        self.txt_token.setText(creds.get("bot_token", ""))
        self.txt_chat.setText(creds.get("chat_id", ""))
        self.txt_api_id.setText(creds.get("api_id", ""))
        self.txt_api_hash.setText(creds.get("api_hash", ""))

    def save_creds(self):
        data = {
            "bot_token": self.txt_token.text().strip(),
            "chat_id": self.txt_chat.text().strip(),
            "api_id": self.txt_api_id.text().strip(),
            "api_hash": self.txt_api_hash.text().strip()
        }
        ConfigManager.set_secret("telegram", data)
        ConfigManager.set_config_value("tg_title_msg", self.txt_title.text().strip())
        return data

    def start_process(self):
        bank = self.combo_banks.currentText()
        if not bank:
            QMessageBox.warning(self, "Error", tr("tg_err_no_bank"))
            return
            
        bank_path = os.path.join("banks", bank)
        cfg = self.save_creds() 
        
        mode = "bot" if self.radio_bot.isChecked() else "user"
        start_idx = self.spin_start.value()
        title_msg = self.txt_title.text().strip() if self.chk_title.isChecked() else None
        
        self.log_view.clear()
        self.log_view.append(f"<span style='color: #888'>Starting in {mode.upper()} mode for bank: {bank} from Q#{start_idx}...</span>")
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_banks.setEnabled(False)
        self.spin_start.setEnabled(False)
        self.txt_title.setEnabled(False)
        self.chk_title.setEnabled(False)
        
        self.worker = TelegramWorker(bank_path, cfg, mode, start_idx, title_msg)
        self.worker.log_signal.connect(self.log_msg)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
        self.worker.stopped_at_signal.connect(self.on_stopped_at)
        
        self.worker.finished.connect(self.reset_ui)
        self.worker.start()

    def stop_process(self):
        if self.worker:
            self.worker.stop()
            self.log_msg(tr("tg_stopped"), "#ff9800")
            self.btn_stop.setEnabled(False)

    def log_msg(self, msg, color):
        self.log_view.append(f"<span style='color: {color}'>{msg}</span>")
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def update_progress(self, curr, total):
        self.prog_bar.setMaximum(total)
        self.prog_bar.setValue(curr)

    def on_stopped_at(self, idx):
        self.spin_start.setValue(idx)
        resume_text = "Resume Publishing" if ConfigManager.get_language() == "en" else "استئناف النشر"
        self.btn_start.setText(resume_text)

    def on_finished(self):
        self.log_msg(tr("tg_done"), "#4CAF50")
        self.spin_start.setValue(1)
        self.btn_start.setText(tr("tg_start"))

    def on_error(self, err):
        self.log_msg(f"FATAL ERROR: {err}", "#ff0000")
        QMessageBox.critical(self, "Error", err)

    def reset_ui(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_banks.setEnabled(True)
        self.spin_start.setEnabled(True)
        self.chk_title.setEnabled(True)
        self.txt_title.setEnabled(self.chk_title.isChecked())

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None)
        self.menu.show()
        self.close()
# --- END OF FILE ui/telegram_sender.py ---