import os
import psycopg2
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", 5433)),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "dbname": os.getenv("PG_DATABASE"),
}
MODEL_EMB = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MODEL_LLM = os.getenv("LLM_MODEL", "gpt-4o-mini")


def get_embedding(text):
    return openai.embeddings.create(input=text, model=MODEL_EMB).data[0].embedding


def embedding_to_pgvector_str(embedding):
    return "[" + ",".join(map(str, embedding)) + "]"


def search_similar(embedding_str, limit=3):
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, json_path, raw_content, embedding <-> %s AS distance
                FROM embedding
                WHERE embedding <-> %s < 0.35
                ORDER BY distance
                LIMIT %s;
                """,
                (embedding_str, embedding_str, limit),
            )
            return cur.fetchall()


def ask_llm(question, contexts):
    context_text = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(contexts)])
    prompt = f"""
Bạn là một trợ lý du lịch thông minh, luôn lắng nghe và thấu hiểu nhu cầu của khách hàng.

Dựa trên những thông tin bên dưới, hãy trả lời câu hỏi của người dùng một cách tự nhiên, thân thiện, ngắn gọn nhưng đủ ý.

Đồng thời hãy để ý đến thái độ và cảm xúc của khách để đưa ra câu trả lời phù hợp với ngữ cảnh.

Quan trọng: Không được bịa quá lố hoặc thêm thông tin không có trong dữ liệu tham khảo. Chỉ dựa vào thông tin có sẵn trong phần dưới đây mà trả lời.

Bạn là trợ lý du lịch thông minh. Dựa trên thông tin bên dưới, hãy trả lời câu hỏi người dùng.

Nếu thông tin không có trong dữ liệu này, hãy trả lời: "Xin lỗi, mình chưa có thông tin về điều đó."

Thông tin tham khảo: {context_text}

Câu hỏi: {question}

Hãy trả lời một cách ngắn gọn, thân thiện và chính xác.


Thông tin tham khảo:
{context_text}

Câu hỏi của khách:
{question}

Hãy trả lời ngay nhé!


"""
    res = openai.chat.completions.create(
        model=MODEL_LLM,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content.strip()


class PgVectorStore:
    """Class bao bọc các hàm embedding, tìm kiếm và hỏi LLM"""

    def __init__(self):
        pass

    def get_embedding(self, text: str):
        return get_embedding(text)

    def embedding_to_str(self, embedding):
        return embedding_to_pgvector_str(embedding)

    def search(self, embedding_str, limit=3):
        return search_similar(embedding_str, limit)

    def ask(self, question, contexts):
        return ask_llm(question, contexts)
    async def initialize(self):
        # Đây có thể là bước chuẩn bị, ví dụ kiểm tra bảng đã tồn tại hay chưa
        print("Initializing PgVectorStore...")

        # Nếu không có việc gì đặc biệt, có thể để trống hoặc pass
        pass