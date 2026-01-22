"""Test script to verify multi-tenancy isolation

This script tests that:
1. Users can only see documents from their own tenant
2. Super admin can see all documents
3. Cross-tenant document access is blocked
"""
import requests

BASE_URL = "http://localhost:8001/api/v1"


def login(username: str, password: str) -> str:
    """Login and return access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code != 200:
        print(f"  ✗ Login failed for {username}: {response.text}")
        return None
    return response.json()["access_token"]


def get_documents(token: str) -> list:
    """Get documents with auth token"""
    response = requests.get(
        f"{BASE_URL}/documents",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code != 200:
        print(f"  ✗ Get documents failed: {response.text}")
        return []
    return response.json()["items"]


def get_document_by_id(token: str, doc_id: int) -> dict:
    """Try to get a specific document"""
    response = requests.get(
        f"{BASE_URL}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response


def test_tenant_isolation():
    """Test tenant isolation"""
    print("=" * 60)
    print("Multi-Tenancy Isolation Test")
    print("=" * 60)
    
    # Test 1: Login as Acme user and verify only Acme docs visible
    print("\n[Test 1] Acme user can only see Acme documents")
    acme_token = login("acme_admin", "acme123")
    if not acme_token:
        return False
    
    acme_docs = get_documents(acme_token)
    print(f"  Acme user sees {len(acme_docs)} documents:")
    for doc in acme_docs:
        print(f"    - {doc['title']} ({doc['document_number']})")
    
    # Verify all docs are Acme docs
    acme_doc_prefixes = all(d["document_number"].startswith("ACME-") for d in acme_docs)
    if acme_doc_prefixes:
        print("  ✓ All documents belong to Acme tenant")
    else:
        print("  ✗ FAILED: Non-Acme documents visible!")
        return False
    
    # Test 2: Login as Beta user and verify only Beta docs visible
    print("\n[Test 2] Beta user can only see Beta documents")
    beta_token = login("beta_admin", "beta123")
    if not beta_token:
        return False
    
    beta_docs = get_documents(beta_token)
    print(f"  Beta user sees {len(beta_docs)} documents:")
    for doc in beta_docs:
        print(f"    - {doc['title']} ({doc['document_number']})")
    
    # Verify all docs are Beta docs  
    beta_doc_prefixes = all(d["document_number"].startswith("BETA-") for d in beta_docs)
    if beta_doc_prefixes:
        print("  ✓ All documents belong to Beta tenant")
    else:
        print("  ✗ FAILED: Non-Beta documents visible!")
        return False
    
    # Test 3: System admin can see all documents
    print("\n[Test 3] System admin can see all documents")
    system_admin_token = login("super_admin", "super123")  # Username unchanged
    if not system_admin_token:
        return False
    
    system_admin_docs = get_documents(system_admin_token)
    print(f"  System admin sees {len(system_admin_docs)} documents:")
    
    acme_count = sum(1 for d in system_admin_docs if d["document_number"].startswith("ACME-"))
    beta_count = sum(1 for d in system_admin_docs if d["document_number"].startswith("BETA-"))
    other_count = len(system_admin_docs) - acme_count - beta_count
    
    print(f"    - Acme documents: {acme_count}")
    print(f"    - Beta documents: {beta_count}")
    print(f"    - Other documents: {other_count}")
    
    if acme_count >= 3 and beta_count >= 3:
        print("  ✓ System admin can see documents from all tenants")
    else:
        print("  ✗ FAILED: System admin not seeing all tenant documents!")
        return False
    
    # Test 4: Cross-tenant access blocked
    print("\n[Test 4] Cross-tenant access blocked")
    
    # Get a Beta document ID
    if beta_docs:
        beta_doc_id = beta_docs[0]["id"]
        print(f"  Attempting to access Beta doc (ID: {beta_doc_id}) as Acme user...")
        
        response = get_document_by_id(acme_token, beta_doc_id)
        if response.status_code == 404:
            print("  ✓ Cross-tenant access blocked (404 Not Found)")
        else:
            print(f"  ✗ FAILED: Acme user could access Beta document! Status: {response.status_code}")
            return False
    
    # Test 5: Tenant users can create documents in their tenant
    print("\n[Test 5] Tenant users can create documents")
    new_doc = {
        "title": "Test Document from Acme",
        "description": "Created during isolation test",
        "category": "Testing"
    }
    
    response = requests.post(
        f"{BASE_URL}/documents",
        json=new_doc,
        headers={"Authorization": f"Bearer {acme_token}"}
    )
    
    if response.status_code == 201:
        created_doc = response.json()
        print(f"  ✓ Created document: {created_doc['document_number']}")
        
        # Verify Beta can't see it
        beta_docs_after = get_documents(beta_token)
        beta_can_see_new = any(d["id"] == created_doc["id"] for d in beta_docs_after)
        
        if not beta_can_see_new:
            print("  ✓ Beta user cannot see newly created Acme document")
        else:
            print("  ✗ FAILED: Beta user can see Acme's new document!")
            return False
    else:
        print(f"  ✗ FAILED: Could not create document: {response.text}")
        return False
    
    # All tests passed
    print("\n" + "=" * 60)
    print("✓ All isolation tests PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys
    success = test_tenant_isolation()
    sys.exit(0 if success else 1)
