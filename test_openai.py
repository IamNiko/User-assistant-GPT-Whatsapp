
from decouple import config
from openai import OpenAI

client = OpenAI(api_key=config('OPENAI_API_KEY'))

def test_gpt4():
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "Eres un asistente para máquinas expendedoras P-KAP"
            },
            {
                "role": "user",
                "content": "Hay un producto caído en la máquina y ya pagué"
            }]
        )
        print("\nRespuesta GPT-4:", response.choices[0].message.content)
        return True
    except Exception as e:
        print("\nError GPT-4:", str(e))
        return False

if __name__ == "__main__":
    print("\nTesteando conexión GPT-4...")
    test_gpt4()
