// eTax Settings Client Script
// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)

frappe.ui.form.on('eTax Settings', {
	refresh: function(frm) {
		// Show/hide fields based on environment
		frm.trigger('environment');
		
		// Add custom CSS for tabs
		frm.page.add_inner_button(__('Sync Reports'), function() {
			frm.trigger('sync_reports');
		});
	},
	
	environment: function(frm) {
		// Update URLs when environment changes
		if (frm.doc.environment === 'Production') {
			frm.set_value('api_base_url', 'https://etax.mta.mn/api/beta');
			frm.set_value('auth_url', 'https://api.frappe.mn/auth/itc');
		} else {
			frm.set_value('api_base_url', 'https://st-etax.mta.mn/api/beta');
			frm.set_value('auth_url', 'https://api.frappe.mn/auth/itc-staging');
		}
	},
	
	test_connection_button: function(frm) {
		// Validate required fields
		if (!frm.doc.username || !frm.doc.password || !frm.doc.ne_key || !frm.doc.org_regno) {
			frappe.msgprint({
				title: __('Missing Credentials'),
				indicator: 'red',
				message: __('Please fill in Username, Password, NE-KEY, and Organization RegNo before testing connection.')
			});
			return;
		}
		
		// Save first if dirty
		if (frm.is_dirty()) {
			frm.save().then(() => {
				frm.trigger('do_test_connection');
			});
		} else {
			frm.trigger('do_test_connection');
		}
	},
	
	do_test_connection: function(frm) {
		frappe.show_alert({
			message: __('Testing connection...'),
			indicator: 'blue'
		});
		
		frappe.call({
			method: 'test_connection',
			doc: frm.doc,
			freeze: true,
			freeze_message: __('Testing eTax API connection...'),
			callback: function(r) {
				if (r.message) {
					if (r.message.success) {
						if (r.message.warning) {
							// Authentication OK but no orgs linked
							frappe.msgprint({
								title: __('Authentication Successful'),
								indicator: 'orange',
								message: r.message.message
							});
						} else {
							// Full success with org info
							frappe.show_alert({
								message: __('Connection successful!') + '<br>' + 
									__('Organization: {0}', [r.message.org_name || '']),
								indicator: 'green'
							}, 5);
						}
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('Connection Failed'),
							indicator: 'red',
							message: r.message.message || __('Unknown error')
						});
						frm.reload_doc();
					}
				}
			},
			error: function(r) {
				frappe.msgprint({
					title: __('Connection Error'),
					indicator: 'red',
					message: __('Failed to test connection. Check browser console for details.')
				});
			}
		});
	},
	
	sync_reports: function(frm) {
		if (!frm.doc.enabled) {
			frappe.msgprint(__('Please enable eTax integration first.'));
			return;
		}
		
		frappe.call({
			method: 'sync_reports',
			doc: frm.doc,
			freeze: true,
			freeze_message: __('Syncing tax reports from MTA...'),
			callback: function(r) {
				if (r.message) {
					if (r.message.success) {
						frappe.show_alert({
							message: r.message.message,
							indicator: 'green'
						}, 5);
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('Sync Failed'),
							indicator: 'red',
							message: r.message.message
						});
					}
				}
			}
		});
	}
});
