from fastapi.testclient import TestClient
from app.main import app, parse_repo, analyze_files

def test_health():
    response = TestClient(app).get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_parse_repo():
    assert parse_repo('https://github.com/example/repo') == ('example', 'repo')
    assert parse_repo('example/repo') == ('example', 'repo')

def test_reject_bad_host():
    response = TestClient(app).post('/api/analyze', json={'repository': 'https://evil.example/a/b'})
    assert response.status_code == 422

def test_scan():
    data = analyze_files({'app.py': 'print("hello")\n# TODO cleanup\n'})
    assert data['files_analyzed'] == 1
    assert data['severity_counts']['low'] == 2
