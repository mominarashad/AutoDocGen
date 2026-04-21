from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential
import os

# -----------------------
# MODELS
# -----------------------

gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",   # ✅ FIXED
    temperature=0.3,
    api_key=os.getenv("GOOGLE_API_KEY")
)

groq_llm = ChatGroq(
    model="llama3-70b-8192",
    api_key=os.getenv("GROQ_API_KEY")
)

# -----------------------
# RETRY (Gemini only)
# -----------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8))
def _call_gemini(prompt):
    return gemini_llm.invoke(prompt)


# -----------------------
# MAIN ROUTER
# -----------------------
def call_llm(prompt, mode="gemini"):
    """
    Unified LLM caller

    mode:
      - gemini → high quality
      - groq → fast
    """

    try:
        if mode == "groq":
            return groq_llm.invoke(prompt)

        # default: gemini
        return _call_gemini(prompt)

    except Exception as e:
        print("⚠️ Primary LLM failed → fallback:", e)

        # fallback to Groq ALWAYS
        try:
            return groq_llm.invoke(prompt)
        except Exception as e2:
            print("❌ Groq also failed:", e2)
            return "⚠️ LLM failed completely"
