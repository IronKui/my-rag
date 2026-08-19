# backend/test_user.py
from core.user_repository import create_user, get_user_by_username


def test_create_user():
    # 1. 测试插入
    username = "test_user"
    password = "mypassword"
    password_hash = "hash_password(password)"

    uid = create_user(username, password_hash)
    print(f"✅ 用户ID: {uid}")

    # 2. 测试查询
    user = get_user_by_username(username)
    print(f"✅ 查回: {user}")

    # 3. 测试重复插入（应该报错）
    try:
        create_user(username, password_hash)
        print("❌ 不应该执行到这里")
    except ValueError as e:
        print(f"✅ 重复插入被正确拦截: {e}")


if __name__ == "__main__":
    test_create_user()