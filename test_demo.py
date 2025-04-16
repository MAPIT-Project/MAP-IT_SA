import requests

def test_demo_api():
    payload = {
        'question': 'What is the impact of climate change on biodiversity?',
    }

    r = requests.post('http://localhost:8000/api/demo', json=payload)

    print(r.status_code)
    print(r.text)


if __name__ == "__main__":
    test_demo_api()