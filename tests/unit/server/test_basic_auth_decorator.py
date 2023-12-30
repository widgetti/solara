"""Unit test for basic_auth_decorator module"""
import os
import pytest
from unittest.mock import patch
from solara.server.basic_auth_decorator import import_module_from_env_var, BadAuthModulePath, MethodNotFound, auth_required, NOT_AUTHRIZED_MESSAGE
from starlette.requests import Request
from starlette.responses import Response
from starlette import status
from starlette.exceptions import HTTPException
from unittest.mock import Mock

def test_import_module_env_var_not_set():
    """test function without env var"""
    assert import_module_from_env_var('NON_EXISTENT_ENV_VAR') is None

def test_import_module_file_not_exist(caplog, monkeypatch):
    """Test with module file that doesn't exist"""
    monkeypatch.setenv('TEST_ENV_VAR', 'nonexistent.py')
    with pytest.raises(BadAuthModulePath):
        import_module_from_env_var('TEST_ENV_VAR')
    assert "File nonexistent.py does not exist" in caplog.text

def test_import_module_no_authenticate_method(tmp_path, monkeypatch):
    """Test import module with no authenticate method"""
    module_file = tmp_path / "temp_module.py"
    module_file.write_text("")
    monkeypatch.setenv('TEST_ENV_VAR', str(module_file))
    with pytest.raises(MethodNotFound):
        import_module_from_env_var('TEST_ENV_VAR')

def test_import_module_success(tmp_path, monkeypatch):
    """Test import module successfully."""
    module_file = tmp_path / "temp_module.py"
    module_file.write_text("def authenticate(request): ...")
    monkeypatch.setenv('TEST_ENV_VAR', str(module_file))
    module = import_module_from_env_var('TEST_ENV_VAR')
    assert module is not None
    assert hasattr(module, 'authenticate')


@pytest.mark.asyncio
async def test_auth_decorator_no_auth_required(monkeypatch):
    monkeypatch.setenv('BASIC_AUTH_REQUIRED', 'False')

    @auth_required
    async def test_func(request):
        return Response()

    request = Mock()
    request.headers = {'Authorization': 'dummy token'}
    response = await test_func(request)
    assert isinstance(response, Response)


@pytest.mark.asyncio
async def test_auth_decorator_no_auth_header():
    with patch.dict(os.environ, {'BASIC_AUTH_REQUIRED': 'True'}, clear=True):
        @auth_required
        async def test_func(request):
            return Response()

        request = Mock()
        request.headers = {}
        with pytest.raises(HTTPException) as excinfo:
            await test_func(request)
        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == NOT_AUTHRIZED_MESSAGE

