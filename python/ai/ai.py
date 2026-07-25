import random
import time
import json
import os

BRAIN_FILE = "word_brain_data.json"
brain_model = {}

def load_brain():
    global brain_model
    if os.path.exists(BRAIN_FILE):
        try:
            with open(BRAIN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # CHUẨN: Tách chuỗi "tu1|tu2" trở lại thành Tuple (tu1, tu2)
                brain_model = {tuple(k.split("|")): v for k, v in data.items()}
            print("💾 Đã tải bộ não từ ngữ thành công!")
        except:
            print("⚠️ File bộ não bị lỗi, khởi tạo bộ não mới.")

def save_brain():
    with open(BRAIN_FILE, "w", encoding="utf-8") as f:
        # ĐÃ SỬA: Lưu chính xác bộ đôi từ k[0] và k[1] ngăn cách bằng dấu |
        str_key_model = {f"{k[0]}|{k[1]}": v for k, v in brain_model.items()}
        json.dump(str_key_model, f, ensure_ascii=False, indent=4)

def train_ai(text):
    words = text.split()
    if len(words) < 3:
        return
    for i in range(len(words) - 2):
        state = (words[i], words[i+1])
        next_word = words[i+2]
        if state not in brain_model:
            brain_model[state] = []
        brain_model[state].append(next_word)
    save_brain()

def ai_generate_reply(start_text):
    if not brain_model:
        return "Tôi chưa được học từ nào cả! 🤖"
        
    start_words = start_text.split()
    
    # Chọn cặp từ khởi đầu dựa trên câu gõ vào
    if len(start_words) >= 2:
        state = (start_words[-2], start_words[-1])
        if state not in brain_model:
            state = random.choice(list(brain_model.keys()))
    else:
        state = random.choice(list(brain_model.keys()))
        
    # Tạo danh sách kết quả ban đầu từ cặp từ khóa
    reply_words = [state[0], state[1]]
    
    # AI tự động mò đường nhả câu dài (tối thiểu 5 từ, tối đa 15 từ)
    for _ in range(15):
        if state in brain_model and brain_model[state]:
            next_word = random.choice(brain_model[state])
            reply_words.append(next_word)
            state = (state[1], next_word)  # Dịch chuyển trạng thái sang từ tiếp theo
        else:
            # Nếu hết đường đi nhưng câu ngắn quá, bốc đại một từ ngẫu nhiên trong não để nói tiếp
            if len(reply_words) < 5:
                state = random.choice(list(brain_model.keys()))
                reply_words.extend([state[0], state[1]])
            else:
                break
            
    return " ".join(reply_words)

# --- MAIN ---
print("🤖 AI Markov Theo Từ (Word-level) Đã Vá Lỗi!")
load_brain()

while True:
    you_input = input("\nYou: ").strip()
    if you_input.lower() == "exit":
        break
        
    train_ai(you_input)
    reply_text = ai_generate_reply(you_input)
    
    time.sleep(0.05)
    print(f"Me: {reply_text}")
