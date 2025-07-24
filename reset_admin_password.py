from app import app, db, User
from werkzeug.security import generate_password_hash

app.app_context().push()

# Reset password for admin user
admin_email = 'sdclark117@gmail.com'  # Change this to the admin email you want to use
new_password = 'admin123'  # Change this to your desired password

user = User.query.filter_by(email=admin_email).first()
if user:
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    print(f"✅ Password reset for {admin_email}")
    print(f"New password: {new_password}")
else:
    print(f"❌ User {admin_email} not found")

print("\nYou can now log in with:")
print(f"Email: {admin_email}")
print(f"Password: {new_password}") 