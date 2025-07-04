.PHONY: build run test up down

IMAGE_NAME=odinbot:latest
GUILD_ID?=TESTING_GUILD_ID
CHANNEL_ID?=TESTING_NOISE_CHANNEL_ID

build:
	docker build -t $(IMAGE_NAME) .

run: build
	docker run --rm \
	  -e DISCORD_TOKEN=$$DISCORD_TOKEN \
	  -e ODIN_API_KEY=$$ODIN_API_KEY \
	  -e OPENAI_API_KEY=$$OPENAI_API_KEY \
	  -e GUILD_ID=$(GUILD_ID) \
	  -e CHANNEL_ID=$(CHANNEL_ID) \
	  $(IMAGE_NAME)

test: build
	docker run --rm \
	  -e DISCORD_TOKEN=$$DISCORD_TOKEN \
	  -e ODIN_API_KEY=$$ODIN_API_KEY \
	  -e OPENAI_API_KEY=$$OPENAI_API_KEY \
	  -e GUILD_ID=$(GUILD_ID) \
	  -e CHANNEL_ID=$(CHANNEL_ID) \
	  $(IMAGE_NAME) \
	  pytest tests/ 

# 'build' is a prerequisite for 'up', so the image is always built before starting services
up: build
	docker-compose up -d

# Stop docker-compose services
down:
	docker-compose down 