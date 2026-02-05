import json
p='data/mock_data_json/tasks/tasks.json'
with open(p,'r',encoding='utf-8') as f:
    arr=json.load(f)
print([x.get('task_id') for x in arr[-10:]])
