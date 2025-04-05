import frappe
from frappe.utils import today, get_datetime, time_diff_in_hours, nowdate

@frappe.whitelist()
def process_attendance():
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
        for log in check_ins:
            employee_logs.setdefault(log.employee, []).append(log)

        for employee, logs in employee_logs.items():
            for log in logs:
                log["time"] = get_datetime(log["time"])
            logs = sorted(logs, key=lambda x: x["time"])

            first_in = next((log for log in logs if log["log_type"] == "IN"), None)
            last_out = next((log for log in reversed(logs) if log["log_type"] == "OUT"), None)

            if not first_in or not last_out:
                continue

            in_time = get_datetime(first_in["time"])
            out_time = get_datetime(last_out["time"])

            if in_time.date() == out_time.date() == get_datetime(nowdate()).date():
                duration = time_diff_in_hours(out_time, in_time)

                if duration >= present_buffer_hour:
                    status = "Present"
                elif duration >= absent_buffer_hour:
                    status = "Half Day"
                else:
                    status = "Absent"

                if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": nowdate()}):
                    attendance = frappe.get_doc({
                        "doctype": "Attendance",
                        "employee": employee,
                        "attendance_date": nowdate(),
                        "status": status,
                        "working_hours": duration,
                        "shift": logs[0].get("shift"),
                        "in_time": in_time,
                        "out_time": out_time,
                    })
                    attendance.insert(ignore_permissions=True)
                    attendance.submit()
                    frappe.db.commit()

            else:
                if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": nowdate()}):
                    attendance = frappe.get_doc({
                        "doctype": "Attendance",
                        "employee": employee,
                        "attendance_date": nowdate(),
                        "status": "Present",
                        "docstatus": 0,
                        "shift": logs[0].get("shift"),
                        "in_time": in_time
                    })
                    attendance.insert(ignore_permissions=True)


        draft_attendances = frappe.get_all("Attendance", filters={
            "docstatus": 0,
            "attendance_date": nowdate()
        }, fields=["name", "employee", "attendance_date"])

        for att in draft_attendances:
            employee = att.employee
            att_date = att.attendance_date
            attendance_doc = frappe.get_doc("Attendance", att.name)

            first_in = frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "log_type": "IN",
                    "time": [">=", f"{att_date} 00:00:00"],
                    "time": ["<=", f"{att_date} 23:59:59"]
                },
                fields=["time"],
                order_by="time ASC",
                limit=1
            )

            last_out = frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": employee,
                    "log_type": "OUT",
                    "time": [">=", f"{att_date} 00:00:00"],
                    "time": ["<=", f"{nowdate()} 23:59:59"]
                },
                fields=["time"],
                order_by="time DESC",
                limit=1
            )

            if not first_in or not last_out:
                continue

            in_time = get_datetime(first_in[0].time)
            out_time = get_datetime(last_out[0].time)
            duration = time_diff_in_hours(out_time, in_time)

            if duration >= present_buffer_hour:
                status = "Present"
            elif duration >= absent_buffer_hour:
                status = "Half Day"
            else:
                status = "Absent"

            attendance_doc.update({
                "status": status,
                "working_hours": duration,
                "in_time": in_time,
                "out_time": out_time
            })
            attendance_doc.submit()

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(title="Attendance Processing Error", message=frappe.get_traceback())
