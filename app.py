from flask import Flask, request, render_template, jsonify
from transformers import MarianMTModel, MarianTokenizer, WhisperProcessor, WhisperForConditionalGeneration
from gtts import gTTS
import os
import logging
import librosa  # Загрузка аудиофайла с помощью librosa

# Настройка логирования
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Пути к моделям
whisper_model_path = "openai/whisper-small.en"
opus_mt_model_path = "Helsinki-NLP/opus-mt-en-ru"

try:
    # Загрузка модели Whisper
    whisper_processor = WhisperProcessor.from_pretrained(whisper_model_path)
    whisper_model = WhisperForConditionalGeneration.from_pretrained(whisper_model_path)

    # Загрузка модели Opus-MT
    opus_mt_tokenizer = MarianTokenizer.from_pretrained(opus_mt_model_path)
    opus_mt_model = MarianMTModel.from_pretrained(opus_mt_model_path)

except Exception as e:
    logging.error(f"Ошибка при загрузке моделей: {e}")
    raise

# Создание приложения
app = Flask(__name__, template_folder='templates', static_folder='static')

# Временные файлы для обработки
TEMP_AUDIO_PATH = "models/output/temp_audio.wav"
TEMP_TEXT_PATH = 'models/output/english_text.txt'
TEMP_TRANSLATED_PATH = 'models/output/translated_text.txt'


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process_stage", methods=["POST"])
def process_stage():
    try:
        data = request.get_json()
        stage = data.get("stage")
        text_input = data.get("text_input")

        # Проверка ввода текста
        if stage == "start":

            if not text_input:
                return jsonify({"error": "Текст не предоставлен."}), 400

            if len(text_input) > 50:
                return jsonify({"error": "Текст не должен превышать 50 символов."}), 400

            return jsonify({"next_stage": "tts"})

        elif stage == "tts":
            # Генерация аудио из текста (TTS)
            try:
                lang = 'ru'
                phrase = text_input
                gtts = gTTS(phrase, lang=lang)
                gtts.save(TEMP_AUDIO_PATH)  # Сохранение аудиофайла

            except Exception as exc:
                logging.error(f"Ошибка при генерации аудио: {exc}")
                return jsonify({"error": "Ошибка генерации аудио."}), 500
            return jsonify({"next_stage": "whisper"})

        elif stage == "whisper":
            # Преобразование аудио в текст (Whisper)
            if not os.path.exists(TEMP_AUDIO_PATH):
                return jsonify({"error": "Аудиофайл не найден."}), 500

            try:
                audio_array, sampling_rate = librosa.load(TEMP_AUDIO_PATH, sr=16000)
                inputs = whisper_processor(audio_array, sampling_rate=sampling_rate, return_tensors="pt")
                predicted_ids = whisper_model.generate(inputs["input_features"])
                english_text = whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

                with open(TEMP_TEXT_PATH, 'w') as file:  # Сохраняем текст в файл
                    file.write(english_text)
            except Exception as exc:
                logging.error(f"Ошибка при обработке аудио: {exc}")
                return jsonify({"error": "Ошибка обработки аудио."}), 500
            return jsonify({"next_stage": "opus_mt"})

        elif stage == "opus_mt":
            # Перевод текста на русский (Helsinki-NLP/Opus-MT)
            try:
                with open(TEMP_TEXT_PATH, 'r') as file:
                    english_text = file.read().strip()

                if not english_text:
                    return jsonify({"error": "Текст для перевода отсутствует."}), 400

                opus_inputs = opus_mt_tokenizer(english_text, return_tensors="pt")
                translated_ids = opus_mt_model.generate(**opus_inputs)
                translated_text = opus_mt_tokenizer.decode(translated_ids[0], skip_special_tokens=True)

                with open(TEMP_TRANSLATED_PATH, 'w') as file:  # Сохраняем текст в файл
                    file.write(translated_text)
            except Exception as exc:
                logging.error(f"Ошибка при переводе текста: {exc}")
                return jsonify({"error": "Ошибка перевода текста."}), 500
            return jsonify({"next_stage": "result"})

        elif stage == "result":
            # Вывод результата
            try:
                with open(TEMP_TRANSLATED_PATH, 'r') as file:
                    translated_text = file.read().strip()

                if not translated_text:
                    return jsonify({"error": "Результат перевода отсутствует."}), 400
            except Exception as exc:
                logging.error(f"Ошибка при чтении перевода: {exc}")
                return jsonify({"error": "Ошибка получения результата."}), 500

            return jsonify({"next_stage": "end", "result": translated_text})

        elif stage == "end":
            # Завершение обработки
            return jsonify({"next_stage": None, "result": None})

        return jsonify({"error": "Неизвестный этап."}), 400
    except Exception as exc:
        logging.error(f"Общая ошибка: {exc}")
        return jsonify({"error": "Внутренняя ошибка сервера."}), 500


if __name__ == "__main__":  # Закоментировать перед развёртыванием на сайте.
    app.run(debug=True, host="0.0.0.0", port=5000)
