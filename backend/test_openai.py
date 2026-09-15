from openai import OpenAI
from app.config import get_settings


def main():
    print("Starting OpenAI API test...")

    settings = get_settings()

    if not settings.openai_api_key:
        print("ERROR: OpenAI API key is not loaded.")
        return

    print("OpenAI API key loaded: True")
    print("Model:", settings.openai_model)
    print("Sending test request...")

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly the word TEST."
                }
            ],
            temperature=0
        )

        result = response.choices[0].message.content

        print()
        print("SUCCESS!")
        print("OpenAI response:", result)

    except Exception as error:
        print()
        print("OPENAI API ERROR")
        print(type(error).__name__)
        print(str(error))


if __name__ == "__main__":
    main()