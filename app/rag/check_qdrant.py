from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

collections = client.get_collections()
print('Collections:', [c.name for c in collections.collections])

print('\nCollection info:')
for c in collections.collections:
    count = client.count(c.name).count
    print(f'{c.name}: {count} points')