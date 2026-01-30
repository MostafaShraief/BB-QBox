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
                             QRadioButton, QButtonGroup, QScrollArea)
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
    log_signal = pyqtSignal(str, str) # message, color code
    progress_signal = pyqtSignal(int, int) # current, total
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, bank_path, config_data, mode="bot"):
        super().__init__()
        self.bank_path = bank_path
        self.cfg = config_data
        self.mode = mode
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

        self.finished_signal.emit()

    def run_bot_mode(self, quizzes, total):
        token = self.cfg.get("bot_token")
        chat_id = self.cfg.get("chat_id")
        base_url = f"https://api.telegram.org/bot{token}"
        
        for idx, quiz in enumerate(quizzes, 1):
            if not self.is_running: break
            
            self.progress_signal.emit(idx, total)
            self.log_signal.emit(tr("tg_processing").format(idx), "#4da3ff") # Blue

            media_files = self.get_media_files(self.bank_path, idx)
            last_msg_id = None
            
            # 1. Send Media
            if media_files:
                try:
                    if len(media_files) == 1:
                        fpath = media_files[0]
                        is_gif = fpath.endswith(".gif")
                        method = "sendAnimation" if is_gif else "sendPhoto"
                        with open(fpath, 'rb') as f:
                            files = {'animation' if is_gif else 'photo': f}
                            data = {'chat_id': chat_id, 'caption': f"Question #{idx}"}
                            r = requests.post(f"{base_url}/{method}", data=data, files=files)
                            if r.ok: last_msg_id = r.json()['result']['message_id']
                    else:
                        # Album
                        files_dict = {}
                        media_arr = []
                        file_handles = []
                        for i, p in enumerate(media_files):
                            fh = open(p, 'rb')
                            file_handles.append(fh)
                            key = f"media{i}"
                            files_dict[key] = fh
                            media_arr.append({
                                "type": "photo", 
                                "media": f"attach://{key}",
                                "caption": f"Question #{idx}" if i==0 else ""
                            })
                        
                        r = requests.post(f"{base_url}/sendMediaGroup", 
                                          data={'chat_id': chat_id, 'media': json.dumps(media_arr)}, 
                                          files=files_dict)
                        for fh in file_handles: fh.close()
                        if r.ok: last_msg_id = r.json()['result'][-1]['message_id']
                except Exception as e:
                    self.log_signal.emit(f"Media Error: {e}", "#ff5252")

            # 2. Send Poll
            expl = quiz.get("explanation", "").strip()
            is_quiz = len(quiz.get("correct_options", [])) == 1
            
            poll_data = {
                "chat_id": chat_id,
                "question": quiz.get("question", "?"),
                "options": json.dumps(quiz.get("options", [])),
                "is_anonymous": True,
                "type": "quiz" if is_quiz else "regular",
                "allows_multiple_answers": not is_quiz
            }
            if is_quiz:
                poll_data["correct_option_id"] = quiz.get("correct_options", [0])[0]
                if expl:
                    poll_data["explanation"] = self.escape_markdown(expl)
                    poll_data["explanation_parse_mode"] = "MarkdownV2"
            
            if last_msg_id: poll_data["reply_to_message_id"] = last_msg_id

            try:
                r = requests.post(f"{base_url}/sendPoll", data=poll_data)
                if r.ok:
                    poll_msg_id = r.json()['result']['message_id']
                    self.log_signal.emit("Poll sent.", "#66bb6a") # Green
                    
                    # Spoiler for non-quiz or fallback
                    if (not is_quiz) or (is_quiz and expl):
                        # Logic for spoiler text
                        correct_syms = [self.option_letters[i] for i in quiz["correct_options"] if 0 <= i < 10]
                        txt = f"✅ الجواب: {', '.join(correct_syms)}"
                        if expl: txt += f"\n💡 {expl}"
                        spoiler = f"||{self.escape_markdown(txt)}||"
                        
                        requests.post(f"{base_url}/sendMessage", data={
                            "chat_id": chat_id, "text": spoiler, 
                            "parse_mode": "MarkdownV2", "reply_to_message_id": poll_msg_id
                        })
                else:
                    self.log_signal.emit(f"API Error: {r.text}", "#ff5252")
            except Exception as e:
                self.log_signal.emit(f"Poll Error: {e}", "#ff5252")
            
            time.sleep(3)

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
        
        for idx, quiz in enumerate(quizzes, 1):
            if not self.is_running: break
            self.progress_signal.emit(idx, total)
            self.log_signal.emit(tr("tg_processing").format(idx), "#4da3ff")

            media_files = self.get_media_files(self.bank_path, idx)
            reply_to = None

            # 1. Media
            if media_files:
                try:
                    # Telethon handles lists as albums
                    msg = await client.send_file(real_chat_id, media_files, caption=f"Question #{idx}")
                    reply_to = msg[-1].id if isinstance(msg, list) else msg.id
                except Exception as e:
                    self.log_signal.emit(f"Media Error: {e}", "#ff5252")

            # 2. Poll
            try:
                answers = [PollAnswer(TextWithEntities(o, []), bytes([i])) for i, o in enumerate(quiz["options"])]
                correct = [bytes([i]) for i in quiz["correct_options"]]
                is_quiz = len(correct) == 1
                
                expl = quiz.get("explanation", "").strip()
                
                poll = Poll(
                    id=0,
                    question=TextWithEntities(quiz["question"], []),
                    answers=answers,
                    closed=False,
                    public_voters=False,
                    multiple_choice=not is_quiz,
                    quiz=is_quiz,
                    close_period=None, close_date=None
                )
                
                # Solution (Explanation) in Poll 
                sol = expl if (is_quiz and expl) else None
                sol_ent = [] if sol else None

                poll_msg = await client.send_message(
                    real_chat_id,
                    file=InputMediaPoll(poll=poll, correct_answers=correct if is_quiz else None, 
                                        solution=sol, solution_entities=sol_ent),
                    reply_to=reply_to
                )
                self.log_signal.emit("Poll sent.", "#66bb6a")

                # Spoiler
                if (not is_quiz) or (is_quiz and sol):
                    correct_syms = [self.option_letters[i] for i in quiz["correct_options"] if 0 <= i < 10]
                    txt = f"✅ Answer: {', '.join(correct_syms)}"
                    if sol: txt += f"\n💡 Note: {sol}"
                    await client.send_message(real_chat_id, f"||{txt}||", parse_mode='md', reply_to=poll_msg.id)

            except Exception as e:
                 self.log_signal.emit(f"Poll Error: {e}", "#ff5252")

            await asyncio.sleep(3)
        
        await client.disconnect()

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
            QLineEdit, QComboBox { background-color: #333; border: 1px solid #555; padding: 6px; border-radius: 4px; color: #fff; }
            QPushButton { background-color: #444; border: 1px solid #666; padding: 8px; border-radius: 4px; color: white; }
            QPushButton:hover { background-color: #505050; border-color: #4da3ff; }
            QTextEdit { background-color: #1e1e1e; border: 1px solid #444; font-family: Consolas, monospace; }
            QProgressBar { border: 1px solid #444; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background-color: #1565C0; }
        """)

        # 1. Bank Selection
        gb_bank = QGroupBox(tr("tg_select_bank"))
        gb_bank_l = QVBoxLayout(gb_bank)
        self.combo_banks = QComboBox()
        self.load_banks()
        gb_bank_l.addWidget(self.combo_banks)
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
        
        # Chat ID (Common)
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

    def switch_mode(self):
        if self.radio_bot.isChecked():
            self.stack_bot.show()
            self.stack_user.hide()
        else:
            self.stack_bot.hide()
            self.stack_user.show()

    def load_creds(self):
        creds = ConfigManager.get_config_value("telegram", {})
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
        ConfigManager.set_config_value("telegram", data)
        QMessageBox.information(self, "Info", tr("tg_msg_saved"))
        return data

    def start_process(self):
        bank = self.combo_banks.currentText()
        if not bank:
            QMessageBox.warning(self, "Error", tr("tg_err_no_bank"))
            return
            
        bank_path = os.path.join("banks", bank)
        cfg = self.save_creds() # Auto save before run
        
        mode = "bot" if self.radio_bot.isChecked() else "user"
        
        self.log_view.clear()
        self.log_view.append(f"<span style='color: #888'>Starting in {mode.upper()} mode for bank: {bank}...</span>")
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.combo_banks.setEnabled(False)
        
        self.worker = TelegramWorker(bank_path, cfg, mode)
        self.worker.log_signal.connect(self.log_msg)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
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

    def on_finished(self):
        self.log_msg(tr("tg_done"), "#4CAF50")
        self.reset_ui()

    def on_error(self, err):
        self.log_msg(f"FATAL ERROR: {err}", "#ff0000")
        QMessageBox.critical(self, "Error", err)
        self.reset_ui()

    def reset_ui(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.combo_banks.setEnabled(True)

    def go_home(self):
        from ui.menu import MainMenu
        self.menu = MainMenu(None)
        self.menu.show()
        self.close()
# --- END OF FILE ui/telegram_sender.py ---