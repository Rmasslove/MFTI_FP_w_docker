const form = document.getElementById("text-form");
const textInput = document.getElementById("text_input");
const errorMessage = document.getElementById("error-message");
const messagesDiv = document.getElementById("messages");

textInput.addEventListener("input", () => {
    const pattern = /^[А-Яа-яЁё\s]*$/; // Разрешаем только русские буквы и пробелы
    if (!pattern.test(textInput.value)) {
        textInput.value = textInput.value.replace(/[^А-Яа-яЁё\s]/g, ""); // Удаляем неподобающие символы
        errorMessage.textContent = "Допускаются только русские буквы."; // Показываем ошибку
    } else {
        errorMessage.textContent = ""; // Очищаем сообщение об ошибке
    }
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    // Очистка предыдущих сообщений
    messagesDiv.innerHTML = "";
    errorMessage.textContent = "";

    const userInput = textInput.value.trim();

    // Проверка: пустое поле
    if (!userInput) {
        errorMessage.textContent = "Текст не предоставлен.";
        return;
    }

    // Проверка: длина текста
    if (userInput.length > 50) {
        errorMessage.textContent = "Текст не должен превышать 50 символов.";
        return;
    }

    // Отображение введённого текста в отдельном блоке
    const inputTextDiv = document.createElement("div");
    inputTextDiv.className = "input-text";

    const inputLabelSpan = document.createElement("span");
    inputLabelSpan.className = "input-label";
    inputLabelSpan.textContent = "Текст для перевода: ";

    const inputValueSpan = document.createElement("span");
    inputValueSpan.className = "input-value";
    inputValueSpan.textContent = userInput;

    inputTextDiv.appendChild(inputLabelSpan);
    inputTextDiv.appendChild(inputValueSpan);
    messagesDiv.appendChild(inputTextDiv);

    // Очистка поля ввода
    textInput.value = "";

    let stage = "start"; // Начальный этап
    let previousMessageDiv = null; // Для отображения "Готово"

    while (stage) {
        // Добавление текущего сообщения
        const messageDiv = document.createElement("div");
        messageDiv.className = "stage-message";
        messageDiv.textContent = getStageMessage(stage);
        messagesDiv.appendChild(messageDiv);

        // Если есть предыдущее сообщение, добавить "Готово"
        if (previousMessageDiv && stage !== "start" && stage !== "end") {
            const readySpan = document.createElement("span");
            readySpan.textContent = " Готово.";
            readySpan.className = "status-ready";
            previousMessageDiv.appendChild(readySpan);
        }

        // Сохраняем текущий div как предыдущий
        if (stage !== "start") {
            previousMessageDiv = messageDiv;
        }

        // Выполнение текущего этапа
        const response = await fetch("/process_stage", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ stage, text_input: userInput }),
        });

        if (!response.ok) {
            const data = await response.json();
            errorMessage.textContent = data.error;
            break;
        }

        const data = await response.json();
        stage = data.next_stage; // Следующий этап

        // Если этап завершен и есть результат
        if (stage === "end" && data.result) {
            const resultMessageDiv = document.createElement("div");
            resultMessageDiv.className = "result-message";

            const resultLabelSpan = document.createElement("span");
            resultLabelSpan.className = "result-label";
            resultLabelSpan.textContent = "Перевод текста: ";

            const resultValueSpan = document.createElement("span");
            resultValueSpan.className = "result-value";
            resultValueSpan.textContent = data.result;

            resultMessageDiv.appendChild(resultLabelSpan);
            resultMessageDiv.appendChild(resultValueSpan);
            messagesDiv.appendChild(resultMessageDiv);
            break;
        }
    }
});

// Функция для получения сообщений по этапам
function getStageMessage(stage) {
    switch (stage) {
        case "start":
            return "";
        case "tts":
            return "Генерация аудио из текста моделью (TTS) . . .";
        case "whisper":
            return "Преобразование аудио в текст моделью (Whisper) . . .";
        case "opus_mt":
            return "Перевод текста на русский язык моделью (Opus-MT) . . .";
        default:
            return "";
    }
}