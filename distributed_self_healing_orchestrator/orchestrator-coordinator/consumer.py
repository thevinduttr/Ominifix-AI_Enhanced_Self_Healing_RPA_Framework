import pika
import json
import os
from coordinator import start_healing


def callback(ch, method, properties, body):
    data = json.loads(body.decode())
    bot_id = data["botId"]
    print("Failure received:", bot_id)
    start_healing(bot_id)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer():
    rabbit_host = os.environ.get("RABBIT_HOST", "rabbitmq")
    rabbit_user = os.environ.get("RABBITMQ_DEFAULT_USER", "guest")
    rabbit_password = os.environ.get("RABBITMQ_DEFAULT_PASS", "guest")
    credentials = pika.PlainCredentials(rabbit_user, rabbit_password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(rabbit_host, credentials=credentials)
    )
    channel = connection.channel()
    channel.queue_declare(queue="bot.failure")

    channel.basic_consume(queue="bot.failure", on_message_callback=callback)
    print("Coordinator listening...")
    channel.start_consuming()


if __name__ == "__main__":
    start_consumer()
