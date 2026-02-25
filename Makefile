.PHONY: run build up down logs

IMAGE_NAME := matveeva-ai
CONTAINER_NAME := matveeva-ai
# Путь к service_account.json на хосте берётся из .env (GOOGLE_APPLICATION_CREDENTIALS)
HOST_CREDENTIALS := $(shell sed -n 's/^GOOGLE_APPLICATION_CREDENTIALS=//p' .env)

run:
	uv run python -m bot.main

build:
	docker build -t $(IMAGE_NAME) .

up:
	@test -n "$(HOST_CREDENTIALS)" || (echo "Ошибка: в .env должен быть задан GOOGLE_APPLICATION_CREDENTIALS (путь к service_account.json на этом компьютере)"; exit 1)
	@test -f "$(HOST_CREDENTIALS)" || (echo "Ошибка: файл не найден: $(HOST_CREDENTIALS)"; exit 1)
	docker run -d --name $(CONTAINER_NAME) \
		--env-file .env \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json \
		-v "$(HOST_CREDENTIALS):/app/service_account.json:ro" \
		$(IMAGE_NAME)

down:
	docker stop $(CONTAINER_NAME) 2>/dev/null || true
	docker rm $(CONTAINER_NAME) 2>/dev/null || true

logs:
	docker logs $(CONTAINER_NAME)
