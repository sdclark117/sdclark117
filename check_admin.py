from app import app, db, User

app.app_context().push()

print("=== Admin Users ===")
admin_users = User.query.filter_by(is_admin=True).all()
for user in admin_users:
    print(f"Email: {user.email}")
    print(f"Admin: {user.is_admin}")
    print(f"Plan: {user.current_plan}")
    print("---")

print("\n=== All Users ===")
all_users = User.query.all()
for user in all_users:
    print(f"Email: {user.email}, Admin: {user.is_admin}, Plan: {user.current_plan}") 