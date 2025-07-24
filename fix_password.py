from app import app, db, User
from werkzeug.security import generate_password_hash, check_password_hash

app.app_context().push()

# Reset password for admin user
admin_email = 'sdclark117@gmail.com'
new_password = 'admin123'

user = User.query.filter_by(email=admin_email).first()
if user:
    # Generate new password hash
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    # Verify the password works
    test_result = check_password_hash(user.password_hash, new_password)
    
    print(f"✅ Password reset for {admin_email}")
    print(f"New password: {new_password}")
    print(f"Password verification test: {'✅ PASSED' if test_result else '❌ FAILED'}")
    
    if test_result:
        print("\n🎉 Password is working correctly!")
        print("You can now log in with:")
        print(f"Email: {admin_email}")
        print(f"Password: {new_password}")
    else:
        print("\n❌ Password verification failed!")
else:
    print(f"❌ User {admin_email} not found") 