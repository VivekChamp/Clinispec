// Copyright (c) 2025, VPS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Setting", {
	refresh(frm) {
		cur_frm.add_custom_button(__("Make Attendance"), function () {
			frappe.call({
				method: "clinispec.customizations.attendance.process_attendance",
				freeze: true,
				callback: function (r) {
						frappe.msgprint("Attendance Processed!")
					}
			});
		},);

	},
});
