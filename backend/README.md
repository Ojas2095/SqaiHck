# 🌿 AYUSH AI

AI-enabled Integrated Early Warning, Treatment & Lifestyle Recommendation System

## Requirements

- Python 3.10+
- Git
- Internet connection (first run)
- Hugging Face Token

## 1. Clone the Repository

```bash
git clone <repository_url>
cd AYUSH-AI
```

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a file named `.env`

```env
HF_TOKEN=your_huggingface_token
```

## 5. Required Datasets

- AyurGenixAI_Dataset.xlsx
- Ayurveda Texts (Kaggle)
- BhashaBench-Ayur (auto download or `python data.py`)
- AYUSH_hospital_beds_and_dispensaries.csv

## 6. Initialize Database

```bash
python ayush_system.py
```

## 7. Run Backend

```bash
python web_app.py
```

or

```bash
uvicorn web_app:app --reload
```

## 8. Open Browser

http://127.0.0.1:8000

Swagger:

http://127.0.0.1:8000/docs

ReDoc:

http://127.0.0.1:8000/redoc

## Project Structure

```text
AYUSH-AI/
├── ayush_system.py
├── web_app.py
├── data_loader.py
├── data.py
├── index.html
├── requirements.txt
├── .env
├── ayush.db
├── Ayurveda Books/
├── AyurGenixAI_Dataset.xlsx
└── AYUSH_hospital_beds_and_dispensaries.csv
```

## Troubleshooting

- Reinstall packages:

```bash
pip install -r requirements.txt
```

- Recreate database:

```bash
python ayush_system.py
```

- Stop server:

Press CTRL + C
