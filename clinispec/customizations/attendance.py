import frappe
from frappe.utils import today, get_datetime, time_diff_in_hours, nowdate

def process_attendance():
    """
    Cron function to process employee check-ins and create attendance records.
    - Fetches today's check-ins.
    - Groups check-ins per employee.
    - Finds first IN and last OUT log (Datetime-based).
    - Calculates duration.
    - Validates against attendance settings.
    - Creates Attendance in Frappe.
    """

    
    attendance_settings = frappe.get_single("Attendance Setting")
    present_buffer_hour = attendance_settings.get("make_attendance_present_buffer_hour")
    absent_buffer_hour = attendance_settings.get("make_attendance_absent_buffer_hour")
    try: 
        
        check_ins = frappe.get_all(
            "Employee Checkin",
            filters={
                "time": [">=", f"{nowdate()} 00:00:00"],  
                "time": ["<=", f"{nowdate()} 23:59:59"]   
            },
            fields=["employee", "time", "log_type", "shift"],
            order_by="time ASC"  
        )

        
        employee_logs = {}
        for check_in in check_ins:
            employee_logs.setdefault(check_in["employee"], []).append(check_in)

        for employee, logs in employee_logs.items():
           
            for log in logs:
                log["time"] = get_datetime(log["time"])

           
            first_in = next((log for log in logs if log["log_type"] == "IN"), None)
            last_out = next((log for log in reversed(logs) if log["log_type"] == "OUT"), None)

            if not first_in or not last_out:
                
                continue
            
            shift = first_in.get("shift", None)
           
            duration = time_diff_in_hours(last_out["time"], first_in["time"])

            
            status = "Absent"
            if duration >= present_buffer_hour:
                status = "Present"
            elif duration >= absent_buffer_hour:
                status = "Half Day"

            if not frappe.db.exists("Attendance",{"employee":employee,"attendance_date":today()}):
                attendance_doc = frappe.get_doc({
                    "doctype": "Attendance",
                    "employee": employee,
                    "attendance_date": today(),
                    "status": status,
                    "working_hours":duration,
                    "shift": shift
                })
                attendance_doc.insert(ignore_permissions=True)
                attendance_doc.submit()
                frappe.db.commit()
    except Exception as e:

        frappe.log_error(title=f"Attendance marked for {employee}: {status} ({duration} hours)",message=e )

