from shared_libs.utils.kafka_producer import KafkaEventProducer

# Initialize Kafka producer
producer = KafkaEventProducer()

# Test data with high interaction counts to trigger embedding updates
test_event = {
    "articles": [
        {"id": "67d7527ca11234fb4ee6a32f", "interaction": {"likes": 3500, "shares": 130, "clicks": 60}},
        {"id": "67d75298a11234fb4ee6a330", "interaction": {"likes": 3140, "shares": 225, "clicks": 50}},
        {"id": "67d752a4a11234fb4ee6a331", "interaction": {"likes": 575, "shares": 735, "clicks": 70}},
        {"id": "67d752b9a11234fb4ee6a332", "interaction": {"likes": 2360, "shares": 540, "clicks": 75}},
        {"id": "67d752c9a11234fb4ee6a333", "interaction": {"likes": 5245, "shares": 228, "clicks": 135}},
        {"id": "67d752e5a11234fb4ee6a334", "interaction": {"likes": 2170, "shares": 450, "clicks": 90}},
        {"id": "67d752fea11234fb4ee6a335", "interaction": {"likes": 880, "shares": 260, "clicks": 200}},
        {"id": "67d750a2a11234fb4ee6a31d", "interaction": {"likes": 1190, "shares": 170, "clicks": 210}},
        {"id": "67d750c1a11234fb4ee6a31e", "interaction": {"likes": 1100, "shares": 180, "clicks": 220}},
    ]
}

# Send test event to Kafka
producer.send("metadata_update", test_event)
print(f"Produced: {test_event}")