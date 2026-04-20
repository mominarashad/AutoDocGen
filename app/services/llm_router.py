from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os

# -----------------------
# GEMINI (High quality)
# -----------------------
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",   # safer than 2.5 (you had 503)
    api_key=os.getenv("GOOGLE_API_KEY")
)

# -----------------------
# GROQ (Fast + cheap)
# -----------------------
groq_llm = ChatGroq(
    model="llama3-70b-8192",
    api_key=os.getenv("GROQ_API_KEY")
)


# -----------------------
# SMART CALLER
# -----------------------
def call_llm(prompt, mode="gemini"):
    """
    mode:
      - "gemini" → high quality
      - "groq" → fast/cheap
    """

    try:
        if mode == "groq":
            return groq_llm.invoke(prompt)

        # default gemini
        return gemini_llm.invoke(prompt)

    except Exception as e:
        print("⚠️ Primary model failed, switching fallback:", e)

        # fallback strategy
        if mode == "gemini":
            return groq_llm.invoke(prompt)

        raise e
