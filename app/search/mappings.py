TICKET_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "id": {"type": "long"},
            "user_id": {"type": "long"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "status": {"type": "keyword"},
            "priority": {"type": "keyword"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        },
    },
}