import redis
import json
import time
import os
from collections import defaultdict

class PRProcessor:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        self.file_changes = defaultdict(lambda: {'status': None, 'last_pr': None})
    
    def process_queue(self):
        while True:
            # Get PR info from queue with timeout
            try:
                result = self.redis_client.blpop('pr_queue', timeout=1)
                if result:
                    _, pr_data = result
                    pr_info = json.loads(pr_data)
                    self.process_pr(pr_info)
                time.sleep(1)  # Prevent tight loop
            except Exception as e:
                print(f"Error processing queue: {e}")
                time.sleep(1)  # Wait before retrying
    
    def process_pr(self, pr_info):
        # Update file changes with latest PR information
        for file_change in pr_info['changed_files']:
            self.file_changes[file_change['filename']] = {
                'status': file_change['status'],  # 'added', 'modified', or 'removed'
                'last_pr': pr_info['pr_number']
            }
        
        # Process consolidated changes
        self.process_consolidated_changes()
    
    def process_consolidated_changes(self):
        # Group changes by type
        changes = {
            'added': [],
            'modified': [],
            'removed': []
        }
        
        for filename, info in self.file_changes.items():
            if info['status'] in changes:
                changes[info['status']].append(filename)
        
        # Implement your processing logic here
        # For example:
        print(f"Processing consolidated changes:")
        print(f"Added files: {len(changes['added'])}")
        print(f"Modified files: {len(changes['modified'])}")
        print(f"Removed files: {len(changes['removed'])}")
        
        # Clear processed changes
        self.file_changes.clear()

if __name__ == '__main__':
    processor = PRProcessor()
    processor.process_queue()