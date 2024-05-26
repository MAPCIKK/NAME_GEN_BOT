import requests
import logging  # модуль для сбора логов
MAX_GPT_TOKENS = 100
SYSTEM_PROMPT = [{'role': 'system', 'text': 'ты - бот-генератор имен. Сгенерируй имя, учитывая факторы, о которых просит пользователь. Не пиши никакого пояснительного текста, а просто выдавай список имен'}]


IAMTOKEN, FOLDER_ID = 'your IAM_TOKEN', 'your FOLDER_ID'

logging.basicConfig(filename='logs.txt', level=logging.INFO, 
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")

def count_gpt_tokens(messages):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion"
    headers = {
        'Authorization': f'Bearer {IAMTOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "messages": messages
    }
    try:
        return len(requests.post(url=url, json=data, headers=headers).json()['tokens'])
    except Exception as e:
        logging.error(e)  # если ошибка - записываем её в логи
        return 0

# запрос к GPT


def ask_gpt(text): 
    headers = { 
        'Authorization': f'Bearer {IAMTOKEN}', 
        'Content-Type': 'application/json' 
    } 
    data = { 
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite", 
        "completionOptions": { 
            "stream": False, 
            "temperature": 0.6, 
            "maxTokens": "200" 
        }, 
        "messages": [ 
            { 
                "role": "user", 
                "text": text 
            } 
        ] 
    } 
    response = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion", 
                             headers=headers, 
                             json=data) 
    if response.status_code == 200: 
        text = response.json()["result"]["alternatives"][0]["message"]["text"] 
        return text 
    else: 
        raise RuntimeError( 
            'Invalid response received: code: {}, message: {}'.format( 
                {response.status_code}, {response.text} 
            ) 
        )


def count_tokens(text):
    headers = {  # заголовок запроса, в котором передаем IAM-токен
        'Authorization': f'Bearer {IAMTOKEN}',  # token - наш IAM-токен
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",  # указываем folder_id
        "maxTokens": MAX_GPT_TOKENS,
        "text": text  # text - тот текст, в котором мы хотим посчитать токены
    }
    return len(
        requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
            json=data,
            headers=headers
        ).json()['tokens']
    )  # здесь, после выполнения запроса, функция возвращает количество токенов в text
