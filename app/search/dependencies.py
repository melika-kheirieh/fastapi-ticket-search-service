from typing import TYPE_CHECKING

from app.search.client import create_elasticsearch_client

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch


def get_elasticsearch_client() -> "Elasticsearch":
    return create_elasticsearch_client()