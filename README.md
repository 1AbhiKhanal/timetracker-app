# ⏱️ TimeTracker - Employee Time Management System

A comprehensive Flask-based web application for tracking employee work hours, breaks, and managing team timesheets with a 48-hour weekly cap.

## 🌟 Features

### Employee Features
- **⏰ Time Tracking**

  - Clock In/Out functionality
  - Lunch break tracking (Start/End)
  - Dinner break tracking (Start/End)
  - Automatic work hour calculation (excluding breaks)

- **👤 User Profile Settings**
  - Change username
  - Change password (with current password verification)
  - Update email address
  - Upload profile picture (PNG, JPG, JPEG, GIF)

- **📊 Dashboard**
  - Today's work and break time summary
  - Clock in/out times display
  - Break times breakdown
  - Reset daily entry option

- **📈 Weekly Summary**
  - View complete weekly work hours
  - Total break time
  - Remaining hours to reach 48-hour target
  - Daily breakdown with all time entries

### Admin Features
- **👥 Team Management**
  - View all employees' weekly summaries
  - Status flags showing hours completion
  - Quick actions: Reset week, Delete user

- **📝 Manual Entry Editing**
  - Edit any employee's time entry
  - Modify clock in/out times
  - Adjust break times
  - Support for past dates

- **📅 Roster Management**
  - Set shift timings for each day
  - Define start and end times per employee
  - Manage working days and schedules

- **⚠️ Compliance Tracking**
  - Visual indicators for 48-hour target status
  - Employee weekly hour totals
  - Break time tracking

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (SQLAlchemy ORM)
- **Frontend**: Bootstrap 5, HTML5, CSS3
- **Icons**: Font Awesome 6.4
- **Authentication**: Flask-Login

## 📦 Installation

### Prerequisites
- Python 3.7+
- pip

### Setup

1. **Install dependencies**
   ```bash
   pip install flask flask-sqlalchemy flask-login werkzeug
   ```

2. **Navigate to project**
   ```bash
   cd time-tracker
   ```

3. **Initialize database**
   ```bash
   python app.py
   # Visit: http://localhost:5000/init
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the app**
   ```
   http://localhost:5000
   ```

## 👥 Default Users

Demo credentials (set up automatically):
- **Abhi** / abhi123
- **Rutul** / rutul123
- **Aman** / aman123
- **Palpasa** / palpasa123
- **Geetika** / geetika123
- **Udita** / udita123

**Admin Account**: First user (Abhi) has admin privileges

## 📚 User Guide

### For Employees

1. **Login**: Select your name and enter password
2. **Clock In**: Click "Clock In" button to start work
3. **Break Time**: Use "Lunch Start/End" and "Dinner Start/End" buttons
4. **Clock Out**: Click "Clock Out" at end of day
5. **View Dashboard**: See today's summary on main dashboard
6. **Weekly Summary**: Click "This Week" to see cumulative hours
7. **Settings**:
   - Change password
   - Update username
   - Add profile picture
   - Update email

### For Admin

1. **Admin Dashboard**: Click "Admin" in navigation
2. **Team Summary**: View all employees' weekly hours
3. **Quick Actions**:
   - 🔄 Reset Week: Clear weekly entries for an employee
   - 🗑️ Delete: Remove user (except admin)
4. **Edit Entry Tab**:
   - Manually adjust any employee's time entry
   - Specify employee name and date
   - Update individual clock in/out times
5. **Roster Tab**:
   - Set shift schedules
   - Assign working hours per day
   - Plan employee rosters

## 📁 Project Structure

```
time-tracker/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── templates/            # HTML templates
│   ├── base.html         # Base layout with navbar
│   ├── login.html        # Login page
│   ├── dashboard.html    # Daily dashboard
│   ├── week.html         # Weekly summary
│   ├── admin.html        # Admin panel
│   └── settings.html     # User settings
└── static/
    ├── uploads/          # User profile pictures
    └── default-avatar.svg # Default profile picture
```

## 🗄️ Database Models

### User
- id, name, password, email, profile_pic, created_at, is_admin

### TimeEntry
- id, user_id, day, clock_in, lunch_start, lunch_end, dinner_start, dinner_end, clock_out

### Roster
- id, user_id, day_of_week, start_time, end_time

## 🎯 Key Calculations

- **Work Minutes** = Clock Out Time - Clock In Time - (Lunch Break + Dinner Break)
- **Weekly Target** = 48 hours (288 minutes)
- **Break Time** = (Lunch End - Lunch Start) + (Dinner End - Dinner Start)

## 🔐 Security Features

- Password hashing using werkzeug
- Login required for all except login page
- Admin-only access to admin panel
- File upload validation (image files only, 16MB limit)
- Secure filename handling

## ✨ UI/UX Highlights

- **Responsive Design**: Works on desktop, tablet, mobile
- **Beautiful Gradients**: Purple/blue gradient theme
- **Icons**: Font Awesome icons throughout
- **Flash Messages**: Success/error notifications
- **Animated Cards**: Smooth hover effects
- **Color Coding**: Green (success), Red (danger), Yellow (warning)

## 🚀 Future Enhancements

- [ ] Export reports to CSV/PDF
- [ ] Email notifications for compliance
- [ ] Multi-month historical reports
- [ ] Team analytics and charts
- [ ] Overtime tracking
- [ ] Leave management
- [ ] Mobile app

## 🤝 Support

For issues or feature requests, please update the code as needed.

## 📄 License

This project is open source and available for use.

---

**Made with ❤️ for efficient time management**
