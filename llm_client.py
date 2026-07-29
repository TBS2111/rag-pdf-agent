import os
from groq import Groq, APIStatusError

class GroqClient:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")

        self.model_name = model_name or os.environ.get(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        )
        self.client = Groq(api_key=api_key)

    def ask(self, question: str, context: str | None = None) -> str:
        """Sends user question to Groq LLM, using context if relevant or general knowledge as fallback."""
        try:
            if context:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant. Use the provided document context to answer "
                            "the user's question if it is relevant. If the question is unrelated to "
                            "the context, ignore the context and answer using your general knowledge."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {question}"
                    }
                ]
            else:
                messages = [{"role": "user", "content": question}]

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""

        except APIStatusError as e:
            if e.status_code == 429:
                return "The model is currently busy or rate-limited. Please try again in a few moments."
            return f"Groq API Error: {e.message}"
        except Exception as e:
            return f"Error: {str(e)}"

# Alias for backwards compatibility
GeminiClient = GroqClient