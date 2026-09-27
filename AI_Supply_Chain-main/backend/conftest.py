import os
import pytest

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


@pytest.fixture(autouse=True)
def legacy_test_api_auth_override(request):
    """
    Ensure legacy test_api.py (which runs unauthenticated queries)
    continues to pass without altering existing legacy test suites.
    """
    if "test_api.py" in str(request.node.fspath):
        from app.main import app
        from app.models.entities import User, UserRole
        from app.services.auth_service import get_current_user

        def mock_admin_user():
            return User(
                id=999,
                username="legacy_admin",
                email="legacy_admin@example.com",
                password_hash="mock_password",
                role=UserRole.ADMIN,
                supplier_id=None,
                is_active=True,
            )

        app.dependency_overrides[get_current_user] = mock_admin_user
        yield
        app.dependency_overrides.pop(get_current_user, None)
    else:
        yield
