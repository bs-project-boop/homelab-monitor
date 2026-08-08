from app.services.versions import check_image


def test_unparseable_registry_is_unknown(monkeypatch):
    monkeypatch.setattr('app.services.versions._lookup', lambda repository: ['latest', '1.2.0', '1.3.0'])
    result = check_image('example.invalid/app:1.2.0')
    assert result.latest == '1.3.0'
    assert result.state == 'update_available'


def test_latest_tag_uses_stable_registry_tag(monkeypatch):
    monkeypatch.setattr('app.services.versions._lookup', lambda repository: ['latest', '1.2.0', '1.4.0-rc.1', '1.3.0'])
    result = check_image('acme/app:latest')
    assert result.latest == '1.3.0'
    assert result.source == 'docker-hub'
