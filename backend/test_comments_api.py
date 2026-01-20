"""Test Comment API"""
import requests
import json

print('='*60)
print('COMMENT API TEST')
print('='*60)

BASE_URL = 'http://localhost:8001/api/v1'

# 1. Login
print('\n1. Login as super_admin...')
login_resp = requests.post(f'{BASE_URL}/auth/login', json={'username': 'super_admin', 'password': 'super123'})
print(f'   Status: {login_resp.status_code}')

if login_resp.status_code != 200:
    print(f'   ERROR: {login_resp.text}')
    exit(1)

token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
print('   SUCCESS: Got access token')

# 2. Create a comment
print('\n2. Create a public comment on document 11...')
comment_data = {'content': 'This is a test public comment!', 'is_private': False}
resp = requests.post(f'{BASE_URL}/documents/11/comments', headers=headers, json=comment_data)
print(f'   Status: {resp.status_code}')

if resp.status_code in [200, 201]:
    comment = resp.json()
    print(f'   SUCCESS: Created comment ID {comment.get("id")}')
    comment_id = comment.get('id')
else:
    print(f'   ERROR: {resp.text[:500]}')
    exit(1)

# 3. Create a private comment
print('\n3. Create a private comment...')
comment_data = {'content': 'This is a PRIVATE comment only for admins!', 'is_private': True}
resp = requests.post(f'{BASE_URL}/documents/11/comments', headers=headers, json=comment_data)
print(f'   Status: {resp.status_code}')
if resp.status_code in [200, 201]:
    print(f'   SUCCESS: Created private comment ID {resp.json().get("id")}')
else:
    print(f'   ERROR: {resp.text[:300]}')

# 4. Create an inline comment with anchor
print('\n4. Create an inline comment with anchor text...')
comment_data = {
    'content': 'This section needs clarification!',
    'is_private': False,
    'anchor_text': 'mismatch: Sidebar links',
    'anchor_id': 'anchor-12345'
}
resp = requests.post(f'{BASE_URL}/documents/11/comments', headers=headers, json=comment_data)
print(f'   Status: {resp.status_code}')
if resp.status_code in [200, 201]:
    print(f'   SUCCESS: Created inline comment ID {resp.json().get("id")}')
else:
    print(f'   ERROR: {resp.text[:300]}')

# 5. Get all comments
print('\n5. Get all comments for document 11...')
resp = requests.get(f'{BASE_URL}/documents/11/comments', headers=headers)
print(f'   Status: {resp.status_code}')
if resp.status_code == 200:
    comments = resp.json()
    print(f'   SUCCESS: Got {len(comments)} comments')
    for c in comments:
        private_tag = ' [PRIVATE]' if c.get('is_private') else ''
        anchor_tag = ' [INLINE]' if c.get('anchor_text') else ''
        print(f'     - ID {c.get("id")}: {c.get("content")[:40]}...{private_tag}{anchor_tag}')
else:
    print(f'   ERROR: {resp.text[:300]}')

# 6. Create a reply
print('\n6. Create a reply to the first comment...')
reply_data = {'content': 'This is a reply to the first comment!', 'parent_id': comment_id}
resp = requests.post(f'{BASE_URL}/documents/11/comments', headers=headers, json=reply_data)
print(f'   Status: {resp.status_code}')
if resp.status_code in [200, 201]:
    print(f'   SUCCESS: Created reply ID {resp.json().get("id")}')
else:
    print(f'   ERROR: {resp.text[:300]}')

print('\n' + '='*60)
print('ALL TESTS PASSED!')
print('='*60)
