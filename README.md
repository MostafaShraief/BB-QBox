# BB-QBox (Blue Bits Question Box) 📦✂️

**BB-QBox** is an all-in-one desktop application designed for medical students, educators, and content creators to manage, process, and automate the creation of digital question banks. 

Whether you are starting from a scanned PDF, a text file, or want to publish your bank to Telegram, BB-QBox provides a streamlined, professional workflow.

---

## 🌟 Key Features

### 1. ✂️ Image Cropper (PDF/Image)
*   **PDF to Image:** Load PDF pages and crop specific questions.
*   **Merge Logic:** Select multiple parts of a question (header, options, image) and merge them into a single image automatically.
*   **Auto-Detection:** Smart layout analysis to detect question blocks in PDFs.
*   **Alignment:** Choose between Right, Center, or Left alignment for merged images.

### 2. 📝 Text Extractor (Txt to JSON)
*   **Smart Parsing:** Converts raw `.txt` files into structured `bank.json` files.
*   **Keyword Support:** Customizable keywords for "Answer", "Explanation", and "Notes".
*   **Lecture Splitting:** Automatically detects numbering resets (e.g., 50 back to 1) to split a single file into multiple lecture folders.
*   **Multiline Logic:** Capture detailed explanations that span multiple lines.

### 3. 👁️ Question Bank Viewer
*   **Interactive Quiz:** Test yourself with a sleek UI; hide or reveal answers with a single click.
*   **Full Editor:** Modify question text, change options, replace images, or add explanations directly within the viewer.
*   **RTL Support:** Native Arabic support with Right-to-Left layout.

### 4. ✈️ Telegram Publisher (New!)
*   **Bot Mode:** Uses the Telegram Bot API to send questions as interactive polls with media attachments.
*   **User Mode:** Uses the Telethon (User API) for advanced features and higher limits.
*   **Album Support:** Automatically sends multiple images for a single question as a "Media Group".
*   **Auto-Spoiler:** Protects the correct answer and explanation using Telegram's spoiler formatting.

---

## 🛠️ Installation

### Prerequisites
- Python 3.9 or higher.

### Step 1: Clone the repository
```bash
git clone https://github.com/MostafaShraief/BB-QBox.git
cd bb-qbox
```

### Step 2: Install dependencies
```bash
pip install PyQt6 PyMuPDF Pillow requests telethon
```

### Step 3: Run the application
```bash
python main.py
```

---

## 📁 Project Structure

```text
project_root/
│
├── main.py                # Application entry point
├── config.json            # User preferences and keyboard shortcuts
│
├── core/                  # Backend Logic
│   ├── config.py          # Configuration manager
│   ├── locales.py         # Multi-language translations (AR/EN)
│   ├── parser.py          # Txt parsing engine
│   └── pdf_ops.py         # PDF rendering and image merging
│
├── ui/                    # Graphical Interface
│   ├── menu.py            # Main hub
│   ├── canvas.py          # Cropping tool logic
│   ├── extractor.py       # Text conversion UI
│   ├── viewer.py          # Bank browser and editor
│   └── telegram_sender.py # Telegram automation UI
│
└── banks/                 # Default directory for generated banks
```

---

## 🌍 Language Support
The application detects the language preference from `config.json`. It fully supports:
- **Arabic (العربية):** Full RTL layout and localized terminology.
- **English:** Standard LTR layout.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

---

### مـلخص بالعـربية 🇸🇦
**برنامج BB-QBox** هو أداة متكاملة لإدارة بنوك الأسئلة. يتيح لك قص الأسئلة من ملفات PDF، تحويل الملفات النصية إلى صيغة JSON المنظمة، استعراض واختبار نفسك في البنوك، وأخيراً نشر الأسئلة بشكل آلي على قنوات التيليجرام عبر البوتات أو حسابات المستخدمين مع دعم كامل للصور والاستفتاءات التفاعلية.
