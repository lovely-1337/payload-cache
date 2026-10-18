FROM python:3.13-slim

WORKDIR /srv

# Зависимости копируем и ставим отдельно от кода: пока requirements.txt
# не менялся, Docker берёт этот слой из кэша, и пересборка занимает секунды.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Непривилегированный пользователь: если приложение взломают,
# у атакующего не будет root внутри контейнера.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]