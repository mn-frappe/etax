// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.listview_settings['eTax Invoice Link'] = {
    get_indicator: function(doc) {
        const status_color = {
            'Pending': 'orange',
            'Included': 'blue',
            'Submitted': 'green',
            'Cancelled': 'red'
        };
        return [__(doc.status), status_color[doc.status] || 'grey', 'status,=,' + doc.status];
    },
    
    formatters: {
        vat_amount: function(value) {
            return format_currency(value, 'MNT');
        }
    },
    
    onload: function(listview) {
        // Add bulk actions
        listview.page.add_action_item(__('Include in Declaration'), function() {
            const selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__('Please select at least one record'));
                return;
            }
            
            frappe.prompt({
                fieldtype: 'Link',
                label: 'eTax Declaration',
                fieldname: 'declaration',
                options: 'eTax Report',
                reqd: 1
            }, function(values) {
                frappe.call({
                    method: 'etax.etax.doctype.etax_invoice_link.etax_invoice_link.bulk_include_in_declaration',
                    args: {
                        links: selected.map(d => d.name),
                        declaration_name: values.declaration
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint(__('Included {0} records in declaration', [r.message.count]));
                            listview.refresh();
                        }
                    }
                });
            }, __('Select Declaration'), __('Include'));
        });
    }
};
