import uuid

### Helps with graph UUIDs

def init_ids(names):
    results = {}
    for name in names:
        results[name] = name + '--' + str(uuid.uuid4())
    return results
