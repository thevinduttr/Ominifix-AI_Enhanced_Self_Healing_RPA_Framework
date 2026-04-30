import pika
import json
import os


def publish_failure_event(bot_id):
    rabbit_host = os.environ.get("RABBIT_HOST", "rabbitmq")
    rabbit_user = os.environ.get("RABBITMQ_DEFAULT_USER", "guest")
    rabbit_password = os.environ.get("RABBITMQ_DEFAULT_PASS", "guest")
    credentials = pika.PlainCredentials(rabbit_user, rabbit_password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(rabbit_host, credentials=credentials)
    )
    channel = connection.channel()
    channel.queue_declare(queue="bot.failure")

    event = json.dumps({"botId": bot_id})
    channel.basic_publish(exchange="", routing_key="bot.failure", body=event)

    print("Sent failure event:", bot_id)
    connection.close()
