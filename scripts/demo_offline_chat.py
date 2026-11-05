"""Local terminal demo using the SAME guarded LR service and chat runtime as HTTP."""
import os
from app.backend.chat import ChatRuntime
from app.backend.prediction import LRPredictionService


def main():
    os.environ['DISEASE_CHAT_MODE'] = 'offline'
    runtime = ChatRuntime.open(LRPredictionService.load(os.environ['DISEASE_API_STORAGE_ROOT']))
    print('Offline rules + approved LR tuned. /reset để bắt đầu lại; /quit để dừng.')
    key = None
    while True:
        text = input('Bạn: ')
        if text == '/quit':
            break
        reply = runtime.handle('' if text == '/reset' else text, session_id=key, reset=text == '/reset')
        key = reply['session_id']
        print(reply['message'])
        print('Trạng thái:', reply['symptom_states'])
        if reply['predictions']:
            for rank, item in enumerate(reply['predictions']['presentation']['top3'], 1):
                print(rank, item['display_label'], 'Điểm tự tin dự đoán (%):', item['score_text'])
            for warning in reply['predictions']['presentation']['warnings']:
                print(warning)


if __name__ == '__main__':
    main()
