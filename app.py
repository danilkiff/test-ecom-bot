import os
import json
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env", override=False)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BRAND_NAME = os.getenv("BRAND_NAME", "Shoply")

if not OPENAI_API_KEY:
  raise RuntimeError("OPENAI_API_KEY не найден в .env")

client = OpenAI(api_key=OPENAI_API_KEY)


def load_json(path: Path):
  with path.open("r", encoding="utf-8") as f:
    return json.load(f)


FAQ = load_json(DATA_DIR / "faq.json")          # список {q, a}
ORDERS = load_json(DATA_DIR / "orders.json")    # словарь id -> данные заказа


def normalize(text: str):
  return re.findall(r"\w+", text.lower())


def find_best_faq_match(question: str, min_overlap: int = 1):
  q_tokens = set(normalize(question))
  best_entry = None
  best_score = 0

  for entry in FAQ:
    e_tokens = set(normalize(entry["q"]))
    score = len(q_tokens & e_tokens)
    if score > best_score:
      best_score = score
      best_entry = entry

  if best_score >= min_overlap:
    return best_entry
  return None


session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = LOGS_DIR / f"session_{session_id}.jsonl"

with log_path.open("a", encoding="utf-8") as f:
  meta = {
    "type": "meta",
    "timestamp": datetime.utcnow().isoformat(),
    "session_id": session_id,
    "brand": BRAND_NAME,
    "model": OPENAI_MODEL,
  }
  f.write(json.dumps(meta, ensure_ascii=False) + "\n")


def log_event(role: str, content: str, usage: dict | None = None, extra: dict | None = None):
  event = {
    "type": "message",
    "timestamp": datetime.utcnow().isoformat(),
    "role": role,
    "content": content,
  }
  if usage is not None:
    # usage: {prompt_tokens, completion_tokens, total_tokens}
    event["usage"] = usage
  if extra:
    event.update(extra)

  with log_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")


SYSTEM_PROMPT = f"""
Ты консольный бот поддержки магазина {BRAND_NAME}.
Правила:
- Отвечай кратко, вежливо, по делу.
- Используй ТОЛЬКО переданный контекст (FAQ или данные заказа).
- Не придумывай факты вне этого контекста.
- Если информации недостаточно, честно скажи об этом и предложи обратиться к оператору.
- Отвечай на русском языке.
""".strip()


def call_model(user_message: str, context: str, history: list[dict]):
  """
  history — список сообщений предыдущего диалога:
  [{role: "user"/"assistant", content: "..."}]
  """
  messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "system", "content": f"Контекст:\n{context}"}
  ]

  # limit ctx length: do not fly to the moon
  trimmed_history = history[-10:]
  messages.extend(trimmed_history)
  messages.append({"role": "user", "content": user_message})

  response = client.chat.completions.create(
    model=OPENAI_MODEL,
    messages=messages,
  )

  msg = response.choices[0].message
  usage = response.usage

  reply = msg.content.strip()
  usage_dict = {
    "prompt_tokens": usage.prompt_tokens,
    "completion_tokens": usage.completion_tokens,
    "total_tokens": usage.total_tokens,
  }

  return reply, usage_dict


def format_order_status(order_id: str, order: dict) -> str:
  status = order.get("status")

  if status == "in_transit":
    eta = order.get("eta_days")
    carrier = order.get("carrier", "")
    base = f"Заказ {order_id} в пути."
    parts = [base]
    if carrier:
      parts.append(f"Служба доставки: {carrier}.")
    if eta is not None:
      parts.append(f"Ориентировочный срок доставки: {eta} дн.")
    return " ".join(parts)

  if status == "delivered":
    delivered_at = order.get("delivered_at")
    if delivered_at:
      return f"Заказ {order_id} доставлен {delivered_at}."
    return f"Заказ {order_id} уже доставлен."

  if status == "processing":
    note = order.get("note", "Заказ в обработке.")
    return f"Заказ {order_id} в обработке. {note}"

  return f"Заказ {order_id}: статус {status or 'неизвестен'}."


def handle_order_command(text: str):
  parts = text.strip().split()
  if len(parts) != 2:
    return "Корректный формат: /order <id> (например: /order 12345)."

  order_id = parts[1]
  order = ORDERS.get(order_id)
  if not order:
    return f"Заказ с номером {order_id} не найден. Проверьте номер или обратитесь к оператору."

  return format_order_status(order_id, order)


def main():
  history: list[dict] = []

  print(f"{BRAND_NAME} support bot. Напишите вопрос или /order <id>. Для выхода — /exit")
  while True:
    try:
      user_input = input("Вы: ").strip()
    except (EOFError, KeyboardInterrupt):
      print("\nЗавершение сессии.")
      break

    if not user_input:
      continue

    if user_input.lower() in ("/exit", "exit", "/quit", "quit"):
      print("Бот: Хорошего дня!")
      log_event("user", user_input)
      log_event("assistant", "Хорошего дня!", usage=None, extra={"note": "session_end"})
      break

    log_event("user", user_input)

    if user_input.startswith("/order"):
      answer = handle_order_command(user_input)
      print(f"Бот: {answer}")
      log_event("assistant", answer, usage=None, extra={"source": "orders"})
      history.append({"role": "user", "content": user_input})
      history.append({"role": "assistant", "content": answer})
      continue

    faq_entry = find_best_faq_match(user_input, min_overlap=1)
    if faq_entry:
      context = f"Вопрос из FAQ: {faq_entry['q']}\nОтвет из FAQ: {faq_entry['a']}"
    else:
      context = (
        "Подходящий вопрос в FAQ не найден. "
        "Скажи, что у тебя нет достаточной информации, и предложи обратиться к оператору."
      )

    reply, usage = call_model(user_input, context, history)

    print(f"Бот: {reply}")
    log_event("assistant", reply, usage=usage, extra={"source": "faq" if faq_entry else "no_faq"})

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
  main()

