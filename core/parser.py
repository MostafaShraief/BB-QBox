# --- START OF FILE core/parser.py ---
import re
import json
import os
from typing import Any, Dict, List, Optional, Tuple

class QuestionParser:
    def __init__(self, config_path: str = "config.json") -> None:
        self.config = self._load_config(config_path)
        self.re_num = re.compile(r'^(\d+)\s*[-.)]') 
        self.re_opt = re.compile(r'^([a-zA-Zأ-ي])\s*[-.)]') 

    def _load_config(self, path: str) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {
            "answer_keywords": ["الحل", "الجواب", "الاجابة", "answer"],
            "note_keywords": ["ملاحظة", "توضيح", "شرح", "تنويه", "note", "hint"],
            "language": "ar"
        }
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return {**defaults, **json.load(f)}
        return defaults

    def _map_char_to_index(self, char: str) -> int:
        char = char.lower()
        if 'a' <= char <= 'z': return ord(char) - ord('a')
        arabic_chars = "أبجدهوزحطيكلمنسعفصقرشتثخذضظغ"
        if char in arabic_chars: return arabic_chars.index(char)
        return 0 

    def parse_text(self, file_path: str, split_lectures: bool = False, inline_note: bool = False, multiline_note: bool = False) -> List[Tuple[str, List[Dict[str, Any]]]]:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        banks = [] 
        current_questions = []
        current_q = None
        lecture_counter = 1
        last_q_num = 0
        
        # State flag for multiline notes
        collecting_note_mode = False

        for line in lines:
            line = line.strip()
            if not line: continue

            # --- Check New Question ---
            q_match = self.re_num.match(line)
            if q_match:
                q_num = int(q_match.group(1))
                
                # Check for numbering reset (Lectures)
                if split_lectures and q_num < last_q_num:
                    if current_questions:
                        banks.append((f"_Lecture_{lecture_counter}", current_questions))
                        current_questions = []
                        lecture_counter += 1
                        current_q = None 

                last_q_num = q_num
                collecting_note_mode = False # Reset note mode on new question

                current_q = {
                    "type": "quiz",
                    "question": f"{q_num}.",
                    "options": [],
                    "correct_options": [],
                    "explanation": ""
                }
                current_questions.append(current_q)
                continue

            # --- Parsing inside a question ---
            if current_q:
                # 1. Check for Answer
                found_ans = False
                for kw in self.config['answer_keywords']:
                    if kw in line:
                        match = re.search(re.escape(kw) + r'[:.\s-]*([a-zA-Zأ-ي0-9])', line)
                        if match:
                            ans_char = match.group(1)
                            current_q['correct_options'] = [self._map_char_to_index(ans_char)]
                            found_ans = True
                            
                            # Option 1: Inline Notes (on the same line)
                            if inline_note:
                                remaining_text = line[match.end():].strip()
                                # Clean common prefixes like "(" or "-"
                                remaining_text = re.sub(r'^[-:.)(]+', '', remaining_text).strip()
                                if remaining_text:
                                    if current_q['explanation']: current_q['explanation'] += "\n"
                                    current_q['explanation'] += remaining_text
                            else:
                                # Standard logic: check for explicit keyword "ملاحظة"
                                self._extract_explanation_standard(line[match.end():], current_q)

                            # Enable Multiline Note Mode if Answer found
                            if multiline_note:
                                collecting_note_mode = True
                            
                        break
                
                if found_ans: continue

                # 2. Check for Options
                # We only check options if we are NOT in note collecting mode
                # (Unless the user formatting is messy, but usually notes come last)
                opt_match = self.re_opt.match(line)
                if opt_match and not collecting_note_mode:
                    char = opt_match.group(1)
                    current_q['options'].append(f"{char})")
                    continue

                # 3. Handle Notes
                
                # A. Standard explicit keyword check (always active)
                is_explicit_note = False
                for kw in self.config['note_keywords']:
                    if kw in line:
                        if current_q['explanation']: current_q['explanation'] += "\n"
                        current_q['explanation'] += line
                        is_explicit_note = True
                        collecting_note_mode = True if multiline_note else False
                        break
                if is_explicit_note: continue

                # B. Multiline Implicit Notes (Lines under answer)
                if multiline_note and collecting_note_mode:
                    if current_q['explanation']: current_q['explanation'] += "\n"
                    current_q['explanation'] += line

        if current_questions:
            suffix = f"_Lecture_{lecture_counter}" if split_lectures and len(banks) > 0 else ""
            banks.append((suffix, current_questions))

        return banks

    def _extract_explanation_standard(self, text: str, q_obj: Dict[str, Any]) -> None:
        """Helper to find notes inside the answer line based on keywords only."""
        for kw in self.config['note_keywords']:
            if kw in text:
                start_idx = text.find(kw)
                note = text[start_idx:].strip()
                if q_obj['explanation']: q_obj['explanation'] += "\n"
                q_obj['explanation'] += note
                return

    def save_banks(self, banks_data: List[Tuple[str, List[Dict[str, Any]]]], base_folder: str, create_img_folder: bool = True) -> List[str]:
        results = []
        for suffix, data in banks_data:
            target_folder_name = base_folder + suffix
            full_path = os.path.join("banks", target_folder_name)
            os.makedirs(full_path, exist_ok=True)
            
            json_path = os.path.join(full_path, "bank.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            if create_img_folder:
                os.makedirs(os.path.join(full_path, "images"), exist_ok=True)
            results.append(full_path)
        return results
# --- END OF FILE core/parser.py ---