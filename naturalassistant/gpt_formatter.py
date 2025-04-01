import openai

async def format_response_with_gpt(result):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Red, a witty, helpful server assistant."},
                {"role": "user", "content": result}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except Exception:
        return "Sorry, I’m running low on power, try again later."
