from flask import Flask, request, jsonify
import redis
import json
import os

app = Flask(__name__)
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-GitHub-Event') != 'pull_request':
        return jsonify({'status': 'ignored', 'reason': 'not a PR event'}), 200
    
    payload = request.json
    
    # Only process merged PRs
    if not (payload.get('action') == 'closed' and payload.get('pull_request', {}).get('merged')):
        return jsonify({'status': 'ignored', 'reason': 'PR not merged'}), 200
    
    # Extract relevant information
    pr_info = {
        'pr_number': payload['pull_request']['number'],
        'merged_at': payload['pull_request']['merged_at'],
        'changed_files': []
    }
    
    # Get the list of changed files from GitHub API
    # Note: You'll need to implement get_changed_files() using GitHub's API
    changed_files = get_changed_files(
        payload['pull_request']['number'],
        payload['repository']['full_name']
    )
    
    pr_info['changed_files'] = changed_files
    
    # Add to Redis queue
    redis_client.rpush('pr_queue', json.dumps(pr_info))
    
    return jsonify({'status': 'queued'}), 200

def get_changed_files(pr_number, repo_name):
    # Implement GitHub API call to get changed files
    # This is a placeholder - you'll need to add GitHub API authentication
    return []

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)