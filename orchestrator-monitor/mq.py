import pika
import json
import os


def publish_failure_event(bot_id):
    rabbit_host = os.environ.get('RABBIT_HOST', 'rabbitmq')
    connection = pika.BlockingConnection(pika.ConnectionParameters(rabbit_host))
    channel = connection.channel()
    channel.queue_declare(queue="bot.failure")

    event = json.dumps({"botId": bot_id})
    channel.basic_publish(exchange="", routing_key="bot.failure", body=event)

    print("Sent failure event:", bot_id)
    connection.close()
