#!/usr/bin/env python3
"""Advanced chatbot in pure Python with bilingual vocabulary support.

This chatbot uses an external vocabulary file to provide English-Vietnamese
translation examples and to help users learn basic vocabulary.
"""

import datetime
import random
import re
import requests
from bs4 import BeautifulSoup

from googlesearch import search
from vocabulary import translate, random_word_pair, all_pairs
from neural_network import create_huge_network, create_ultra_network, train_xor_model, sample_prediction
from virtual_network import create_virtual_network_with_min_params
import subprocess


def contains_keyword(text, keywords):
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords)


def google_search(query, max_results=3):
    try:
        results = list(search(query, num_results=max_results, lang='en', sleep_interval=1))
        if results:
            return results
    except Exception:
        pass
    return duckduckgo_search(query, max_results=max_results)


def duckduckgo_search(query, max_results=3):
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    }
    try:
        response = requests.post(url, data={"q": query}, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for result in soup.find_all("a", class_="result__a"):
            href = result.get("href")
            if href:
                links.append(href)
            if len(links) >= max_results:
                break
        return links
    except Exception:
        return []


exit_keywords = ["tạm biệt", "bye", "thoát", "exit", "quit", "ngủ", "hẹn gặp lại"]
greeting_keywords = ["xin chào", "chào", "hello", "hi", "hey"]
name_questions = ["tên bạn", "bạn tên gì", "gọi bạn", "tên là gì"]
thanks_keywords = ["cảm ơn", "thank you", "thanks"]
time_keywords = ["mấy giờ", "giờ", "time", "ngày", "today", "ngày nào"]
math_keywords = ["cộng", "trừ", "nhân", "chia", "plus", "minus", "times", "divide"]
weather_keywords = ["thời tiết", "weather"]
help_keywords = ["giúp", "help", "hướng dẫn", "cách" ]
joke_keywords = ["joke", "đùa", "cười"]
forget_keywords = ["quên", "đừng nhớ"]
vocab_keywords = ["từ vựng", "vocab", "dịch", "translate", "dịch từ", "dịch nghĩa"]
search_keywords = ["tìm kiếm", "google", "search", "tra cứu", "tìm"]
network_keywords = ["mạng neuron", "tạo mạng neuron", "neural network", "mạng nơ rô", "mô hình", "create network"]
train_keywords = ["huấn luyện", "train", "tập huấn", "đào tạo"]

filegen_keywords = ["tạo file lớn", "sinh file", "tạo file", "tạo tệp"]

knowledge = {
    "ai": "Tôi là một chatbot Python được thiết kế để giống AI hơn, với ký ức ngắn hạn và phản hồi dựa trên ngữ cảnh.",
    "python": "Python là một ngôn ngữ lập trình dễ học, mạnh mẽ và rất phù hợp để viết chatbot đơn giản.",
    "openai": "OpenAI là một công ty nghiên cứu AI tạo ra các mô hình lớn như GPT. Tuy nhiên, tôi chạy hoàn toàn cục bộ trên Python.",
    "machine learning": "Machine learning là một nhánh AI giúp máy tính học từ dữ liệu và đưa ra dự đoán.",
}

fallback_replies = [
    "Mình chưa hiểu rõ ý bạn. Bạn có thể diễn đạt khác không?",
    "Nghe có vẻ thú vị, nhưng mình cần biết rõ hơn để trả lời chính xác.",
    "Hãy hỏi mình một điều đơn giản hơn, mình sẵn sàng trả lời!",
    "Mình là chatbot đơn giản, nhưng mình đang cố gắng giống AI thật hơn đấy."
]

name_patterns = [
    r"tôi tên là ([a-zạáàảãạăắằẳẵặâấầẩẫậđẹéèẻẽẹêếềểễệỉịìĩòóỏõọôốồổỗộơớờởỡợưứừửữựỳýỷỹỵ\w]+)",
    r"mình tên là ([a-zạáàảãạăắằẳẵặâấầẩẫậđẹéèẻẽẹêếềểễệỉịìĩòóỏõọôốồổỗộơớờởỡợưứừửữựỳýỷỹỵ\w]+)",
]

class Chatbot:
    def __init__(self, name="Ava"):
        self.name = name
        self.user_name = None
        self.history = []

    def normalize(self, text):
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9ạáàảãạăắằẳẵặâấầẩẫậđẹéèẻẽẹêếềểễệỉịìĩòóỏõọôốồổỗộơớờởỡợưứừửữựỳýỷỹỵ\s\+\-\*\/\.\?]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def remember(self, user_input):
        self.history.append(user_input)
        if len(self.history) > 10:
            self.history.pop(0)

    def parse_name(self, text):
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).capitalize()
        return None

    def answer_math(self, text):
        clean = text.replace("x", "*").replace("nhân", "*").replace("chia", "/").replace("cộng", "+").replace("trừ", "-")
        clean = re.sub(r"[^0-9\.\+\-\*\/\s]", "", clean)
        try:
            result = eval(clean)
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return f"Kết quả là {result}."
        except Exception:
            return None

    def answer_time(self, text):
        now = datetime.datetime.now()
        if any(word in text for word in ["hôm nay", "ngày"]):
            return f"Hôm nay là {now.strftime('%A, %d/%m/%Y')}"
        return f"Bây giờ là {now.strftime('%H:%M:%S')}"

    def answer_knowledge(self, text):
        for keyword, response in knowledge.items():
            if keyword in text:
                return response
        return None

    def answer_search(self, text):
        if contains_keyword(text, search_keywords):
            normalized = self.normalize(text)
            query = normalized
            for keyword in search_keywords:
                query = query.replace(keyword, "")
            query = query.strip()
            if not query:
                return "Hãy nói rõ nội dung cần tìm kiếm. Ví dụ: 'tìm kiếm chatbot Python'."
            results = google_search(query, max_results=3)
            if not results:
                return "Mình không tìm thấy kết quả nào."
            return "Kết quả tìm kiếm:\n" + "\n".join(results)
        return None

    def answer_network(self, text):
        if contains_keyword(text, network_keywords):
            if contains_keyword(text, train_keywords):
                network = create_ultra_network()
                history = train_xor_model(network, epochs=30)
                predictions = sample_prediction(network)
                results = "; ".join(f"{inputs}->{output}" for inputs, output in predictions)
                return (
                    f"Tôi đã tạo mạng neuron siêu lớn với {network.parameter_count()} tham số và huấn luyện trên XOR. "
                    f"Mất {len(history)} epoch, mất giảm xuống {history[-1]:.6f}. Kết quả ví dụ: {results}"
                )
            # support creating a virtual network with >=300 million parameters
            if "300" in text or "300000000" in text or "300 triệu" in text:
                vnet = create_virtual_network_with_min_params(300_000_000)
                return (
                    f"Tôi tạo một mạng ảo với {vnet.parameter_count()} tham số (không cấp phát bộ nhớ đầy đủ).\n"
                    f"{vnet.summary()}"
                )
            network = create_ultra_network()
            return (
                f"Tôi tạo được mạng neuron siêu lớn với {network.parameter_count()} tham số. "
                "Gõ 'huấn luyện mạng neuron' để thử trên XOR."
            )
        return None

    def answer_filegen(self, text):
        if contains_keyword(text, filegen_keywords):
            # create a large file using the helper script
            # run create_large_files.py to create one file with 300000 lines
            try:
                subprocess.check_call(["python3", "create_large_files.py", "--count", "1", "--lines", "300000", "--prefix", "large_"], cwd=".")
                return "Đã tạo file lớn: large_1.txt (300000 dòng)."
            except Exception as e:
                return f"Không thể tạo file lớn: {e}"
        return None

    def answer_vocab(self, text):
        if contains_keyword(text, vocab_keywords):
            normalized = self.normalize(text)
            if "ngẫu nhiên" in normalized or "random" in normalized or "ví dụ" in normalized:
                eng, viet = random_word_pair()
                return f"Một từ vựng: '{eng}' nghĩa là '{viet}'."

            result = translate(normalized)
            if result:
                return f"Dịch: {result}"

            # Try word extraction for translation requests
            candidates = normalized.split()
            for word in candidates:
                translation = translate(word)
                if translation:
                    return f"Dịch: {translation}"

            all_items = all_pairs()
            sample = random.choice(all_items)
            return f"Mình chưa rõ từ này, đây là một cặp từ gợi ý: '{sample[0]}' = '{sample[1]}'."
        return None

    def choose_response(self, text):
        vocab_answer = self.answer_vocab(text)
        if vocab_answer:
            return vocab_answer

        if contains_keyword(text, greeting_keywords):
            return random.choice([
                f"Chào bạn! Tôi là {self.name}. Bạn muốn trò chuyện về gì?",
                "Xin chào! Mình có thể giúp gì cho bạn hôm nay?",
            ])

        if contains_keyword(text, name_questions):
            return f"Mình tên là {self.name}. Rất vui được gặp bạn!"

        if contains_keyword(text, thanks_keywords):
            return random.choice([
                "Không có gì!", "Rất vui khi được giúp.", "Bạn cứ hỏi thêm khi cần nhé."
            ])

        if contains_keyword(text, joke_keywords):
            return random.choice([
                "Tại sao máy tính không bao giờ đói? Vì nó luôn có byte!", 
                "Tôi là AI mà, tôi kể chuyện cười kém phết, nhưng vẫn dễ thương nhé."
            ])

        if contains_keyword(text, weather_keywords):
            return "Mình chưa có dữ liệu thời tiết thực, nhưng mình có thể kể chuyện hoặc giúp bạn học Python."

        if contains_keyword(text, help_keywords):
            return "Mình có thể trả lời câu hỏi đơn giản, xử lý một số phép toán, dịch từ vựng, tìm kiếm Google, tạo hoặc huấn luyện mạng neuron, nhận diện tên, và giữ lịch sử cuộc trò chuyện nhỏ."

        search_answer = self.answer_search(text)
        if search_answer:
            return search_answer

        network_answer = self.answer_network(text)
        if network_answer:
            return network_answer

        name = self.parse_name(text)
        if name:
            self.user_name = name
            return f"Rất vui được biết bạn tên {self.user_name}! Mình sẽ ghi nhớ tên này trong cuộc trò chuyện hôm nay."

        if "tôi là" in text or "mình là" in text:
            if self.user_name:
                return f"Rất vui gặp lại bạn, {self.user_name}! Bạn muốn nói gì thêm không?"
            return "Bạn vừa cho mình biết về bản thân, cảm ơn nhé!"

        if contains_keyword(text, time_keywords):
            return self.answer_time(text)

        if contains_keyword(text, math_keywords):
            math_answer = self.answer_math(text)
            if math_answer:
                return math_answer

        if any(keyword in text for keyword in forget_keywords):
            self.history.clear()
            self.user_name = None
            return "Mình đã xóa một số ký ức tạm thời. Bắt đầu lại nhé."

        knowledge_answer = self.answer_knowledge(text)
        if knowledge_answer:
            return knowledge_answer

        if self.history:
            return random.choice([
                "Mình đang suy nghĩ... Có gì khác bạn muốn hỏi không?",
                "Câu hỏi này khá thú vị. Bạn muốn mình trả lời bằng cách khác không?",
                "Mình chưa chắc chắn ý bạn lắm, bạn có thể nói rõ hơn không?"
            ])

        return random.choice(fallback_replies)

    def respond(self, user_input):
        normalized = self.normalize(user_input)
        self.remember(normalized)
        return self.choose_response(normalized)


def run_chatbot():
    bot = Chatbot(name="Ava")
    print("=== Ava Chatbot ===")
    print("Hãy nhập câu hỏi. Gõ 'tạm biệt' hoặc 'exit' để kết thúc.")

    while True:
        try:
            user_input = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Tạm biệt! Hẹn gặp lại.")
            break

        if not user_input:
            print("Bot: Xin hãy nhập câu hỏi để mình trả lời.")
            continue

        normalized = bot.normalize(user_input)
        if contains_keyword(normalized, exit_keywords):
            print("Bot: Tạm biệt! Chúc bạn một ngày tốt lành.")
            break

        answer = bot.respond(user_input)
        print(f"Bot: {answer}")


if __name__ == "__main__":
    run_chatbot()
