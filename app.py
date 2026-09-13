import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# PROMPT: FORMAL (Cold, factual, analytical)
PROMPT_FORMAL = (
    "Ты — холодный, расчетливый инженер-аналитик. Твоя задача: проанализировать идею пользователя "
    "и найти в ней критические уязвимости. Используй сухие факты, технические термины и логику. "
    "Каждый из 6 пунктов должен затрагивать УНИКАЛЬНУЮ тему (Железо, Электричество, Сеть, Время, Риски, Деньги). "
    "НИКАКОЙ повторной темы (например, не пиши про свет дважды!). "
    "НИКАКОЙ магии, фантастики или эмоций. Только сухие факты. "
    "Выдавай ответ ТОЛЬКО в виде списка: '- [текст]'. "
    "Каждый пункт — новая строка. Без вступлений и заключений."
)

# PROMPT: ROAST (Aggressive, sarcastic, brutal)
PROMPT_ROAST = (
    "Ты — беспощадный Дьявол-критик. Твоя цель — разнести идею пользователя в пух и прах сарказмом. "
    "Будь жестким, вызывай осознание ошибки через насмешку. Используй сленг, но оставайся в рамках реальности. "
    "Каждый из 6 пунктов должен затрагивать УНИКАЛЬНУЮ тему (Железо, Электричество, Сеть, Время, Риски, Деньги). "
    "НИКАКОЙ повторной темы (не пиши про свет дважды!). "
    "НИКАКОЙ фантастики или магии. Только реальный, жестокий мир. "
    "Выдавай ответ ТОЛЬКО в виде списка: '- [текст]'. "
    "Каждый пункт — новая строка. Без вступлений и заключений."
)

def get_client():
    load_dotenv(override=True)
    api_key = (os.getenv("GONKA_BROKER_API_KEY") or "").strip()
    base_url = (os.getenv("GONKA_BROKER_URL") or "").strip().rstrip("/")
    if not api_key or not base_url:
        raise RuntimeError(
            "Missing configuration in .env: GONKA_BROKER_URL or GONKA_BROKER_API_KEY."
        )
    return OpenAI(api_key=api_key, base_url=base_url, timeout=90.0)

def get_model():
    load_dotenv(override=True)
    model = (os.getenv("GONKA_MODEL") or "").strip()
    if not model:
        raise RuntimeError("Missing GONKA_MODEL in .env.")
    return model

def analyze_idea(idea: str, mode: str) -> str:
    client = get_client()
    prompt = PROMPT_FORMAL if mode == 'formal' else PROMPT_ROAST
    
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": idea},
        ],
        temperature=0.8,
    )
    return (response.choices[0].message.content or "").strip()

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/analyze")
def analyze_idea_endpoint():
    payload = request.get_json(silent=True) or {}
    idea = (payload.get("idea") or request.form.get("idea") or "").strip()
    mode = payload.get("mode", "roast") # Default to roast
    
    if not idea:
        return jsonify({"error": "Введите идею, чтобы убить её!"}), 400

    try:
        text = analyze_idea(idea, mode)
        # Split into lines, strip whitespace, and remove leading "- " or "1. " etc.
        items = []
        for line in text.split('\n'):
            cleaned_line = line.strip()
            if cleaned_line:
                # Remove leading "- ", "1. ", "1) ", "* ", etc.
                cleaned_line = re.sub(r"^\s*(?:\d+[.)]\s*|[-*]\s*)", "", cleaned_line)
                items.append(cleaned_line)
        
        if not items:
            items = [text]
            
        return jsonify({"text": text, "items": items[:6]}) # Up to 6 points of critique
    except Exception as exc:
        print(f"Error analyzing idea: {exc}")
        return jsonify({"error": f"Критический сбой: {str(exc)}"}), 502

if __name__ == "__main__":
    app.run(debug=True)
