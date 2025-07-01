# Simple-Time-Tracker
Welcome to Simple Time Tracker! This is a clean, powerful, and local-first time tracking tool designed to help you effortlessly log, manage, and review the time you spend on various tasks. Whether for work, study, or personal projects, it can be a great assistant in boosting your productivity and optimizing your time allocation.
![2025-07-01_123408](https://github.com/user-attachments/assets/b2ccc0f0-9d24-49b1-a805-69b4b0731570)


2. Quick Start

    Run the Application: Simply execute the time_tracker.py script to launch the app.

    Data File: On the first run, the program will automatically create a file named time_tracker_data.json in the same directory. This is your core data file. Please do not modify it manually unless you know what you are doing. All your data (categories, activity logs, and settings) is stored here.

    Start Tracking:

        Select a category from the Category dropdown menu (e.g., "Work").

        Enter the specific activity name in the What are you working on? input field (e.g., "Writing project report").

        Click the green Start button to begin the timer.

        Once you're done, click the red Stop button. An activity record will be automatically saved to the "Activities Log" below.

3. Feature Details
3.1 Date Navigation

The date control section at the top allows you to easily view activity records for different dates.

    ? Prev / Next ?: Switch to the previous or next day.

    Date Input Field: You can manually enter a date in YYYY-MM-DD format and click the Go button to jump to that specific date.

    Today: Quickly return to today's date view.

3.2 Timer

This is the core interactive area of the application.

    Category: You must select a specific category from this dropdown menu before starting the timer.

    What are you working on?: Fill in a description of your current activity.

    Time Display: Shows the elapsed time or the remaining time for a Pomodoro session in HH:MM:SS format.

    Start/Stop Button: Controls the start and stop of the timer.

3.3 Pomodoro Timer

This is a collapsible module that provides Pomodoro Technique functionality.

    Enable Pomodoro Mode: When checked, the Start button will initiate a Pomodoro cycle.

    Work (min) / Break (min): Customize the duration (in minutes) for a work session and a break session.

    Status: Displays the current state (Idle/Work/Break).

    Workflow:

        After a "Work" session ends, the activity is automatically logged (with a (Pomodoro) tag appended to the name), and a "Break" session begins.

        After the "Break" session ends, the timer stops automatically, waiting for you to start the next work cycle.

        During a break, the button will change to "Skip Break," which you can click to stop the timer immediately.

3.4 Category Management

A collapsible module for managing all your categories.

    Add a New Category:

        Enter the new category name in the input field (e.g., "Fitness").

        Click the 【】 or [] button next to it to toggle the bracket style used for displaying new activities in the log. This preference is saved automatically.

        Click the Add button to add it.

    Filter Activities Log: Click on any of the created category buttons below (e.g., "Work 2.5h") to filter the "Activities Log" to show only activities of that category. Click "All" to view all activities again.

    Delete a Category: Click the X icon next to a category button to delete it.

        Note: For data safety, you cannot delete a category if it already has associated activity records.

3.5 Activities Log

This section displays all activity records for the selected date.

    Total Time: Shows the total duration for the currently filtered view. Clicking this area will copy the total time (e.g., "Work Time: 3.50h").

    Columns: By default, it displays "Time Range," "Activity," "Duration," and "Copy" columns.

    Copy a Single Activity: Click the ?? icon at the end of each row to quickly copy the text for that activity (e.g., 09:00-09:30 【Work】Reply to emails).

    Copy All Activities: Click the Copy All button at the top left to copy the text for all activities in the current view.

    Export to TXT: Click the Export to TXT button to export all of today's activities and a category summary into a .txt file.

    Edit/Delete an Activity: Right-click on any activity record to bring up a context menu, where you can choose Edit Activity or Delete.

    Reorder Columns: Right-click an activity record and select Display: Time First or Display: Activity First from the context menu to change the display order of the "Time Range" and "Activity" columns. This setting is saved automatically.

4. Menu Bar Functions
4.1 File

    Backup Data...: Highly Recommended! This feature allows you to back up your current time_tracker_data.json file to any location you choose. Regular backups are a good habit to protect your valuable data.

    Restore from Backup...: Restore all your data from a previously created backup file.

        ?? WARNING: This is an overwrite operation that will replace all your current data with the backup file and cannot be undone. Please confirm before proceeding. After a successful restore, the application will close automatically, and you will need to restart it manually.

    Exit: Safely saves all settings and closes the application.

4.2 View

    Theme: You can switch between Dark and Light themes to suit your preference. The theme setting is saved automatically.

5. Shortcuts

To enhance your efficiency, the application includes the following keyboard shortcuts:

    Ctrl + S: Start or stop the timer.

    Ctrl + N: Quickly focus the cursor on the "Add a new category" input field.

    Ctrl + M: Open the "Add Activity Manually" window.

If this tool is helpful to you, please give me some encouragement stars
