import frappe
from frappe.utils import get_datetime, time_diff_in_hours

@frappe.whitelist()
def process_attendance():
   

    attendance_settings = frappe.get_single("Attendance Setting")
    present_buffer_hour = attendance_settings.make_attendance_present_buffer_hour or 8
    absent_buffer_hour = attendance_settings.make_attendance_absent_buffer_hour or 4

    try:
        check_ins = frappe.get_all(
            "Employee Checkin",
            filters={"attendance": ["is", "not set"]},
            fields=["name", "employee", "time", "log_type", "shift"],
            order_by="employee ASC, time ASC"
        )

        employee_logs = {}
        for log in check_ins:
            log["time"] = get_datetime(log["time"])
            employee_logs.setdefault(log["employee"], []).append(log)

        for employee, logs in employee_logs.items():
            i = 0
            while i < len(logs):
                log = logs[i]

                if log["log_type"] != "IN":
                    i += 1
                    continue

                in_time = log["time"]
                in_log = log
                out_log = None

                for j in range(i + 1, len(logs)):
                    if logs[j]["log_type"] == "OUT":
                        out_time = logs[j]["time"]
                        out_log = logs[j]
                        break

                if not out_log:
                    i += 1
                    continue

                duration = time_diff_in_hours(out_log["time"], in_time)
                if duration >= present_buffer_hour:
                    status = "Present"
                elif duration >= absent_buffer_hour:
                    status = "Half Day"
                else:
                    status = "Absent"

                att_date = in_time.date()

                if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": att_date, "docstatus": 1}):
                    attendance = frappe.get_doc({
                        "doctype": "Attendance",
                        "employee": employee,
                        "attendance_date": att_date,
                        "status": status,
                        "working_hours": duration,
                        "shift": in_log.get("shift"),
                        "in_time": in_time,
                        "out_time": out_log["time"],
                    })
                    attendance.insert(ignore_permissions=True)
                    attendance.submit()

                    frappe.db.set_value("Employee Checkin", in_log["name"], "attendance", attendance.name)
                    frappe.db.set_value("Employee Checkin", out_log["name"], "attendance", attendance.name)

                i = logs.index(out_log) + 1

        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error in process_attendance")
