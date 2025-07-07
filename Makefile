.PHONY: build run test up down debug build-test

IMAGE_NAME=odinbot:latest
GUILD_ID?=TESTING_GUILD_ID
CHANNEL_ID?=TESTING_NOISE_CHANNEL_ID

build:
	docker build --target prod -t odinbot:latest .

run: build
	docker run --rm \
	  -e DISCORD_TOKEN=$$DISCORD_TOKEN \
	  -e ODIN_API_KEY=$$ODIN_API_KEY \
	  -e OPENAI_API_KEY=$$OPENAI_API_KEY \
	  -e GUILD_ID=$(GUILD_ID) \
	  -e CHANNEL_ID=$(CHANNEL_ID) \
	  $(IMAGE_NAME)

build-test: build
	docker build --target test -t odinbot:latest.tests .

test: build-test
	docker run --rm \
	  -e DISCORD_TOKEN=$$DISCORD_TOKEN \
	  -e ODIN_API_KEY=$$ODIN_API_KEY \
	  -e OPENAI_API_KEY=$$OPENAI_API_KEY \
	  -e GUILD_ID=$(GUILD_ID) \
	  -e CHANNEL_ID=$(CHANNEL_ID) \
	  -v $(PWD)/tests:/app/tests \
	  odinbot:latest.tests \
	  pytest tests/

up: build
	docker-compose up -d

down:
	docker-compose down

debug: build
	docker run --rm -it \
	  -e DISCORD_TOKEN=$$DISCORD_TOKEN \
	  -e ODIN_API_KEY=$$ODIN_API_KEY \
	  -e OPENAI_API_KEY=$$OPENAI_API_KEY \
	  -e GUILD_ID=$(GUILD_ID) \
	  -e CHANNEL_ID=$(CHANNEL_ID) \
	  -v $(PWD)/tests:/app/tests \
	  $(IMAGE_NAME) \
	  /bin/sh 