"""Test comment API"""
import requests

# Login
print("Testing comment API...")
login_resp = requests.post('http://localhost:8001/api/v1/auth/login', json={'username': 'super_admin', 'password': 'super123'})
print(f'Login status: {login_resp.status_code}')

if login_resp.status_code == 200:
    token = login_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Create comment
    comment_data = {'content': 'Test comment works!', 'is_private': False}
    resp = requests.post('http://localhost:8001/api/v1/documents/11/comments', headers=headers, json=comment_data)
    print(f'Comment status: {resp.status_code}')
    print(f'Response: {resp.text[:800] if resp.text else "Empty"}')
else:
    print(f'Login failed: {login_resp.text}')
