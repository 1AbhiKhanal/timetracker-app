# ⚡ QUICK START GUIDE - NEW FEATURES

## 🚀 START THE APP
```bash
cd time-tracker
python app.py
```
Visit: `http://localhost:5000/init` (First time only)

---

## 🔐 FEATURE 1: FORGOT PASSWORD

**Access:** Login page → "🔐 Forgot Password?" link

**How it works:**
1. Enter email or username
2. Email sent with reset link (shows in console)
3. Click link to reset password
4. Login with new password

**Routes:**
- `/forgot-password` - Request reset
- `/reset-password/<token>` - Confirm reset

---

## 📥 FEATURE 2: CSV EXPORT

**Employee Export:**
- Go to: Admin → Employee Management
- Click: "Export to CSV"
- File: `employees_YYYY-MM-DD.csv`

**Timesheet Export:**
- Go to: Admin → Reports
- Click: "Export Timesheets" or "Export Employees"
- File: `timesheets_YYYY-MM-DD.csv` or `employees_YYYY-MM-DD.csv`

**Route:** `/export-csv?type=<employees|timesheets>&date=<optional>`

---

## 📧 FEATURE 3: EMAIL NOTIFICATIONS

**Current Integration:**
- Logs to console (for demo)
- Ready for production email services

**Demo Output:**
```
📧 EMAIL SENT
   To: user@email.com
   Subject: Password Reset Request
   Body: [Email content]
```

**When Emails Are Sent:**
- ✅ Password reset request
- ✅ Password reset confirmation

**Upgrade for Production:**
Add your SendGrid/Gmail/AWS SES keys to `send_email()` function in `app.py`

---

## 🎭 DEMO USERS

After running `/init`, use these accounts:

| Username | Password | Role |
|----------|----------|------|
| Abhi | abhi123 | Admin |
| Rutul | rutul123 | Employee |
| Aman | aman123 | Employee |
| Palpasa | palpasa123 | Employee |
| Geetika | geetika123 | Employee |
| Udita | udita123 | Employee |

---

## 📋 NEW FILES ADDED

**Templates:**
- `forgot_password.html` - Request password reset
- `reset_password.html` - Create new password

**Database:**
- `PasswordReset` table for secure tokens

**Routes:**
- `@app.route("/forgot-password")` - Password reset request
- `@app.route("/reset-password/<token>")` - Reset with token
- `@app.route("/export-csv")` - CSV export endpoint

---

## ✨ QUICK FEATURES CHECK

```
Feature              | Status   | Access
---------------------|----------|------------------
Forgot Password      | ✅ Done  | Login page link
CSV Export           | ✅ Done  | Reports/Employees
Email Notifications  | ✅ Done  | Console (demo)
---
TOTAL: 10/10 COMPLETE
```

---

## 🔧 CUSTOMIZATION

### Change Password Reset Expiry:
Edit `app.py`, line ~740:
```python
if (datetime.now() - reset.created_at).seconds > 86400:  # Change 86400 (24 hours)
```

### Change CSV File Names:
Edit `app.py`, line ~795:
```python
download_name=f'employees_{date.today().isoformat()}.csv'
```

### Setup Real Email:
Edit `send_email()` function in `app.py`, line ~150

---

## 📞 QUICK HELP

**Q: Email not sending?**
A: Currently logging to console. Add your email provider credentials to `send_email()` function.

**Q: Can't reset password?**
A: Check console for reset link. Make sure token hasn't expired (24 hours).

**Q: CSV file corrupt?**
A: Try opening in Excel or Google Sheets. Verify UTF-8 encoding.

**Q: 403 Access Denied on export?**
A: Only admins can export. Login as admin (Abhi).

---

## 🎯 PRODUCTION CHECKLIST

- [ ] Configure real email service (SendGrid/Gmail/AWS)
- [ ] Update `send_email()` function with API keys
- [ ] Set secure database
- [ ] Enable HTTPS
- [ ] Configure backup system
- [ ] Test all features
- [ ] Monitor activity logs
- [ ] Set up error alerts

---

**Everything is ready to use! 🚀**

App Status: **RUNNING** on `http://localhost:5000`
