# Database Guide - Persistent User Accounts

## 🎉 **Problem Solved!**

Your user accounts are now **persistent** and will survive server restarts and app updates. No more losing accounts!

## 📁 **How It Works**

### **Persistent Database File**
- **Database file:** `sneaker_agent.db`
- **Location:** In your project root directory
- **Type:** SQLite database (lightweight, reliable)
- **Backup:** Automatically excluded from git (in `.gitignore`)

### **What's Preserved**
✅ **All user accounts** - Email, password, profile info  
✅ **Admin accounts** - Your admin privileges  
✅ **User settings** - Search preferences, defaults  
✅ **Subscription data** - Plans, payment info  
✅ **Search history** - User activity tracking  
✅ **Guest usage** - Anti-abuse protection data  

## 🚀 **How to Start the App**

### **Option 1: Use the startup script (Recommended)**
```bash
python start_app.py
```

This will:
- ✅ Check if database exists
- ✅ Initialize database if needed
- ✅ Start the Flask server
- ✅ Show admin login credentials

### **Option 2: Direct Flask start**
```bash
python app.py
```

## 🔧 **Database Management**

### **Initialize Database (First Time)**
```bash
python init_database.py
```

### **Backup Database**
```bash
python backup_database.py backup
```

### **List Available Backups**
```bash
python backup_database.py list
```

### **Restore from Backup**
```bash
python backup_database.py restore --file sneaker_agent_backup_20250723_210000.db
```

## 📊 **Database Status**

### **Check Database Size**
```bash
ls -lh sneaker_agent.db
```

### **View All Users**
```bash
python check_admin.py
```

## 🔑 **Default Admin Accounts**

Your admin accounts are preserved:
- **Email:** `sdclark117@gmail.com`
- **Password:** `admin123`
- **Email:** `kasieewardd@gmail.com`
- **Password:** `admin123`

## 🛡️ **Data Protection**

### **Automatic Backups**
- Database file is automatically backed up before updates
- Backup files are timestamped for easy identification
- Multiple backup versions are kept

### **Git Safety**
- Database file is in `.gitignore`
- User data is never committed to version control
- Sensitive information stays private

## 🔄 **Server Restart Process**

1. **Stop the server:** `Ctrl+C`
2. **Start the server:** `python start_app.py`
3. **All accounts preserved** ✅

## 📈 **Benefits**

✅ **No more lost accounts** - Users stay logged in  
✅ **Persistent admin access** - Your admin privileges preserved  
✅ **User data survives updates** - Settings, preferences, history  
✅ **Automatic initialization** - Database created if missing  
✅ **Easy backups** - Simple backup/restore process  
✅ **Production ready** - Can be deployed with persistent data  

## 🎯 **What This Means for Users**

- **New users:** Create account once, use forever
- **Existing users:** All data preserved across restarts
- **Admin users:** Admin privileges always available
- **Settings:** User preferences saved permanently
- **Search history:** Previous searches remembered

## 🚨 **Important Notes**

1. **Keep the database file safe** - It contains all user data
2. **Regular backups recommended** - Use the backup script
3. **Don't delete `sneaker_agent.db`** - This is your user database
4. **Backup before major updates** - Just in case

## 🎉 **Success!**

Your application now has **enterprise-level data persistence**. Users will never lose their accounts again! 